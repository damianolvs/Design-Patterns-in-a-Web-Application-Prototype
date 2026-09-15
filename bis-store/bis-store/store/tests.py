"""Tests that check each pattern actually behaves like the pattern.

Run with:  python manage.py test

These are not here for coverage. Each test asserts the property that makes
the pattern the pattern -- one instance for Singleton, interchangeable
algorithms for Strategy, and a Model layer that does not depend on HTTP for
MVT.
"""

from decimal import Decimal

from django.test import Client, SimpleTestCase

from store.models import CartLine, Checkout, Product, ShoppingCart
from store.patterns.shipping import (
    ExpressShipping,
    ShippingStrategy,
    StandardShipping,
    StorePickup,
    get_strategy,
)
from store.patterns.store_state import StoreState


def _cart(price="1000.00", weight="1.00", quantity=1) -> ShoppingCart:
    product = Product(
        sku="T-01",
        name="Test product",
        category="Test",
        price=Decimal(price),
        weight_kg=Decimal(weight),
        stock=99,
    )
    return ShoppingCart(lines=[CartLine(product=product, quantity=quantity)])


class SingletonTests(SimpleTestCase):
    """store/patterns/store_state.py"""

    def test_get_instance_always_returns_the_same_object(self):
        first = StoreState.get_instance()
        second = StoreState.get_instance()
        self.assertIs(first, second)
        self.assertEqual(first.instance_id, second.instance_id)

    def test_direct_instantiation_is_blocked(self):
        StoreState.get_instance()  # make sure the singleton exists
        with self.assertRaises(RuntimeError):
            StoreState()

    def test_state_survives_between_calls(self):
        state = StoreState.reset()
        state.add_to_cart("KB-01")
        self.assertEqual(StoreState.get_instance().cart.item_count, 1)

    def test_access_counter_increments(self):
        StoreState.reset()
        before = StoreState.get_instance().access_count
        StoreState.get_instance()
        self.assertGreater(StoreState.get_instance().access_count, before)


class StrategyTests(SimpleTestCase):
    """store/patterns/shipping.py"""

    def test_every_strategy_implements_the_interface(self):
        for code in ("standard", "express", "pickup"):
            strategy = get_strategy(code)
            self.assertIsInstance(strategy, ShippingStrategy)

    def test_same_cart_different_prices_per_strategy(self):
        cart = _cart(price="1000.00", weight="2.00")
        costs = {
            code: Checkout(cart=cart, strategy_code=code).shipping_cost
            for code in ("standard", "express", "pickup")
        }
        self.assertEqual(costs["standard"], Decimal("135.00"))  # 99 + 18*2
        self.assertEqual(costs["express"], Decimal("289.00"))   # 219 + 35*2
        self.assertEqual(costs["pickup"], Decimal("0.00"))

    def test_standard_shipping_is_free_above_the_threshold(self):
        cart = _cart(price="3000.00", weight="2.00")
        checkout = Checkout(cart=cart, strategy_code="standard")
        self.assertEqual(checkout.shipping_cost, Decimal("0.00"))

    def test_express_is_never_free(self):
        cart = _cart(price="9999.00", weight="1.00")
        checkout = Checkout(cart=cart, strategy_code="express")
        self.assertGreater(checkout.shipping_cost, Decimal("0.00"))

    def test_pickup_refuses_a_heavy_cart(self):
        cart = _cart(price="1000.00", weight="5.00", quantity=3)  # 15 kg
        checkout = Checkout(cart=cart, strategy_code="pickup")
        self.assertFalse(checkout.shipping_available)

    def test_swapping_the_strategy_changes_the_total(self):
        cart = _cart(price="1000.00", weight="2.00")
        checkout = Checkout(cart=cart, strategy_code="standard")
        cheap_total = checkout.total
        checkout.strategy_code = "express"  # runtime swap, one assignment
        self.assertGreater(checkout.total, cheap_total)

    def test_unknown_code_falls_back_to_the_default(self):
        self.assertIsInstance(get_strategy("teleport"), StandardShipping)


class ModelLayerTests(SimpleTestCase):
    """store/models.py -- the M of MVT"""

    def test_model_layer_does_not_import_anything_from_django(self):
        """The Model layer must be usable without a web request at all."""
        import ast
        import store.models as models_module

        tree = ast.parse(open(models_module.__file__, encoding="utf-8").read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)

        django_imports = [m for m in imported if m.split(".")[0] == "django"]
        self.assertEqual(django_imports, [], f"Model layer leaked: {django_imports}")

    def test_totals_are_computed_in_the_model_not_the_view(self):
        cart = _cart(price="100.00", weight="1.00", quantity=2)
        checkout = Checkout(cart=cart, strategy_code="pickup")
        self.assertEqual(checkout.cart.subtotal, Decimal("200.00"))
        self.assertEqual(checkout.tax, Decimal("32.00"))
        self.assertEqual(checkout.total, Decimal("232.00"))


class ViewLayerTests(SimpleTestCase):
    """store/views.py + templates -- the V and T of MVT"""

    def setUp(self):
        StoreState.reset()
        self.client = Client()

    def test_homepage_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Catalogue")

    def test_add_to_cart_round_trip(self):
        response = self.client.post("/cart/add/KB-01/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StoreState.get_instance().cart.item_count, 1)

    def test_stock_goes_down_and_comes_back(self):
        state = StoreState.get_instance()
        before = state.find_product("MS-02").stock
        self.client.post("/cart/add/MS-02/")
        self.assertEqual(state.find_product("MS-02").stock, before - 1)
        self.client.post("/cart/remove/MS-02/")
        self.assertEqual(state.find_product("MS-02").stock, before)

    def test_shipping_switch_updates_the_selection(self):
        self.client.post("/checkout/shipping/", {"strategy": "express"})
        self.assertEqual(StoreState.get_instance().selected_shipping, "express")

    def test_htmx_request_returns_only_the_fragment(self):
        full = self.client.get("/")
        fragment = self.client.get("/", headers={"HX-Request": "true"})
        self.assertNotContains(fragment, "<!doctype html>")
        self.assertLess(len(fragment.content), len(full.content))

    def test_order_can_be_placed_end_to_end(self):
        self.client.post("/cart/add/CH-05/")
        self.client.post("/checkout/shipping/", {"strategy": "pickup"})
        self.client.post("/checkout/confirm/")
        order = StoreState.get_instance().last_order
        self.assertIsNotNone(order)
        self.assertEqual(order["shipping_cost"], Decimal("0.00"))
        self.assertTrue(StoreState.get_instance().cart.is_empty)

    def test_empty_cart_cannot_be_ordered(self):
        self.client.post("/checkout/confirm/")
        self.assertIsNone(StoreState.get_instance().last_order)
