FROM python:3.8-alpine

ARG PACKAGE_NAME

COPY dist/${PACKAGE_NAME} /src/${PACKAGE_NAME}

RUN python3 -m pip install /src/${PACKAGE_NAME}

ENTRYPOINT uvicorn opensearch_stac_adapter.app:app --host 0.0.0.0 --port 80