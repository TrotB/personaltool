from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class PricingRule:
    label: str
    multiplier: Decimal


@dataclass(frozen=True)
class TotalsPlan:
    add_net_total: bool = False
    hst_rate: Decimal | None = None
    add_grand_total: bool = False
    add_deposit: bool = False
    deposit_rate: Decimal | None = None
    deposit_amount: Decimal | None = None
    deposit_adjustment: Decimal = Decimal("0")
    add_balance: bool = False


@dataclass(frozen=True)
class InstructionPlan:
    original_text: str
    default_multiplier: Decimal = Decimal("1")
    specific_rules: tuple[PricingRule, ...] = ()
    totals: TotalsPlan = field(default_factory=TotalsPlan)


@dataclass(frozen=True)
class PriceMatch:
    original_text: str
    original_value: Decimal
    marked_up_value: Decimal
    multiplier: Decimal
    label: str
    context: str
    start: int
    end: int


@dataclass(frozen=True)
class ProcessOptions:
    round_to_whole_dollar: bool


@dataclass(frozen=True)
class ProcessResult:
    output_path: Path
    price_count: int
    net_total: Decimal
    warnings: tuple[str, ...] = ()
