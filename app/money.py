from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


CENT_QUANT = Decimal("0.01")
WHOLE_DOLLAR_QUANT = Decimal("1")


def parse_amount(text: str) -> Decimal:
    cleaned = text.strip().replace(",", "")
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    value = Decimal(cleaned)
    return -value if negative else value


def round_money(value: Decimal, whole_dollars: bool) -> Decimal:
    quant = WHOLE_DOLLAR_QUANT if whole_dollars else CENT_QUANT
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def format_money(value: Decimal, whole_dollars: bool) -> str:
    rounded = round_money(value, whole_dollars)
    sign = "-" if rounded < 0 else ""
    absolute = abs(rounded)
    if whole_dollars:
        return f"{sign}${absolute:,.0f}"
    return f"{sign}${absolute:,.2f}"


def format_percent(rate: Decimal) -> str:
    percent = rate * Decimal("100")
    if percent == percent.quantize(Decimal("1")):
        return f"{percent:.0f}%"
    return f"{percent.normalize()}%"
