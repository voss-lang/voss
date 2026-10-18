class Inventory:
    def __init__(self) -> None:
        self._entries: list[tuple[str, int]] = []

    def add(self, sku: str, qty: int) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        self._entries.append((sku, qty))

    def quantity(self, sku: str) -> int:
        return sum(q for s, q in self._entries if s == sku)
