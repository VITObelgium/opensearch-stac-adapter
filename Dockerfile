FROM python:3.8

ARG PACKAGE_NAME

COPY pip.conf /etc/pip.conf

COPY logging.yaml /src/logging.yaml
COPY dist/${PACKAGE_NAME} /src/${PACKAGE_NAME}
RUN mkdir /logs

RUN python3 -m pip install /src/${PACKAGE_NAME}

ENTRYPOINT uvicorn opensearch_stac_adapter.app:app --host 0.0.0.0 --port 80 --proxy-headers --log-config /src/logging.yaml
