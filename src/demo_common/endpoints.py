import re
from urllib.parse import urlparse


def require_demo_app_url(url: str, resource_name: str) -> str:
    parsed = urlparse(url)
    pattern = rf"{re.escape(resource_name)}(?:-[a-z0-9]+)?(?:\.[a-z0-9-]+)?\.azurewebsites\.net"
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not re.fullmatch(pattern, parsed.hostname)
        or parsed.port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Refusing access to a non-demo application endpoint.")
    return url.rstrip("/")
