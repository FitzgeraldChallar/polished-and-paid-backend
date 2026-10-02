# Polish & Pay API Quick Reference

Base URL: `http://127.0.0.1:8000/api`

## Catalog
- `GET /categories/`
- `GET /categories/{slug}/`
- `GET /products/`
- `GET /products/{slug}/`
- `GET /products/?category=beauty-skincare`
- `GET /products/?search=serum`
- `GET /products/?featured=true`
- `GET /products/?new=true`
- `GET /products/?bestseller=true`
- `GET /products/?ordering=price` or `-price`

## Authentication
- `POST /auth/register/` → `{email,password,first_name,last_name,phone}`
- `POST /auth/login/` → `{email,password}` → token
- `POST /auth/logout/` with `Authorization: Token <token>`
- `GET/PATCH /auth/profile/`

## Addresses
- `GET/POST /addresses/`
- `GET/PATCH/DELETE /addresses/{id}/`

## Cart
- `GET /cart/`
- `DELETE /cart/` clears the cart
- `POST /cart/items/` → `{product_id, quantity}` adds quantity
- `PATCH /cart/items/` → `{item_id, quantity}` sets quantity
- `DELETE /cart/items/` → `{item_id}` removes item

Guest carts use the Django session. Authenticated carts belong to the customer.

## Checkout / Orders
`POST /checkout/` creates a pending order from the current cart. Body:
```json
{
  "email": "customer@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "shipping_line1": "123 Main Street",
  "shipping_line2": "",
  "shipping_city": "Atlanta",
  "shipping_state": "GA",
  "shipping_postal_code": "30301",
  "shipping_country": "United States",
  "shipping_phone": "+1...",
  "shipping_fee": "0.00",
  "tax": "0.00",
  "notes": ""
}
```

- `GET /orders/` requires authentication and returns the customer's order history.
- `GET /orders/{id}/` requires authentication.

## Stripe
- `POST /payments/stripe/create-checkout-session/` → `{order_id}`
- `POST /payments/stripe/webhook/` → Stripe webhook endpoint

The webhook, not the frontend success page, changes an order to `paid` and records the Stripe payment.
