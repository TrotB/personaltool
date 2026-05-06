from __future__ import annotations

import re
from decimal import Decimal

from models import InstructionPlan, PriceMatch
from money import parse_amount


PRICE_WORDS = (
    "amount",
    "balance",
    "bid",
    "budget",
    "charge",
    "cost",
    "estimate",
    "fee",
    "invoice",
    "price",
    "quote",
    "rate",
    "subtotal",
    "total",
)

AMOUNT_PATTERN = r"(?:\(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?\)|\(\d+(?:\.\d{1,2})?\)|\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"

CURRENCY_VALUE_RE = re.compile(
    rf"""
    (?<![\w.])
    (?:
        (?P<prefix>(?:USD|CAD|US\$|C\$|\$)\s*)
        (?P<prefix_amount>{AMOUNT_PATTERN})
        |
        (?P<suffix_amount>{AMOUNT_PATTERN})
        \s*(?P<suffix>USD|CAD)
    )
    (?!\w)
    """,
    re.IGNORECASE | re.VERBOSE,
)

KEYWORD_NUMBER_RE = re.compile(rf"(?<![\w.])(?P<amount>{AMOUNT_PATTERN})(?!\w)", re.VERBOSE)

PLAIN_PRICE_RE = re.compile(
    rf"""
    (?ix)
    \b(?:amount|bid|budget|charge|cost|estimate|fee|invoice|price|quote|rate|subtotal|total)\b
    \s*(?:[:=#-]|\bis\b|\bof\b|\bat\b|\bfor\b)?\s*
    (?P<amount>{AMOUNT_PATTERN})
    |
    (?P<amount_before>{AMOUNT_PATTERN})
    \s*(?:[:=#-]|\bis\b|\bof\b|\bat\b|\bfor\b)?\s*
    \b(?:amount|bid|budget|charge|cost|estimate|fee|invoice|price|quote|rate|subtotal|total)\b
    """,
    re.VERBOSE,
)


def find_prices_in_text(text: str, plan: InstructionPlan, context_hint: str = "") -> list[PriceMatch]:
    matches: list[PriceMatch] = []
    occupied_ranges: list[tuple[int, int]] = []
    allow_plain_amounts = has_price_context(context_hint)

    for match in CURRENCY_VALUE_RE.finditer(text):
        amount_text = match.group("prefix_amount") or match.group("suffix_amount")
        if not amount_text:
            continue
        if is_currency_noise(text, match.start(), match.end()):
            continue
        matches.append(build_price_match(text, match.start(), match.end(), amount_text, match.group(0).strip(), plan, context_hint))
        occupied_ranges.append((match.start(), match.end()))

    for match in KEYWORD_NUMBER_RE.finditer(text):
        if any(start <= match.start() < end for start, end in occupied_ranges):
            continue
        amount_text = match.group("amount")
        if is_plain_number_noise(text, match.start(), match.end(), amount_text):
            continue
        if not has_plain_price_label(text, match.start(), match.end()) and not (
            allow_plain_amounts and is_likely_price_amount(amount_text) and is_plain_amount_cell(text)
        ):
            continue
        matches.append(build_price_match(text, match.start(), match.end(), amount_text, match.group(0).strip(), plan, context_hint))

    return sorted(matches, key=lambda item: item.start)


def build_price_match(
    text: str,
    start: int,
    end: int,
    amount_text: str,
    original_text: str,
    plan: InstructionPlan,
    context_hint: str = "",
) -> PriceMatch:
    value = parse_amount(amount_text)
    context = compact_context(text, start, end)
    label = infer_label(text, start, end)
    if not is_useful_label(label):
        label = context_hint
    multiplier = choose_multiplier(label, f"{context_hint} {context}", plan)
    return PriceMatch(
        original_text=original_text,
        original_value=value,
        marked_up_value=value * multiplier,
        multiplier=multiplier,
        label=label,
        context=context,
        start=start,
        end=end,
    )


def choose_multiplier(label: str, context: str, plan: InstructionPlan) -> Decimal:
    normalized_label = normalize_text(label)
    normalized_context = normalize_text(context)
    best_multiplier = plan.default_multiplier
    best_score = 0
    for rule in plan.specific_rules:
        normalized_rule = normalize_text(rule.label)
        score = label_match_score(normalized_rule, normalized_label)
        if score == 0 and not normalized_label:
            score = exact_phrase_score(normalized_rule, normalized_context)
        if score > best_score:
            best_score = score
            best_multiplier = rule.multiplier
    return best_multiplier


