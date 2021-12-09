from stac_fastapi.api.app import StacApi
from stac_fastapi.api.app import ApiSettings
from opensearch_stac_adapter.adapter import OpenSearchAdapterClient
from opensearch_stac_adapter.types.search import AdaptedSearch

settings = ApiSettings()

api = StacApi(
    settings=settings,
    client=OpenSearchAdapterClient(),
    extensions=[],
    title="STAC API for Remote Sensing",
    description="STAC API for Remote Sensing",
    search_request_model=AdaptedSearch,
)

app = api.app


def run():
    """Run app from command line using uvicorn if available."""
    try:
        import uvicorn

        uvicorn.run(
            "opensearch_stac_adapter.app:app",
            host=settings.app_host,
            port=settings.app_port,
            log_level="info",
            reload=settings.reload
        )
    except ImportError:
        raise RuntimeError("Uvicorn must be installed in order to use command")


if __name__ == "__main__":
    run()
