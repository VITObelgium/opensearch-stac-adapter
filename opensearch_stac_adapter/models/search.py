from stac_pydantic.api import Search
from typing import Optional
from stac_pydantic.api.extensions.fields import FieldsExtension


class AdaptedSearch(Search):
    """Search model"""
    token: Optional[str] = None
    field: Optional[FieldsExtension] = None
