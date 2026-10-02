# Polish & Pay Backend

Django REST backend for the Polish & Pay commerce storefront.

## Included
- Product/category catalog with images, SKU, pricing, sale pricing, inventory flags and merchandising flags
- Storefront APIs: listing, category filter, search, featured/new/bestsellers, product detail
- Guest and authenticated shopping cart with stock validation
- Customer registration/login/token authentication, profile and addresses
- Checkout and order history
- Stripe Checkout + webhook payment confirmation
- Payment records linked to orders
- Django admin for catalog, inventory, orders, customers and payments

## Local setup
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

API root: `http://127.0.0.1:8000/api/`
Admin: `http://127.0.0.1:8000/admin/`

## Stripe webhook during local development
Install Stripe CLI and run:
```bash
stripe listen --forward-to localhost:8000/api/payments/stripe/webhook/
```
Put the displayed `whsec_...` in `.env` as `STRIPE_WEBHOOK_SECRET`.

Never trust a frontend success page as proof of payment. The order is marked paid by the Stripe webhook.


## Dedicated React Store Administration

The API now exposes a client-friendly administrator API under `/api/admin/`.
The Next.js admin portal can manage products, categories, orders, inventory, customers and payments without requiring the client to use Django Admin. Administrator endpoints require a Django user with `is_staff=True`.
