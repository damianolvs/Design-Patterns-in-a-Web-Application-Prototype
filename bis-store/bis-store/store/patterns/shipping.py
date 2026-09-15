"""
=============================================================================
 DESIGN PATTERN #3 -- STRATEGY  (behavioural)
=============================================================================

Problem this solves in BIS Store
--------------------------------
Shipping is not one formula. Standard delivery charges a flat fee plus a
per-kilo rate and becomes free above a certain subtotal; express delivery is
more expensive and never free; store pickup costs nothing but only works for
carts that are not too heavy.

The naive version of this is a chain of `if method == "express": ...` inside
the checkout view. That has three problems:

  * the view grows every time the business adds a shipping option,
  * pricing rules end up mixed with HTTP handling code,
  * you cannot test a single pricing rule in isolation.

Strategy fixes that: every algorithm becomes its own class behind a common
interface, and the object that needs a shipping cost (the Checkout context in
`store/models.py`) just holds a reference to one of them and calls
`calculate()`. Swapping the algorithm at runtime is a single assignment.

Why this is Strategy and not Factory
------------------------------------
`SHIPPING_STRATEGIES` below is a lookup table, not a factory: it does not
decide *how* to build anything, it hands back an already-configured strategy
object. What is being demonstrated is the interchangeable algorithm plus the
context that delegates to it, which is Strategy.

To add "same-day drone delivery" you write one new class and add one line to
the registry. No view, template or model changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import ROUND_HALF_UP, Decimal


def money(value: Decimal) -> Decimal:
    """Round to two decimals the way money should be rounded."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ShippingStrategy(ABC):
    """The common interface every shipping algorithm must implement."""

    code: str = ""
    label: str = ""
    eta: str = ""
    description: str = ""

    @abstractmethod
    def calculate(self, subtotal: Decimal, total_weight: Decimal) -> Decimal:
        """Return the shipping cost for this cart."""

    def is_available(self, subtotal: Decimal, total_weight: Decimal) -> bool:
        """A strategy may refuse a cart. Default: always available."""
        return True

    def unavailable_reason(self) -> str:
        return ""


class StandardShipping(ShippingStrategy):
    """Flat fee + per-kilo rate, free once the cart is big enough."""

    code = "standard"
    label = "Standard"
    eta = "3-5 business days"
    description = "$99 base + $18/kg — free over $2,500"

    BASE_FEE = Decimal("99.00")
    PER_KILO = Decimal("18.00")
    FREE_FROM = Decimal("2500.00")

    def calculate(self, subtotal: Decimal, total_weight: Decimal) -> Decimal:
        if subtotal >= self.FREE_FROM:
            return Decimal("0.00")
        return money(self.BASE_FEE + self.PER_KILO * total_weight)


class ExpressShipping(ShippingStrategy):
    """Higher fee, heavier per-kilo rate, never free."""

    code = "express"
    label = "Express"
    eta = "24 hours"
    description = "$219 base + $35/kg — no free threshold"

    BASE_FEE = Decimal("219.00")
    PER_KILO = Decimal("35.00")

    def calculate(self, subtotal: Decimal, total_weight: Decimal) -> Decimal:
        return money(self.BASE_FEE + self.PER_KILO * total_weight)


class StorePickup(ShippingStrategy):
    """Free, but the customer has to be able to carry it."""

    code = "pickup"
    label = "Store pickup"
    eta = "Ready in 2 hours"
    description = "Free — carts under 8 kg only"

    MAX_WEIGHT = Decimal("8.00")

    def calculate(self, subtotal: Decimal, total_weight: Decimal) -> Decimal:
        return Decimal("0.00")

    def is_available(self, subtotal: Decimal, total_weight: Decimal) -> bool:
        return total_weight <= self.MAX_WEIGHT

    def unavailable_reason(self) -> str:
        return f"cart is over {self.MAX_WEIGHT} kg"


# Registry of available strategies. Adding an option = adding one line here.
SHIPPING_STRATEGIES: dict[str, ShippingStrategy] = {
    StandardShipping.code: StandardShipping(),
    ExpressShipping.code: ExpressShipping(),
    StorePickup.code: StorePickup(),
}

DEFAULT_STRATEGY_CODE = StandardShipping.code


def get_strategy(code: str) -> ShippingStrategy:
    """Look up a strategy, falling back to the default for unknown codes."""
    return SHIPPING_STRATEGIES.get(code, SHIPPING_STRATEGIES[DEFAULT_STRATEGY_CODE])