def label_match_score(rule_label: str, context: str) -> int:
    if not rule_label:
        return 0
    if rule_label in context:
        return len(rule_label.split()) + 10
    generic_words = {"and", "product", "products", "price", "prices", "markup", "mark", "up", "item", "items"}
    words = [word for word in rule_label.split() if len(word) > 2 and word not in generic_words]
    if not words:
        return 0
    matched = sum(1 for word in words if word in context)
    if " and " in f" {rule_label} " and matched >= 1:
        return matched
    required = len(words) if len(words) <= 2 else 2
    if matched < required:
        return 0
    return matched


def exact_phrase_score(rule_label: str, context: str) -> int:
    if rule_label and rule_label in context:
        return len(rule_label.split())
    return 0


def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def compact_context(text: str, start: int, end: int, radius: int = 120) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    snippet = " ".join(text[left:right].split())
    if left > 0:
        snippet = "..." + snippet
    if right < len(text):
        snippet += "..."
    return snippet


def infer_label(text: str, start: int, end: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end].strip()
    label = line[: max(0, start - line_start)].strip(" :-\t")
    if label:
        return " ".join(label.split())[-100:]
    return " ".join(line.split())[:100]


def is_useful_label(label: str) -> bool:
    if not label:
        return False
    without_prices = CURRENCY_VALUE_RE.sub("", label)
    without_numbers = KEYWORD_NUMBER_RE.sub("", without_prices)
    return bool(re.search(r"[A-Za-z]{3,}", without_numbers))


def is_likely_year(amount_text: str) -> bool:
    if "," in amount_text or "." in amount_text or amount_text.startswith("("):
        return False
    try:
        value = int(amount_text)
    except ValueError:
        return False
    return 1900 <= value <= 2099


def has_price_context(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:price|prices|amount|total|subtotal|quote|estimate|proposal|cost|fee|charge|deposit|balance|cad|cdn|hst|tax)\b|\$",
            text,
            re.IGNORECASE,
        )
    )


def is_likely_price_amount(amount_text: str) -> bool:
    clean = amount_text.strip()
    if is_likely_year(clean):
        return False
    if "." in clean or "," in clean:
        return True
    try:
        value = abs(parse_amount(clean))
    except Exception:
        return False
    return value >= Decimal("20")


def is_plain_amount_cell(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    without_amounts = KEYWORD_NUMBER_RE.sub("", stripped)
    without_symbols = re.sub(r"[\s,$().:/|\\-]+", "", without_amounts)
    return without_symbols == ""


def is_plain_number_noise(text: str, start: int, end: int, amount_text: str) -> bool:
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    after_window = text[end : min(len(text), end + 12)].lower()
    clean = amount_text.strip()

    if is_likely_year(clean):
        return True
    if (before and before in ("%/#xX")) or (after and after in ("%/#xX\"'")):
        return True
    if re.match(r"\.\s*--", after_window):
        return True
    if re.match(r"\s*(?:ft|ft²|sq|sf|mm|cm|m|in|inch|inches|lbs?|kg|x)\b", after_window):
        return True
    if before.isalpha() or after.isalpha():
        return True
    return False


def is_currency_noise(text: str, start: int, end: int) -> bool:
    after_window = text[end : min(len(text), end + 8)]
    before_window = text[max(0, start - 8) : start]
    if re.match(r"\.\s*--", after_window):
        return True
    if re.search(r"[A-Za-z]\s*$", before_window) and re.match(r"\s*[A-Za-z0-9.-]", after_window):
        return True
    return False


def has_plain_price_label(text: str, start: int, end: int) -> bool:
    search_start = max(0, start - 40)
    search_end = min(len(text), end + 40)
    window = text[search_start:search_end]
    local_start = start - search_start
    local_end = end - search_start

    for match in PLAIN_PRICE_RE.finditer(window):
        amount_group = "amount" if match.group("amount") is not None else "amount_before"
        amount_start, amount_end = match.span(amount_group)
        if amount_start == local_start and amount_end == local_end:
            return True
    return False
