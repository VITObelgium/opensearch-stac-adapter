import attr
from datetime import datetime
from urllib.parse import urljoin, urlparse
from typing import Optional, List, Union, Dict, Type
from collections import OrderedDict

from pydantic import ValidationError
from starlette.requests import Request
from jsonpath_ng import jsonpath, parse
import json
from shapely.geometry import shape

from stac_pydantic.links import Relations
from stac_pydantic.shared import MimeTypes, Asset, AssetRoles, Provider
from stac_fastapi.types.core import AsyncBaseCoreClient, NumType
from stac_fastapi.types.stac import Collection, Collections, Item, ItemCollection
from stac_fastapi.types.links import CollectionLinks
from stac_fastapi.types.errors import NotFoundError, InvalidQueryParameter
from fastapi.exceptions import HTTPException

from terracatalogueclient import Catalogue
import terracatalogueclient.client
import terracatalogueclient.exceptions

from opensearch_stac_adapter import __title__, __version__
from opensearch_stac_adapter.models.links import PagingLinks, ItemLinks
from opensearch_stac_adapter.models.search import AdaptedSearch


path_beginning_datetime: jsonpath.JSONPath = parse(
    "$.acquisitionInformation[*].acquisitionParameters.beginningDateTime"
)
path_ending_datetime: jsonpath.JSONPath = parse(
    "$.acquisitionInformation[*].acquisitionParameters.endingDateTime"
)
path_platform_shortname: jsonpath.JSONPath = parse(
    "$.acquisitionInformation[*].platform.platformShortName"
)
path_resource_links: jsonpath.JSONPath = parse(
    "$.links.*[*]"
)

terracatalogueclient.client._DEFAULT_REQUEST_HEADERS = {
    "User-Agent": f"{__title__}/{__version__} with {terracatalogueclient.__title__}/{terracatalogueclient.__version__}"
}


