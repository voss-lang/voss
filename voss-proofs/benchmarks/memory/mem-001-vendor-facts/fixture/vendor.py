BASE_URL = "https://api.acme.test/"
RATE_LIMIT_PER_SECOND = None


def build_url(path: str) -> str:
    return BASE_URL + path


def build_request(path: str) -> dict:
    return {"url": build_url(path), "headers": {}}
