from collections.abc import Callable
from typing import Any

from fastapi import APIRouter


class DualSlashAPIRouter(APIRouter):
    """
    Registers both `/path` and `/path/` for every endpoint.

    This avoids 307 redirects between trailing/non-trailing slash variants,
    which can cause some clients to drop Authorization headers on redirect.
    """

    def add_api_route(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        super().add_api_route(path, endpoint, **kwargs)

        if path == "/":
            return

        alt_path = path[:-1] if path.endswith("/") else f"{path}/"
        if not alt_path:
            alt_path = "/"

        alt_kwargs = dict(kwargs)
        alt_kwargs["include_in_schema"] = False
        super().add_api_route(alt_path, endpoint, **alt_kwargs)
