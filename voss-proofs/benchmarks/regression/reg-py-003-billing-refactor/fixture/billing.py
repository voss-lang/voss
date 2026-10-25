def invoice_line(description: str, cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    amount = f"{sign}${cents // 100:,}.{cents % 100:02d}"
    return f"{description:<30}{amount:>12}"


def receipt_line(description: str, cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    amount = f"{sign}${cents // 100:,}.{cents % 100:02d}"
    return f"{description}: {amount}"
