"""URL map -- the 'front door' that translates HTTP into view calls.

Kept deliberately thin: every route points straight at one view function in
store/views.py and contains no logic of its own.
"""

from django.urls import path

from store import views

urlpatterns = [
    path("", views.index, name="index"),
    path("cart/add/<str:sku>/", views.add_to_cart, name="add_to_cart"),
    path("cart/qty/<str:sku>/", views.change_quantity, name="change_quantity"),
    path("cart/remove/<str:sku>/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/shipping/", views.set_shipping, name="set_shipping"),
    path("checkout/confirm/", views.confirm_order, name="confirm_order"),
    path("demo/second-instance/", views.try_second_instance, name="try_second_instance"),
    path("demo/reset/", views.reset_state, name="reset_state"),
]
