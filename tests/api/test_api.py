import pytest

STAC_CORE_ROUTES = [
    "GET /",
    "GET /collections",
    "GET /collections/{collectionId}",
    "GET /collections/{collectionId}/items",
    "GET /collections/{collectionId}/items/{itemId}",
    "GET /conformance",
    "GET /search",
    "POST /search",
]


@pytest.mark.asyncio
async def test_core_router(api_client):
    core_routes = set(STAC_CORE_ROUTES)
    api_routes = set(
        f"{list(route.methods)[0]} {route.path}" for route in api_client.app.routes
    )
    assert core_routes.issubset(api_routes)
