"""
=============================================================================
 DESIGN PATTERN #2 -- SINGLETON  (creational)
=============================================================================

Problem this solves in BIS Store
--------------------------------
The prototype keeps the whole catalogue, the shopping cart and an activity
log in memory (no database, per the lab requirements). Every HTTP request
handled by Django must see exactly the same data: if a request added a
product to the cart, the next request has to find it there.

If each request built its own `StoreState()` the cart would reset on every
click. Singleton guarantees one -- and only one -- state object for the whole
process, and gives every module a controlled way to reach it.

How the pattern is enforced here
--------------------------------
1. `_instance` is a private class attribute that holds the only instance.
2. `__init__` refuses to run a second time -- this is the Python equivalent
   of the "private constructor" used in the instructor's TypeScript example.
3. `get_instance()` is the single public access point. It uses a lock plus
   double-checked locking so two concurrent requests cannot create two
   objects.
4. `instance_id` and `access_count` exist purely as proof for the demo:
   the id never changes and the counter keeps growing, which shows the same
   object is accumulating state across requests.

Known trade-off (be ready to say this out loud in the demo)
-----------------------------------------------------------
A Python module is already cached by the interpreter, so a module-level
object behaves like a singleton "by accident". We implement the pattern
explicitly anyway because the guarantee then lives in the class itself
instead of depending on import mechanics -- `StoreState()` raises instead of
quietly giving you a second, broken copy.

Also: the singleton is per *process*. Running Django under Gunicorn with 4
workers would give 4 independent carts. That is fine for a single-user
prototype and is exactly the "hidden global state" risk the lab guide warns
about in section 4.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime
from decimal import Decimal

from store.models import CartLine, Product, ShoppingCart
from store.patterns.shipping import DEFAULT_STRATEGY_CODE


class StoreState:
    """The single source of truth for the whole prototype."""

    # -- Singleton machinery -------------------------------------------------
    _instance: "StoreState | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        # "Private constructor": once the singleton exists, block any attempt
        # to build a second one. Comment this block out during the demo and
        # you will see the instance_id change on every request.
        if StoreState._instance is not None:
            raise RuntimeError(
                "StoreState is a Singleton. Use StoreState.get_instance() "
                "instead of StoreState()."
            )

        self.instance_id: str = uuid.uuid4().hex[:8]
        self.created_at: datetime = datetime.now()
        self.access_count: int = 0

        self._products: list[Product] = _seed_catalogue()
        self.cart: ShoppingCart = ShoppingCart()
        self.activity_log: list[str] = []
        self.last_order: dict | None = None

        # currently selected Strategy (see store/patterns/shipping.py)
        self.selected_shipping: str = DEFAULT_STRATEGY_CODE
        # filled by the "try a second instance" demo button
        self.singleton_error: str = ""

        self.log(f"StoreState created (instance_id={self.instance_id})")

    @classmethod
    def get_instance(cls) -> "StoreState":
        """The one and only way to obtain the state object."""
        if cls._instance is None:  # fast path, no lock needed
            with cls._lock:
                if cls._instance is None:  # double-checked locking
                    cls._instance = cls()
        cls._instance.access_count += 1
        return cls._instance

    @classmethod
    def reset(cls) -> "StoreState":
        """Throw the singleton away and rebuild it. Used by the Reset button.

        This is a deliberate escape hatch for the demo, not part of the
        pattern. Real singletons usually expose something like this for tests.
        """
        with cls._lock:
            cls._instance = None
        return cls.get_instance()

    # -- Catalogue access ----------------------------------------------------
    def products(self) -> list[Product]:
        return self._products

    def find_product(self, sku: str) -> Product | None:
        return next((p for p in self._products if p.sku == sku), None)

    # -- Activity log --------------------------------------------------------
    def log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.append(f"[{stamp}] {message}")
        # keep the panel readable
        self.activity_log = self.activity_log[-12:]

    # -- Cart operations -----------------------------------------------------
    def add_to_cart(self, sku: str, quantity: int = 1) -> str:
        product = self.find_product(sku)
        if product is None:
            return f"Unknown SKU {sku}"
        if product.stock < quantity:
            return f"Not enough stock for {product.name}"

        self.last_order = None  # starting a new cart clears the old receipt

        line = self.cart.line_for(sku)
        if line is None:
            self.cart.lines.append(CartLine(product=product, quantity=quantity))
        else:
            line.quantity += quantity

        product.stock -= quantity
        message = f"Added {quantity} x {product.name} to the cart"
        self.log(message)
        return message

    def change_quantity(self, sku: str, delta: int) -> str:
        line = self.cart.line_for(sku)
        if line is None:
            return f"{sku} is not in the cart"

        if delta > 0 and line.product.stock < delta:
            return f"No more stock for {line.product.name}"

        new_quantity = line.quantity + delta
        if new_quantity <= 0:
            return self.remove_from_cart(sku)

        line.quantity = new_quantity
        line.product.stock -= delta
        message = f"{line.product.name} quantity set to {new_quantity}"
        self.log(message)
        return message

    def remove_from_cart(self, sku: str) -> str:
        line = self.cart.line_for(sku)
        if line is None:
            return f"{sku} is not in the cart"

        line.product.stock += line.quantity  # give the stock back
        self.cart.lines.remove(line)
        message = f"Removed {line.product.name} from the cart"
        self.log(message)
        return message

    def clear_cart(self) -> None:
        for line in self.cart.lines:
            line.product.stock += line.quantity
        self.cart.lines.clear()


def _seed_catalogue() -> list[Product]:
    """Hardcoded catalogue. No database is used in this prototype."""
    return [
        Product(
            sku="KB-01",
            name="Mechanical keyboard 65%",
            category="Peripherals",
            price=Decimal("1290.00"),
            weight_kg=Decimal("0.85"),
            stock=8,
            emoji="⌨️",
        ),
        Product(
            sku="MS-02",
            name="Wireless ergonomic mouse",
            category="Peripherals",
            price=Decimal("640.00"),
            weight_kg=Decimal("0.12"),
            stock=14,
            emoji="🖱️",
        ),
        Product(
            sku="MN-03",
            name='27" IPS monitor',
            category="Displays",
            price=Decimal("4850.00"),
            weight_kg=Decimal("5.40"),
            stock=4,
            emoji="🖥️",
        ),
        Product(
            sku="HP-04",
            name="Studio headphones",
            category="Audio",
            price=Decimal("2100.00"),
            weight_kg=Decimal("0.38"),
            stock=6,
            emoji="🎧",
        ),
        Product(
            sku="CH-05",
            name="USB-C 7-in-1 hub",
            category="Accessories",
            price=Decimal("520.00"),
            weight_kg=Decimal("0.09"),
            stock=20,
            emoji="🔌",
        ),
        Product(
            sku="DK-06",
            name="Adjustable laptop stand",
            category="Accessories",
            price=Decimal("380.00"),
            weight_kg=Decimal("1.10"),
            stock=11,
            emoji="💻",
        ),
    ]
