from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from models import InstructionPlan, PricingRule, TotalsPlan
from money import parse_amount


MULTIPLIER_RE = re.compile(
    r"""
    (?:
        (?:by|x|times|multiply(?:\s+by)?|multiplied\s+by|multiplier(?:\s+of)?|should\s+be|at|to)\s*
    )?
    (?P<number>\d+(?:\.\d+)?)
    \s*(?:x|times)?
    """,
    re.IGNORECASE | re.VERBOSE,
)
PERCENT_RE = re.compile(r"(?P<number>\d+(?:\.\d+)?)\s*%", re.IGNORECASE)
HST_RE = re.compile(r"\b(?:hst|tax)\b(?:\s*(?:at|of|=|:))?\s*(?P<number>\d+(?:\.\d+)?)\s*%", re.IGNORECASE)
DEPOSIT_RE = re.compile(
    r"\bdeposit\b(?:\s*(?:at|of|=|:))?\s*(?:(?P<percent>\d+(?:\.\d+)?)\s*%|\$?\s*(?P<amount>\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?))?",
    re.IGNORECASE,
)
CHANGE_MARKUP_RE = re.compile(
    r"\b(?:change|set|make|adjust)\s+(?P<label>[A-Za-z][A-Za-z0-9 &/().,'-]{1,80}?)\s+"
    r"(?:markup|mark\s*up|multiplier|price\s*markup)\s+(?:to|at|=)\s+(?P<number>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
DEPOSIT_ADJUSTMENT_RE = re.compile(
    r"\b(?P<direction>add|increase|plus|subtract|deduct|remove|minus)\s+\$?\s*"
    r"(?P<amount>\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\s+"
    r"(?:to|from)?\s*(?:the\s+)?deposit\b",
    re.IGNORECASE,
)
DEPOSIT_SET_RE = re.compile(
    r"\b(?:set|change|make|adjust)\s+(?:the\s+)?deposit\s+(?:to|at|=)\s+\$?\s*"
    r"(?P<amount>\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)


def parse_instructions(text: str) -> InstructionPlan:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        raise ValueError("Describe what you want done before processing the document.")

    default_multiplier = find_default_multiplier(cleaned)
    specific_rules = tuple(find_specific_rules(cleaned, default_multiplier))
    totals = find_totals_plan(cleaned)
    return InstructionPlan(
        original_text=cleaned,
        default_multiplier=default_multiplier,
        specific_rules=specific_rules,
        totals=totals,
    )


def find_default_multiplier(text: str) -> Decimal:
    lower = CHANGE_MARKUP_RE.sub("", text).lower()
    markup_percent = re.search(r"\b(?:markup|mark up|increase|raise)\b.{0,24}?(?P<number>\d+(?:\.\d+)?)\s*%", lower)
    if markup_percent:
        return Decimal("1") + Decimal(markup_percent.group("number")) / Decimal("100")

    for pattern in (
        r"\b(?:markup|mark up|multiply|multiplied|multiplier|times)\b.{0,35}?(?P<number>\d+(?:\.\d+)?)",
        r"\ball\s+prices\b.{0,35}?(?P<number>\d+(?:\.\d+)?)",
    ):
        match = re.search(pattern, lower)
        if match:
            number = as_decimal(match.group("number"))
            if number is not None and number > 0:
                return number

    return Decimal("1")


def find_specific_rules(text: str, default_multiplier: Decimal) -> list[PricingRule]:
    rules: list[PricingRule] = []
    for match in CHANGE_MARKUP_RE.finditer(text):
        multiplier = as_decimal(match.group("number"))
        label = clean_label(match.group("label"))
        if label and multiplier and Decimal("0.01") < multiplier < Decimal("10"):
            rules.append(PricingRule(label=label, multiplier=multiplier))

    fragments = re.split(r"\b(?:except|but|however)\b", text, flags=re.IGNORECASE)
    for fragment in fragments[1:]:
        for part in re.split(r"\b(?:and except|, except|; except)\b", fragment, flags=re.IGNORECASE):
            rule = parse_rule_fragment(part)
            if rule and rule.multiplier != default_multiplier:
                rules.append(rule)

    named_rules = re.finditer(
        r"(?P<label>[A-Za-z][A-Za-z0-9 &/().,'-]{2,80}?)\s+(?:should\s+be|is|at|to|by|x|times)\s+(?P<number>\d+(?:\.\d+)?)",
        text,
        flags=re.IGNORECASE,
    )
    for match in named_rules:
        label = clean_label(match.group("label"))
        multiplier = as_decimal(match.group("number"))
        if (
            label
            and multiplier
            and multiplier != default_multiplier
            and not looks_like_total_label(label)
            and not re.search(r"\b(?:except|but|however|markup|mark up|multiply|multiplied|all prices)\b", label, re.IGNORECASE)
        ):
            rules.append(PricingRule(label=label, multiplier=multiplier))

    return dedupe_rules(rules)


def parse_rule_fragment(fragment: str) -> PricingRule | None:
    multiplier_match = None
    for match in MULTIPLIER_RE.finditer(fragment):
        number = as_decimal(match.group("number"))
        if number is not None and Decimal("0.01") < number < Decimal("10"):
            multiplier_match = match
            break
    if not multiplier_match:
        return None

    label = fragment[: multiplier_match.start()]
    label = re.sub(r"\b(?:which|that|it|they|prices?|line\s*items?)\b", " ", label, flags=re.IGNORECASE)
    label = clean_label(label)
    if not label or looks_like_total_label(label):
        return None
    return PricingRule(label=label, multiplier=as_decimal(multiplier_match.group("number")) or Decimal("1"))


def find_totals_plan(text: str) -> TotalsPlan:
    lower = text.lower()
    hst_match = HST_RE.search(text)
    hst_rate = Decimal(hst_match.group("number")) / Decimal("100") if hst_match else None

    deposit_match = DEPOSIT_RE.search(text)
    deposit_set_match = DEPOSIT_SET_RE.search(text)
    add_deposit = deposit_match is not None
    deposit_rate = None
    deposit_amount = None
    if deposit_set_match:
        add_deposit = True
        deposit_amount = parse_amount(deposit_set_match.group("amount"))
    elif deposit_match:
        if deposit_match.group("percent"):
            deposit_rate = Decimal(deposit_match.group("percent")) / Decimal("100")
        elif deposit_match.group("amount"):
            deposit_amount = parse_amount(deposit_match.group("amount"))
        else:
            deposit_rate = Decimal("0.50")

    deposit_adjustment = Decimal("0")
    for adjustment_match in DEPOSIT_ADJUSTMENT_RE.finditer(text):
        add_deposit = True
        amount = parse_amount(adjustment_match.group("amount"))
        direction = adjustment_match.group("direction").lower()
        if direction in {"subtract", "deduct", "remove", "minus"}:
            amount = -amount
        deposit_adjustment += amount

    add_net_total = bool(re.search(r"\b(net\s+total|subtotal|total\s+cost)\b", lower))
    add_grand_total = bool(re.search(r"\b(grand\s+total|final\s+total|\btotal\b)\b", lower)) or hst_rate is not None
    add_balance = "balance" in lower or add_deposit
    if add_deposit and deposit_rate is None and deposit_amount is None:
        deposit_rate = Decimal("0.50")

    return TotalsPlan(
        add_net_total=add_net_total or hst_rate is not None or add_deposit or add_balance,
        hst_rate=hst_rate,
        add_grand_total=add_grand_total,
        add_deposit=add_deposit,
        deposit_rate=deposit_rate,
        deposit_amount=deposit_amount,
        deposit_adjustment=deposit_adjustment,
        add_balance=add_balance,
    )


def as_decimal(text: str) -> Decimal | None:
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def clean_label(text: str) -> str:
    label = re.sub(r"\b(?:which|that)?\s*(?:should|would|will|must|needs?)\b.*$", "", text, flags=re.IGNORECASE)
    label = re.sub(r"^[\s,.;:-]+|[\s,.;:-]+$", "", label)
    label = re.sub(r"\s+", " ", label)
    return label.strip(" \"'")


def looks_like_total_label(label: str) -> bool:
    return bool(re.search(r"\b(total|subtotal|hst|tax|deposit|balance|markup|prices?)\b", label, re.IGNORECASE))


def dedupe_rules(rules: list[PricingRule]) -> list[PricingRule]:
    positions: dict[str, int] = {}
    deduped: list[PricingRule] = []
    for rule in rules:
        key = rule.label.lower()
        if key in positions:
            deduped[positions[key]] = rule
        else:
            positions[key] = len(deduped)
            deduped.append(rule)
    return deduped
