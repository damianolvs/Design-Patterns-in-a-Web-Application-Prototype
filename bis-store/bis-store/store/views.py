"""
=============================================================================
 DESIGN PATTERN #1 -- MVT / MVC  ->  THE "V" LAYER  (architectural)
=============================================================================

In Django's MVT this file plays the role the *Controller* plays in classic
MVC (the instructor's `controllers/TaskController.ts`). It is the only layer
that is allowed to know about HTTP.

What a view in here is allowed to do:
    * read the request,
    * validate/normalise the input,
    * ask the Model (or the Singleton that holds it) to do the work,
    * pick which template renders the result.

What a view in here must NOT do:
    * compute a shipping price   -> that is the Strategy's job,
    * build its own state object -> that is `StoreState.get_instance()`,
    * write HTML                 -> that is the Template's job.

Every handler below is short on purpose. If a view starts growing branches of
business logic, the logic belongs one layer down.

HTMX note: each action returns the same `partials/app.html` fragment. When
the request comes from HTMX we send only that fragment; otherwise we render
the full page. That is why the app still works with JavaScript disabled --
the forms are ordinary POST forms with a progressive-enhancement attribute.
"""

from __future__ import annotations

from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from store.models import Checkout
from store.patterns.shipping import SHIPPING_STRATEGIES
from store.patterns.store_state import StoreState

# module-level counter for order numbers; the demo does not need persistence
_order_counter = {"value": 0}


def _build_context(state: StoreState, flash: str = "") -> dict:
    """Assemble everything the template needs. No business rules here."""
    checkout = Checkout(cart=state.cart, strategy_code=state.selected_shipping)
    return {
        "products": state.products(),
        "cart": state.cart,
        "checkout": checkout,
        "quotes": checkout.quote_all_strategies(),
        "activity_log": list(reversed(state.activity_log)),
        "last_order": state.last_order,
        "flash": flash,
        # Singleton evidence panel
        "instance_id": state.instance_id,
        "created_at": state.created_at,
        "access_count": state.access_count,
        "singleton_error": state.singleton_error,
    }


def _respond(request, state: StoreState, flash: str = ""):
    """Full page for a normal request, fragment for an HTMX request."""
    context = _build_context(state, flash)
    if request.headers.get("HX-Request"):
        return render(request, "store/partials/app.html", context)
    return render(request, "store/index.html", context)


@require_GET
def index(request):
    state = StoreState.get_instance()
    return _respond(request, state)


@require_POST
def add_to_cart(request, sku: str):
    state = StoreState.get_instance()
    flash = state.add_to_cart(sku)
    return _respond(request, state, flash)


@require_POST
def change_quantity(request, sku: str):
    state = StoreState.get_instance()
    try:
        delta = int(request.POST.get("delta", "1"))
    except ValueError:
        delta = 1
    flash = state.change_quantity(sku, delta)
    return _respond(request, state, flash)


@require_POST
def remove_from_cart(request, sku: str):
    state = StoreState.get_instance()
    flash = state.remove_from_cart(sku)
    return _respond(request, state, flash)


@require_POST
def set_shipping(request):
    """Swap the Strategy at runtime. One assignment, no pricing logic here."""
    state = StoreState.get_instance()
    code = request.POST.get("strategy", "")
    if code not in SHIPPING_STRATEGIES:
        return _respond(request, state, f"Unknown shipping option '{code}'")

    state.selected_shipping = code
    strategy = SHIPPING_STRATEGIES[code]
    flash = f"Shipping strategy switched to {strategy.__class__.__name__}"
    state.log(flash)
    return _respond(request, state, flash)


@require_POST
def confirm_order(request):
    state = StoreState.get_instance()
    if state.cart.is_empty:
        return _respond(request, state, "The cart is empty")

    checkout = Checkout(cart=state.cart, strategy_code=state.selected_shipping)
    if not checkout.shipping_available:
        reason = checkout.strategy.unavailable_reason()
        return _respond(request, state, f"{checkout.strategy.label} unavailable: {reason}")

    _order_counter["value"] += 1
    order = checkout.build_order(_order_counter["value"])
    state.last_order = order
    state.cart.lines.clear()  # stock was already reserved when items were added
    state.log(f"Order {order['number']} confirmed — total ${order['total']}")
    return _respond(request, state, f"Order {order['number']} confirmed")


@require_POST
def try_second_instance(request):
    """Demo-only endpoint: prove the Singleton refuses a second instance.

    Mirrors section 7.1.3 of the lab guide ("if the constructor were public,
    every call would produce a different id"). Here the constructor raises.
    """
    state = StoreState.get_instance()
    try:
        StoreState()  # <- this is what the pattern forbids
        state.singleton_error = "No error?! The Singleton guard is broken."
    except RuntimeError as exc:
        state.singleton_error = str(exc)
    state.log("Tried StoreState() directly — blocked by the Singleton guard")
    return _respond(request, state, "Direct instantiation was blocked")


@require_POST
def reset_state(request):
    old_id = StoreState.get_instance().instance_id
    state = StoreState.reset()
    state.log(f"State rebuilt — previous instance was {old_id}")
    return _respond(request, state, "Store state rebuilt from scratch")
