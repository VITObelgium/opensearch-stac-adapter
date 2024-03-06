FROM python:3.8-slim

ARG PACKAGE_NAME

COPY dist/$PACKAGE_NAME /src/$PACKAGE_NAME
COPY logging.conf /src/logging.conf

RUN python3 -m pip install /src/${PACKAGE_NAME} "gunicorn==21.2.0"  --extra-index-url https://artifactory.vgt.vito.be/artifactory/api/pypi/python-packages/simple

ENV WEB_CONCURRENCY=8

ENTRYPOINT gunicorn opensearch_stac_adapter.app:app --bind 0.0.0.0:80 --worker-class 'uvicorn.workers.UvicornWorker' --log-config /src/logging.conf
