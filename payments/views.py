import logging
from decimal import Decimal, ROUND_HALF_UP

import stripe
from django.conf import settings
from django.core import signing
from django.db import transaction
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Product
from orders.models import Order
from .models import Payment

logger = logging.getLogger(__name__)

CHECKOUT_TOKEN_SALT = "polishpay.stripe-checkout"
CHECKOUT_TOKEN_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def _minor_units(value):
    """Convert a decimal currency amount to Stripe's integer minor units."""
    amount = Decimal(str(value or "0.00"))
    return int((amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _stripe_object_to_dict(value):
    """Convert Stripe SDK objects recursively to plain JSON-safe Python values."""
    if isinstance(value, dict):
        return {str(key): _stripe_object_to_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_stripe_object_to_dict(item) for item in value]

    # Stripe's Python SDK exposes to_dict_recursive() on StripeObject. Avoid
    # calling to_json(), which is not available in current SDK versions.
    to_dict_recursive = getattr(value, "to_dict_recursive", None)
    if callable(to_dict_recursive):
        return _stripe_object_to_dict(to_dict_recursive())

    return value


def _valid_checkout_token(token, order):
    if not token:
        return False
    try:
        payload = signing.loads(
            token,
            salt=CHECKOUT_TOKEN_SALT,
            max_age=CHECKOUT_TOKEN_MAX_AGE_SECONDS,
        )
    except signing.BadSignature:
        return False
    return (
        str(payload.get("order_id")) == str(order.pk)
        and payload.get("order_number") == order.order_number
    )


def _checkout_session_response(session, order):
    return Response(
        {
            "checkout_url": session.get("url"),
            "session_id": session.get("id"),
            "order": order.order_number,
        }
    )


class CreateStripeCheckoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"detail": "Stripe is not configured. Add STRIPE_SECRET_KEY to the backend environment."},
                status=503,
            )

        order_id = request.data.get("order_id")
        checkout_token = request.data.get("checkout_token")
        if not order_id:
            return Response({"detail": "order_id is required."}, status=400)

        try:
            order = Order.objects.prefetch_related("items").get(pk=order_id)
        except (Order.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Order not found."}, status=404)

        is_owner = bool(
            request.user.is_authenticated
            and order.user_id
            and order.user_id == request.user.id
        )
        if not is_owner and not _valid_checkout_token(checkout_token, order):
            return Response(
                {"detail": "You are not authorized to start payment for this order. Return to checkout and try again."},
                status=403,
            )

        if order.status in {"paid", "processing", "shipped", "delivered", "refunded", "cancelled"}:
            return Response(
                {"detail": f"This order cannot be paid because its status is {order.status}."},
                status=409,
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            with transaction.atomic():
                # Lock the order/payment row so concurrent clicks do not create
                # multiple active Checkout Sessions for the same order.
                locked_order = Order.objects.select_for_update().get(pk=order.pk)
                payment, _ = Payment.objects.get_or_create(
                    order=locked_order,
                    defaults={
                        "amount": locked_order.total,
                        "currency": locked_order.currency.upper(),
                        "status": "pending",
                    },
                )
                payment = Payment.objects.select_for_update().get(pk=payment.pk)

                if payment.status == "paid":
                    return Response(
                        {"detail": "This order has already been paid."},
                        status=409,
                    )

                if payment.stripe_checkout_session_id:
                    try:
                        existing = stripe.checkout.Session.retrieve(
                            payment.stripe_checkout_session_id
                        )
                        existing_status = existing.get("status")
                        if existing_status == "open" and existing.get("url"):
                            return _checkout_session_response(existing, locked_order)
                        if existing_status == "complete" and payment.status == "pending":
                            return Response(
                                {"detail": "This checkout was submitted and payment confirmation is pending. Please wait a moment before trying again."},
                                status=409,
                            )
                    except stripe.StripeError:
                        # If the stored session cannot be retrieved, attempt to
                        # create a replacement and persist its new identifier.
                        logger.warning(
                            "Could not retrieve prior Stripe session for order %s.",
                            locked_order.order_number,
                            exc_info=True,
                        )

                line_items = []
                computed_total = 0
                for item in locked_order.items.all():
                    if item.quantity < 1:
                        return Response({"detail": "An order item has an invalid quantity."}, status=400)
                    unit_amount = _minor_units(item.unit_price)
                    if unit_amount < 0:
                        return Response({"detail": "An order item has an invalid price."}, status=400)
                    line_items.append(
                        {
                            "price_data": {
                                "currency": locked_order.currency.lower(),
                                "product_data": {
                                    "name": item.product_name,
                                    "metadata": {"sku": item.sku},
                                },
                                "unit_amount": unit_amount,
                            },
                            "quantity": item.quantity,
                        }
                    )
                    computed_total += unit_amount * item.quantity

                for label, amount in (("Shipping", locked_order.shipping_fee), ("Tax", locked_order.tax)):
                    minor_amount = _minor_units(amount)
                    if minor_amount < 0:
                        return Response({"detail": f"{label} cannot be negative."}, status=400)
                    if minor_amount > 0:
                        line_items.append(
                            {
                                "price_data": {
                                    "currency": locked_order.currency.lower(),
                                    "product_data": {"name": label},
                                    "unit_amount": minor_amount,
                                },
                                "quantity": 1,
                            }
                        )
                        computed_total += minor_amount

                if computed_total != _minor_units(locked_order.total):
                    return Response(
                        {"detail": "The order total does not match its item, shipping, and tax amounts. Please contact support."},
                        status=400,
                    )
                if computed_total <= 0 or not line_items:
                    return Response({"detail": "The order total must be greater than zero."}, status=400)

                session = stripe.checkout.Session.create(
                    mode="payment",
                    line_items=line_items,
                    customer_email=locked_order.email,
                    success_url=(
                        f"{settings.FRONTEND_URL}/checkout/success"
                        f"?session_id={{CHECKOUT_SESSION_ID}}&order={locked_order.order_number}"
                    ),
                    cancel_url=(
                        f"{settings.FRONTEND_URL}/checkout/cancelled"
                        f"?order={locked_order.order_number}"
                    ),
                    metadata={
                        "order_id": str(locked_order.id),
                        "order_number": locked_order.order_number,
                    },
                    payment_intent_data={
                        "metadata": {
                            "order_id": str(locked_order.id),
                            "order_number": locked_order.order_number,
                        }
                    },
                )

                payment.amount = locked_order.total
                payment.currency = locked_order.currency.upper()
                payment.status = "pending"
                payment.stripe_checkout_session_id = session.id
                payment.raw_response = _stripe_object_to_dict(session)
                payment.save(
                    update_fields=[
                        "amount",
                        "currency",
                        "status",
                        "stripe_checkout_session_id",
                        "raw_response",
                        "updated_at",
                    ]
                )

                return _checkout_session_response(session, locked_order)

        except stripe.StripeError as exc:
            logger.exception("Stripe Checkout Session creation failed for order %s.", order.order_number)
            return Response(
                {"detail": "Stripe could not start checkout. Please try again. If the problem continues, contact support."},
                status=502,
            )


class StripeWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not settings.STRIPE_WEBHOOK_SECRET:
            return Response({"detail": "Webhook secret is not configured."}, status=503)

        signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = stripe.Webhook.construct_event(
                request.body,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
        except (ValueError, stripe.SignatureVerificationError):
            return Response({"detail": "Invalid webhook signature or payload."}, status=400)

        event_data = _stripe_object_to_dict(event)
        event_type = event_data.get("type", "")
        session_data = event_data.get("data", {}).get("object", {})
        session_id = session_data.get("id")
        if not session_id:
            return Response({"received": True})

        relevant_events = {
            "checkout.session.completed",
            "checkout.session.async_payment_succeeded",
            "checkout.session.async_payment_failed",
            "checkout.session.expired",
        }
        if event_type not in relevant_events:
            return Response({"received": True})

        try:
            with transaction.atomic():
                payment = (
                    Payment.objects.select_for_update()
                    .select_related("order")
                    .filter(stripe_checkout_session_id=session_id)
                    .first()
                )
                if payment is None:
                    # Acknowledge events for sessions not associated with an
                    # order in this database so Stripe does not retry forever.
                    return Response({"received": True})

                order = Order.objects.select_for_update().get(pk=payment.order_id)
                if payment.status == "paid":
                    # A duplicate event must never deduct inventory twice.
                    return Response({"received": True})

                if event_type in {
                    "checkout.session.completed",
                    "checkout.session.async_payment_succeeded",
                }:
                    if session_data.get("payment_status") != "paid":
                        # Some delayed methods emit completed before funds settle.
                        return Response({"received": True})

                    expected_amount = _minor_units(order.total)
                    received_amount = session_data.get("amount_total")
                    received_currency = str(session_data.get("currency") or "").lower()
                    if (
                        received_amount is not None
                        and int(received_amount) != expected_amount
                    ) or received_currency != order.currency.lower():
                        logger.error(
                            "Stripe amount/currency mismatch for order %s (session %s).",
                            order.order_number,
                            session_id,
                        )
                        return Response({"detail": "Payment amount or currency mismatch."}, status=400)

                    # Lock all order items and products, then deduct inventory
                    # only if every extant product has enough stock. Payment is
                    # still recorded as paid if stock changed after checkout;
                    # the logged exception lets the store resolve fulfillment.
                    order_items = list(order.items.select_for_update().all())
                    product_ids = [item.product_id for item in order_items if item.product_id]
                    products = {
                        product.pk: product
                        for product in Product.objects.select_for_update().filter(pk__in=product_ids)
                    }
                    stock_is_available = all(
                        item.product_id is None
                        or (
                            item.product_id in products
                            and products[item.product_id].stock_quantity >= item.quantity
                        )
                        for item in order_items
                    )
                    if stock_is_available:
                        for item in order_items:
                            product = products.get(item.product_id)
                            if product:
                                product.stock_quantity -= item.quantity
                                product.save(update_fields=["stock_quantity", "updated_at"])
                    else:
                        logger.error(
                            "Payment received for order %s but inventory was insufficient; fulfillment review is required.",
                            order.order_number,
                        )

                    payment.status = "paid"
                    payment.stripe_payment_intent_id = session_data.get("payment_intent") or ""
                    order.status = "paid"
                    order.save(update_fields=["status", "updated_at"])

                elif event_type == "checkout.session.async_payment_failed":
                    payment.status = "failed"
                elif event_type == "checkout.session.expired":
                    payment.status = "cancelled"

                payment.raw_response = _stripe_object_to_dict(session_data)
                payment.save(
                    update_fields=[
                        "status",
                        "stripe_payment_intent_id",
                        "raw_response",
                        "updated_at",
                    ]
                )

        except Exception:
            logger.exception("Failed to process Stripe webhook event %s.", event_type)
            return Response({"detail": "Webhook processing failed."}, status=500)

        return Response({"received": True})
