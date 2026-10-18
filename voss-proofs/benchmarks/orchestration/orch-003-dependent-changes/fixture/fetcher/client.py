from collections.abc import Callable

from .settings import Settings


class Client:
    def __init__(self, settings: Settings, send: Callable[[str, float], str]) -> None:
        self.settings = settings
        self._send = send

    def get(self, url: str) -> str:
        attempts = 1 + 3
        for attempt in range(attempts):
            try:
                return self._send(url, self.settings.timeout)
            except ConnectionError:
                if attempt == attempts - 1:
                    raise
        raise AssertionError("unreachable")
