from stac_fastapi.api.app import StacApi
from stac_fastapi.api.app import ApiSettings
from fastapi import FastAPI, Request
from opensearch_stac_adapter.adapter import OpenSearchAdapterClient
from opensearch_stac_adapter.models.search import AdaptedSearch

settings = ApiSettings()

api = StacApi(
    settings=settings,
    client=OpenSearchAdapterClient(landing_page_id="terrascope"),
    extensions=[],
    title="Terrascope - STAC API",
    description="VITO Remote Sensing EO Data Catalogue - Terrascope platform.",
    search_request_model=AdaptedSearch,
)

app: FastAPI = api.app


@app.middleware("http")
async def handle_x_forwarded_prefix_header(request: Request, call_next):
    prefix = request.headers.get("X-Forwarded-Prefix")
    if prefix:
        request.scope['root_path'] = prefix

    return await call_next(request)


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
