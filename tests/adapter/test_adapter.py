from opensearch_stac_adapter.adapter import OpenSearchAdapterClient
import pytest

base_url = "http://localhost/"


@pytest.mark.asyncio
async def test_collection(opensearch_adapter_client: OpenSearchAdapterClient):
    [opensearch_collection] = opensearch_adapter_client.catalogue.get_collections(
        uid="urn:eop:VITO:TERRASCOPE_S2_LAI_V2"
    )
    stac_collection = await opensearch_adapter_client._collection_adapter(opensearch_collection, base_url)

    assert stac_collection['id'] == opensearch_collection.id


@pytest.mark.asyncio
async def test_item(opensearch_adapter_client: OpenSearchAdapterClient):
    collection = "urn:eop:VITO:TERRASCOPE_S2_LAI_V2"
    [opensearch_product] = opensearch_adapter_client.catalogue.get_products(
        collection=collection,
        uid="urn:eop:VITO:TERRASCOPE_S2_LAI_V2:S2A_20220107T104431_31UFS_LAI_10M_V200"
    )
    stac_item = await opensearch_adapter_client._item_adapter(opensearch_product, collection, base_url)

    assert stac_item['id'] == opensearch_product.id
    assert all(any(asset['href'] == pf.href for key, asset in stac_item['assets'].items())
               for pf
               in opensearch_product.previews +
               opensearch_product.alternates +
               opensearch_product.related +
               opensearch_product.data
    )
    print(stac_item)
