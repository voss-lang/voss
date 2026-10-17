def page_count(total: int, per_page: int) -> int:
    """Number of pages needed to show `total` items, `per_page` at a time."""
    return total // per_page
