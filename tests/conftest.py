import pytest

from stac_fastapi.api.app import ApiSettings
from stac_fastapi.api.app import StacApi
from fastapi.testclient import TestClient

from opensearch_stac_adapter.adapter import OpenSearchAdapterClient
from opensearch_stac_adapter.models.search import AdaptedSearch

settings = ApiSettings()


@pytest.fixture(scope="session")
def opensearch_adapter_client() -> OpenSearchAdapterClient:
    return OpenSearchAdapterClient()


@pytest.fixture(scope="session")
def api_client() -> StacApi:
    extensions = []

    api = StacApi(
        settings=settings,
        extensions=extensions,
        client=OpenSearchAdapterClient(),
        search_request_model=AdaptedSearch,
    )

    return api


@pytest.fixture(scope="session")
def test_client(api_client) -> TestClient:
    app = api_client.app
    client = TestClient(app)
    return client
