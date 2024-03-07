from fastapi.testclient import TestClient
from jsonpath_ng import jsonpath
from jsonpath_ng.ext import parse

# for testing, consult the following resources
# - https://fastapi.tiangolo.com/tutorial/testing/
# - https://github.com/stac-utils/stac-fastapi (tests of pgstac and sqlalchemy clients)


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


def test_core_router(api_client):
    core_routes = set(STAC_CORE_ROUTES)
    api_routes = set(
        f"{list(route.methods)[0]} {route.path}" for route in api_client.app.routes
    )
    assert core_routes.issubset(api_routes)


def test_root(test_client: TestClient):
    response = test_client.get("/")
    assert response.status_code == 200


def test_collections(test_client: TestClient):
    response = test_client.get("/collections")
    assert response.status_code == 200


def test_collection(test_client: TestClient):
    response = test_client.get("/collections/urn:eop:VITO:TERRASCOPE_S2_CHL_V1")
    assert response.status_code == 200


def test_collection_invalid(test_client: TestClient):
    response = test_client.get("/collections/non_existent_collection")
    assert response.status_code == 404


def test_items(test_client: TestClient):
    response = test_client.get("/collections/urn:eop:VITO:TERRASCOPE_S2_CHL_V1/items")
    assert response.status_code == 200
    data = response.json()
    assert len(data['features']) > 0
    path_links_next: jsonpath.JSONPath = parse("$.links[?(@.rel=='next')]")
    assert len(path_links_next.find(data)) == 1


def test_items_invalid(test_client: TestClient):
    response = test_client.get("/collections/non_existent_collection/items")
    assert response.status_code == 404


def test_item(test_client: TestClient):
    response = test_client.get("/collections/urn:eop:VITO:TERRASCOPE_S2_CHL_V1/items/"
                               "urn:eop:VITO:TERRASCOPE_S2_CHL_V1:S2A_20220110T105421_31UES_CHL_20M_V120")
    assert response.status_code == 200
    data = response.json()
    # don't expect a 'tiles' link
    path_links_tiles: jsonpath.JSONPath = parse("$.links[?(@.title=='tiles')]")
    assert len(path_links_tiles.find(data)) == 0


def test_item_invalid(test_client: TestClient):
    # valid collection with invalid item identifier
    response = test_client.get("/collections/urn:eop:VITO:TERRASCOPE_S2_CHL_V1/items/non_existent_item")
    assert response.status_code == 404


def test_item_invalid_collection(test_client: TestClient):
    # invalid collection
    response = test_client.get("/collections/non_existent_collection/items/non_existent_item")
    assert response.status_code == 404


def test_get_search(test_client: TestClient):
    page = 0
    response = test_client.get(
        "/search",
        params={
            "collections": ",".join(["urn:eop:VITO:TERRASCOPE_S2_CHL_V1", "urn:eop:VITO:TERRASCOPE_S2_TUR_V1"]),
            "datetime": "2020-02-01T00:00:00Z/2020-02-20T23:59:59Z"
        }
    )
    assert response.status_code == 200
    data = response.json()

    # test next link
    path_links_next: jsonpath.JSONPath = parse("$.links[?(@.rel=='next')].href")
    matches = path_links_next.find(data)
    assert len(matches) == 1

    while len(matches) > 0:
        next_link = matches[0].value
        page += 1
        response = test_client.get(next_link)
        assert response.status_code == 200
        data = response.json()
        matches = path_links_next.find(data)

    assert page >= 1


def test_get_search_no_collection(test_client: TestClient):
    response = test_client.get(
        "/search",
        params={
            "datetime": "2020-02-01T00:00:00Z/2020-02-20T23:59:59Z"
        }
    )
    assert response.status_code == 200


def test_post_search(test_client: TestClient):
    page = 0
    response = test_client.post(
        "/search",
        json={
            "collections": ["urn:eop:VITO:TERRASCOPE_S2_CHL_V1", "urn:eop:VITO:TERRASCOPE_S2_TUR_V1"],
            "datetime": "2020-02-01T00:00:00Z/2020-02-20T23:59:59Z"
        }
    )
    assert response.status_code == 200
    data = response.json()

    # test next link
    path_links_next: jsonpath.JSONPath = parse("$.links[?(@.rel=='next')]")
    matches = path_links_next.find(data)
    assert len(matches) == 1

    while len(matches) > 0:
        next_link = matches[0].value
        page += 1
        response = test_client.post(next_link['href'], json=next_link['body'])
        assert response.status_code == 200
        data = response.json()
        matches = path_links_next.find(data)

    assert page >= 1
