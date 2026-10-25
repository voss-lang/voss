"""Tiny request router used by the service layer."""


def handle(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    if method == "GET" and path == "/health":
        return 200, {"status": "ok"}
    return 404, {"error": "not found"}
