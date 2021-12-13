import pytest

from stac_fastapi.api.app import ApiSettings
from stac_fastapi.api.app import StacApi

from opensearch_stac_adapter.adapter import OpenSearchAdapterClient
from opensearch_stac_adapter.types.search import AdaptedSearch

settings = ApiSettings()


@pytest.fixture(scope="session")
def api_client():
    extensions = []

    api = StacApi(
        settings=settings,
        extensions=extensions,
        client=OpenSearchAdapterClient(),
        search_request_model=AdaptedSearch,
    )

    return api