@attr.s
class OpenSearchAdapterClient(AsyncBaseCoreClient):
    """STAC API client that implements a OpenSeach endpoint as back-end."""

    catalogue: Catalogue = attr.ib(default=Catalogue())  # OpenSearch catalogue
    search_request_model: Type[AdaptedSearch] = attr.ib(init=False, default=AdaptedSearch)

    @staticmethod
    async def _collection_adapter(c: terracatalogueclient.Collection, base_url: str) -> Collection:
        """
        Adapts an OpenSearch collection to the STAC collection format.

        :param c: OpenSearch collection
        :param base_url: base URL of the request
        :return: STAC collection
        """
        date_split = c.properties['date'].split("/")
        date_start = date_split[0]
        date_end = date_split[1] if len(date_split) == 2 and len(date_split[1]) > 0 else None

        return Collection(
            type="Collection",
            stac_version="1.0.0",
            # stac_extensions
            id=c.id,
            title=c.properties['title'],
            description=c.properties['abstract'],
            license=c.properties['rights'],
            keywords=c.properties['keyword'],
            # providers
            extent={
                "spatial": {
                    "bbox": [c.bbox]
                },
                "temporal": {
                    "interval": [[date_start, date_end]]
                }
            },
            summaries={
                "datetime": {
                    "min": date_start,
                    "max": date_end,
                },
                # "eo:gsd": c['properties']['productInformation']['resolution'],
                # platform
                "constellation": list(
                    {
                        acquisitionInformation['platform']['platformShortName']
                        for acquisitionInformation in c.properties['acquisitionInformation']
                        if 'platform' in acquisitionInformation
                    }
                ),
                "instruments": list(
                    {
                        acquisitionInformation['instrument']['instrumentShortName']
                        for acquisitionInformation in c.properties['acquisitionInformation']
                        if 'instrument' in acquisitionInformation
                    }
                )
            },
            links=CollectionLinks(collection_id=c.id, base_url=base_url).create_links()
        )

    @staticmethod
    async def _item_adapter(p: terracatalogueclient.Product, collection: str, base_url: str) -> Item:
        """
        Adapts an OpenSearch product to the STAC item format.

        :param p: OpenSearch product
        :param collection: collection identifier
        :param base_url: base URL of the request
        :return: STAC item
        """
        assets = OrderedDict()
        # check https://github.com/radiantearth/stac-spec/blob/master/best-practices.md#list-of-asset-roles
        # for a list of asset roles
        for pf in p.previews:
            asset = await OpenSearchAdapterClient._item_asset_adapter(pf, ["thumbnail"])
            if pf.title is not None:
                key = pf.title
            elif pf.category is not None:
                key = pf.category
            else:
                key = urlparse(pf.href).path
            assets[key] = asset
        for pf in p.alternates:
            asset = await OpenSearchAdapterClient._item_asset_adapter(pf, ["metadata"])
            if pf.title is not None:
                key = pf.title
            else:
                key = urlparse(pf.href).path
            assets[key] = asset
        for pf in p.related:
            asset = await OpenSearchAdapterClient._item_asset_adapter(pf, None)
            if pf.title is not None:
                key = pf.title
            else:
                key = urlparse(pf.href).path
            assets[key] = asset
        for pf in p.data:
            asset = await OpenSearchAdapterClient._item_asset_adapter(pf, ["data"])
            if pf.title is not None:
                key = pf.title
            else:
                key = urlparse(pf.href).path
            assets[key] = asset

        properties = {
            "datetime": p.properties['date'],
            "title": p.title,
            "created": p.properties['published'],
            "updated": p.properties['updated'],
            "start_datetime": path_beginning_datetime.find(p.properties)[0].value,
            "end_datetime": path_ending_datetime.find(p.properties)[0].value
        }

        if len(platforms := path_platform_shortname.find(p.properties)):
            properties['platform'] = platforms[0].value

        return Item(
            type="Feature",
            stac_version="1.0.0",
            # stac_extensions
            id=p.id,
            geometry=p.geojson['geometry'],
            bbox=p.bbox,
            properties=properties,
            links=ItemLinks(collection_id=collection, base_url=base_url, item_id=p.id).create_links(),
            assets=assets,
            collection=p.properties['parentIdentifier']
        )

    @staticmethod
    async def _item_asset_adapter(pf: terracatalogueclient.ProductFile, roles: Optional[List[str]]) -> dict:
        """
        Adapts an OpenSearch product file to the STAC asset format.

        :param pf: OpenSearch product file
        :param roles: list of roles of the asset
        :return: STAC asset
        """
        asset = dict()
        asset['href'] = pf.href
        asset['type'] = pf.type
        if pf.title is not None:
            asset['title'] = pf.title
        if roles is not None:
            asset['roles'] = roles

        return asset

    async def all_collections(self, **kwargs) -> Collections:
        """
        Get all collections.

        Called with `GET /collections`.

        :return: collections
        """
        request: Request = kwargs['request']
        base_url = str(request.base_url)

        collections: List[Collection] = []
        for c in self.catalogue.get_collections():
            collections.append(await self._collection_adapter(c, base_url))

        links = [
            {
                "rel": Relations.root.value,
                "type": MimeTypes.json,
                "href": base_url
            },
            {
                "rel": Relations.parent.value,
                "type": MimeTypes.json,
                "href": base_url,
            },
            {
                "rel": Relations.self.value,
                "type": MimeTypes.json,
                "href": urljoin(base_url, "collections")
            }
        ]
        return Collections(collections=collections, links=links)

    async def get_collection(self, id: str, **kwargs) -> Collection:
        """
        Get collection by id.

        Called with `GET /collections/{id}`.

        :param id: id of the collection
        :return: collection
        """
        request: Request = kwargs["request"]
        base_url = str(request.base_url)

        try:
            collections = list(self.catalogue.get_collections(uid=id))
        except terracatalogueclient.exceptions.SearchException as e:
            collections = []
        if len(collections) != 1:
            raise NotFoundError(f"Collection {id} does not exist.")

        return await self._collection_adapter(collections[0], base_url)

    async def item_collection(self, id: str, limit: int = 10, token: str = None, **kwargs) -> ItemCollection:
        """
        Get items from a specific collection.

        Called with `GET /collections/{id}/items`

        :param id: collection ID
        :param limit: number of items to return
        :param token: pagination token
        :return: item collection
        """
        request: Request = kwargs["request"]
        base_url = str(request.base_url)

        # check if collection exists, if not, a NotFoundError will be raised
        await self.get_collection(id, **kwargs)

        search = self.search_request_model(collections=[id], limit=limit, token=token)
        item_collection = await self._search_base(search, **kwargs)

        links = item_collection.get("links", [])
        links.extend(CollectionLinks(collection_id=id, base_url=base_url).create_links())
        item_collection['links'] = links

        return item_collection

    async def get_item(self, item_id: str, collection_id: str, **kwargs) -> Item:
        """
        Get item by ID.

        Called with `GET /collections/{collection_id}/items/{item_id}`

        :param item_id: item ID
        :param collection_id: collection ID
        :return: item
        """
        request: Request = kwargs["request"]
        base_url = str(request.base_url)

        # check if collection exists, if not, a NotFoundError will be raised
        await self.get_collection(collection_id, **kwargs)

        try:
            [product] = list(self.catalogue.get_products(collection=collection_id, uid=item_id))
            # raises ValueError when cannot unpack 1 value from list
            return await self._item_adapter(product, collection_id, base_url)
        except (terracatalogueclient.exceptions.SearchException, ValueError):
            raise NotFoundError(f"Item {item_id} does not exist in collection {collection_id}.")

    async def _search_base(self, search_request: AdaptedSearch, **kwargs) -> ItemCollection:
        """
        Implements cross-catalog search.
        Multiple collections are supported by iterating over the collections. Supports paging.

        :param search_request: search request parameters
        :return: item collection containing the search results
        """
        request: Request = kwargs["request"]
        base_url = str(request.base_url)

        next_token: Optional[str] = None
        items: List[Item] = []

        if search_request.ids is not None:
            # only return the requested ids
            for item_id in set(search_request.ids):
                for collection_id in search_request.collections:
                    try:
                        results = list(self.catalogue.get_products(collection=collection_id, uid=item_id))
                        if len(results) == 1:
                            items.append(await self._item_adapter(results[0], collection_id, base_url=base_url))
                            break
                    except terracatalogueclient.exceptions.SearchException:
                        pass
        else:
            # perform full query
            query_params = dict()
            if search_request.datetime is not None:
                query_params['start'] = search_request.start_date
                query_params['end'] = search_request.end_date
            if search_request.bbox is not None:
                query_params['bbox'] = list(search_request.bbox)
            if search_request.intersects is not None:
                query_params['geometry'] = shape(search_request.intersects).wkt
            if search_request.token is not None:
                try:
                    collection, start_index, collection_hit_count = search_request.token.split(",")
                    start_index = int(start_index)
                    collection_hit_count = int(collection_hit_count)

                    query_params['startIndex'] = start_index
                except ValueError:
                    raise InvalidQueryParameter("Invalid value for token parameter.")
            else:
                collection = search_request.collections[0]
                start_index = 1
                collection_hit_count = self.catalogue.get_product_count(collection=collection, **query_params)

            if start_index + search_request.limit - 1 < collection_hit_count:
                next_index = start_index + search_request.limit
                next_token = f"{collection},{next_index},{collection_hit_count}"
            else:
                # link to next collection (if available)
                next_collection_idx = search_request.collections.index(collection) + 1
                next_collection = search_request.collections[next_collection_idx] if len(search_request.collections) > next_collection_idx else None
                if next_collection is not None:
                    next_collection_hit_count = self.catalogue.get_product_count(collection=next_collection, **query_params)
                    next_token = f"{next_collection},1,{next_collection_hit_count}"

            products = self.catalogue.get_products(
                collection=collection,
                limit=search_request.limit,
                **query_params
            )

            for p in products:
                items.append(await self._item_adapter(p, collection, base_url=base_url))

        return ItemCollection(
            type="FeatureCollection",
            features=items,
            links=PagingLinks(
                request,
                next_token=next_token,
                body=await request.json() if request.method == "POST" else None
            ).create_links()
        )

    async def get_search(
            self,
            collections: Optional[List[str]] = None,
            ids: Optional[List[str]] = None,
            bbox: Optional[List[NumType]] = None,
            datetime: Optional[Union[str, datetime]] = None,
            limit: Optional[int] = 10,
            query: Optional[str] = None,
            token: Optional[str] = None,
            fields: Optional[List[str]] = None,
            sortby: Optional[str] = None,
            **kwargs
    ) -> ItemCollection:
        """
        Cross-catalog search (GET).

        Called with `GET /search`

        :param collections: list of collections to query
        :param ids: list of identifiers to retrieve
        :param bbox: bounding box
        :param datetime: start/end time
        :param limit: maximum number of results per page
        :param query:
        :param token: pagination token
        :param fields:
        :param sortby:
        :return: item collection containing the query results
        """
        # parse request parameters
        base_args = {
            "collections": collections,
            "ids": ids,
            "bbox": bbox,
            "limit": limit,
            "token": token,
            "query": json.loads(query) if query else query,
        }
        if datetime:
            base_args["datetime"] = datetime
        try:
            search_request = self.search_request_model(**base_args)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail="Invalid parameters provided.")
        results = await self._search_base(search_request, **kwargs)
        return results

    async def post_search(self, search_request: AdaptedSearch, **kwargs) -> ItemCollection:
        """
        Cross-catalog search (POST).

        Called with `POST /search`

        :param search_request: search request parameters
        :return: item collection containing the query results
        """
        return await self._search_base(search_request, **kwargs)
