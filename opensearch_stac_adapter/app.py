from stac_fastapi.api.app import StacApi
from stac_fastapi.api.app import ApiSettings
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from asgi_logger import AccessLoggerMiddleware
from opensearch_stac_adapter.adapter import OpenSearchAdapterClient
from opensearch_stac_adapter.models.search import AdaptedSearch
import logging
from typing import Optional, Dict, Any

settings = ApiSettings()

api = StacApi(
    settings=settings,
    client=OpenSearchAdapterClient(landing_page_id="terrascope"),
    extensions=[],
    title="Terrascope - STAC API",
    description="VITO Remote Sensing EO Data Catalogue - Terrascope platform.",
    search_request_model=AdaptedSearch,
    middlewares=[]
)

app: FastAPI = api.app
app.add_middleware(
    AccessLoggerMiddleware,
    format='%(t)s %(client_addr)s "%(request_line)s" %(s)s %(B)s %(M)s',
    logger=logging.getLogger("access")
)


def customize_openapi() -> Optional[Dict[str, Any]]:
    """Customize OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=api.title, version=api.api_version, routes=app.routes, servers=app.servers
    )

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = customize_openapi


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
