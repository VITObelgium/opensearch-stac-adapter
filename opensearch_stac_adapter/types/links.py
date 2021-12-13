import attr
from typing import Optional, List, Dict, Any
from starlette.requests import Request

from stac_pydantic.links import Relations


@attr.s
class PagingLinks():
    """Links for paging."""
    request: Request = attr.ib()
    next_token: Optional[int] = attr.ib(kw_only=True, default=None)
    body: Dict[str, Any] = attr.ib(kw_only=True, default=None)

    def next(self) -> Optional[Dict[str, Any]]:
        """Create `next` link."""
        if self.next_token is not None:
            method = self.request.method
            if method == "GET":
                return {
                    "rel": Relations.next.value,
                    "method": method,
                    "href": str(self.request.url.include_query_params(token=self.next_token))
                }
            elif method == "POST":
                return {
                    "rel": Relations.next.value,
                    "method": method,
                    "href": str(self.request.url),
                    "body": {
                        **self.body,
                        "token": self.next_token,
                    }
                }

        return None

    def create_links(self) -> List[Dict[str, Any]]:
        """Return all links."""
        links = []
        next_link = self.next()
        if next_link is not None:
            links.append(next_link)
        return links
