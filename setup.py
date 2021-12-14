from setuptools import setup, find_packages
import re

with open('opensearch_stac_adapter/__init__.py', 'r') as fd:
    __version__ = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', fd.read(), re.MULTILINE).group(1)

version = __version__

setup(
    name="opensearch-stac-adapter",
    version=version,
    author="Stijn Caerts",
    author_email="stijn.caerts@vito.be",
    description="OpenSearch to STAC adapter",
    url="https://github.com/VITObelgium/opensearch-stac-adapter",
    packages=find_packages(),
    install_requires=[
        "attrs",
        "terracatalogueclient==0.1.7",
        "stac-fastapi.api==2.2.0",
        "stac-fastapi.types==2.2.0",
        "stac-fastapi.extensions==2.2.0",
        "uvicorn[standard]",
        "jsonpath-ng"
    ],
    tests_require=[
        "pytest",
        "pytest-asyncio"
    ],
)
