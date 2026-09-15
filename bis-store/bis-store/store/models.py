"""
=============================================================================
 DESIGN PATTERN #1 -- MVT / MVC  ->  THE "M" LAYER  (architectural)
=============================================================================

This file is the Model layer of Django's MVT architecture.

Rule this file obeys: it knows nothing about HTTP. There is no import of
`django.http`, no `request`, no template name, no URL. It only describes what
the data *is* and what the business rules *are*. You could import this module
from a CLI script or a unit test and it would work unchanged.

Django's MVT vs the classic MVC in the instructor's example:

    classic MVC          Django MVT           in this project
    -----------          ----------           ---------------
    Model                Model                store/models.py      <- you are here
    View (presentation)  Template             store/templates/
    Controller           View                 store/views.py

Normally Django's Model layer is built on `django.db.models.Model` and maps to
database tables. The lab explicitly allows hardcoded data with no database, so
these are plain dataclasses instead. The architectural role is identical: this
is still the only place that owns the shape of the data and the rules about
it, and the layer above it (`store/views.py`) never reaches past it.

`Checkout` at the bottom of this file is also the CONTEXT of the Strategy
pattern -- it holds a `ShippingStrategy` and delegates the shipping
calculation to it instead of computing it itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from store.patterns.shipping import (
    DEFAULT_STRATEGY_CODE,
    ShippingStrategy,
    get_strategy,
    money,
)

TAX_RATE = Decimal("0.16")  # IVA


@dataclass
class Product:
    sku: str
    name: str
    category: str
    price: Decimal
    weight_kg: Decimal
    stock: int
    emoji: str = "📦"

    @property
    def in_stock(self) -> bool:
        return self.stock > 0


@dataclass
class CartLine:
    product: Product
    quantity: int

    @property
    def line_total(self) -> Decimal:
        return money(self.product.price * self.quantity)

    @property
    def line_weight(self) -> Decimal:
        return self.product.weight_kg * self.quantity


@dataclass
class ShoppingCart:
    lines: list[CartLine] = field(default_factory=list)

    def line_for(self, sku: str) -> CartLine | None:
        return next((l for l in self.lines if l.product.sku == sku), None)

    @property
    def is_empty(self) -> bool:
        return not self.lines

    @property
    def item_count(self) -> int:
        return sum(l.quantity for l in self.lines)

    @property
    def subtotal(self) -> Decimal:
        return money(sum((l.line_total for l in self.lines), Decimal("0")))

    @property
    def total_weight(self) -> Decimal:
        return sum((l.line_weight for l in self.lines), Decimal("0"))


@dataclass
class Checkout:
    """Context object of the Strategy pattern.

    It does not know how shipping is priced. It owns a `ShippingStrategy` and
    asks it. Changing `strategy_code` swaps the algorithm at runtime.
    """

    cart: ShoppingCart
    strategy_code: str = DEFAULT_STRATEGY_CODE

    @property
    def strategy(self) -> ShippingStrategy:
        return get_strategy(self.strategy_code)

    @property
    def shipping_available(self) -> bool:
        return self.strategy.is_available(self.cart.subtotal, self.cart.total_weight)

    @property
    def shipping_cost(self) -> Decimal:
        if self.cart.is_empty or not self.shipping_available:
            return Decimal("0.00")
        # <<< the delegation that makes this Strategy and not an if-chain >>>
        return self.strategy.calculate(self.cart.subtotal, self.cart.total_weight)

    @property
    def tax(self) -> Decimal:
        return money(self.cart.subtotal * TAX_RATE)

    @property
    def total(self) -> Decimal:
        return money(self.cart.subtotal + self.tax + self.shipping_cost)

    def quote_all_strategies(self) -> list[dict]:
        """Price the cart with every strategy so the UI can compare them.

        This is only possible because the algorithms share one interface --
        the same loop works for options that do not exist yet.
        """
        subtotal = self.cart.subtotal
        weight = self.cart.total_weight
        quotes = []
        for code, strategy in _all_strategies().items():
            available = strategy.is_available(subtotal, weight)
            quotes.append(
                {
                    "code": code,
                    "label": strategy.label,
                    "eta": strategy.eta,
                    "description": strategy.description,
                    "cost": strategy.calculate(subtotal, weight) if available else None,
                    "available": available,
                    "reason": "" if available else strategy.unavailable_reason(),
                    "selected": code == self.strategy_code,
                }
            )
        return quotes

    def build_order(self, order_number: int) -> dict:
        """Freeze the current cart into an immutable order summary."""
        return {
            "number": f"BIS-{order_number:04d}",
            "lines": [
                {
                    "name": l.product.name,
                    "quantity": l.quantity,
                    "unit_price": l.product.price,
                    "line_total": l.line_total,
                }
                for l in self.cart.lines
            ],
            "item_count": self.cart.item_count,
            "subtotal": self.cart.subtotal,
            "tax": self.tax,
            "shipping_label": self.strategy.label,
            "shipping_eta": self.strategy.eta,
            "shipping_cost": self.shipping_cost,
            "total": self.total,
        }


def _all_strategies():
    # imported lazily to keep the module import graph obvious
    from store.patterns.shipping import SHIPPING_STRATEGIES

    return SHIPPING_STRATEGIES
