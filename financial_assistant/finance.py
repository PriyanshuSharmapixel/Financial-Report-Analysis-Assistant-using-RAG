"""Transparent arithmetic on user-verified report figures.

The user supplies values and source pages; this module does not claim to parse
financial statement tables or infer whether a number is consolidated.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Figure:
    value: Decimal
    company: str
    fiscal_year: str
    currency: str
    unit: str
    basis: str
    document: str
    page: int

    def __post_init__(self) -> None:
        if not self.value.is_finite():
            raise ValueError("Figure must be finite")
        if self.page < 1 or not all((self.company, self.fiscal_year, self.currency,
                                      self.unit, self.basis, self.document)):
            raise ValueError("Each figure needs metadata and a one-based PDF page")

    @property
    def source(self) -> str:
        return f"{self.document}, PDF p. {self.page}"


@dataclass(frozen=True)
class Calculation:
    label: str
    value: Decimal
    formula: str
    sources: tuple[str, ...]


def _compatible(a: Figure, b: Figure, *, same_year: bool) -> None:
    for field in ("company", "currency", "unit", "basis"):
        if getattr(a, field).strip().casefold() != getattr(b, field).strip().casefold():
            raise ValueError(f"Figures have different {field}; reconcile them before calculating")
    if same_year and a.fiscal_year != b.fiscal_year:
        raise ValueError("Figures must cover the same fiscal year")
    if not same_year and a.fiscal_year == b.fiscal_year:
        raise ValueError("Revenue growth needs two distinct fiscal years")


def revenue_growth(current: Figure, previous: Figure) -> Calculation:
    _compatible(current, previous, same_year=False)
    if previous.value <= 0:
        raise ValueError("Previous revenue must be positive; a nonpositive base is misleading")
    value = (current.value - previous.value) / previous.value * 100
    return Calculation("Revenue growth", value,
                       f"(({current.value} - {previous.value}) / {previous.value}) × 100",
                       (current.source, previous.source))


def _margin(profit: Figure, revenue: Figure, label: str) -> Calculation:
    _compatible(profit, revenue, same_year=True)
    if revenue.value <= 0:
        raise ValueError("Revenue must be positive")
    value = profit.value / revenue.value * 100
    return Calculation(label, value, f"({profit.value} / {revenue.value}) × 100",
                       (profit.source, revenue.source))


def net_profit_margin(net_profit: Figure, revenue: Figure) -> Calculation:
    return _margin(net_profit, revenue, "Net profit margin")


def operating_margin(operating_profit: Figure, revenue: Figure) -> Calculation:
    return _margin(operating_profit, revenue, "Operating margin")
