# guhya-pos — restaurant POS (backend)

Multi-tenant restaurant POS built on Django. One database, one codebase;
every restaurant (tenant) sees only its own data, scoped by a middleware —
the same pattern as your other apps. Owners/admins manage everything from the
Django admin.

## What's inside

- `tenancy/` — the `Tenant` model, a `CurrentTenantMiddleware` that resolves the
  restaurant from the logged-in user, and a `TenantAwareModel` base that scopes
  and auto-fills tenant on every model.
- `accounts/` — custom `User` with a `tenant` and a `role`
  (owner / admin / cashier / kitchen / waiter).
- `catalog/` — `MenuCategory`, `MenuItem` (price, half_price, veg/non-veg/egg,
  per-item GST rate, availability).
- `orders/` — `Table`, `Order` (with a `source`: dine-in / online / aggregator),
  `OrderLine` (price + GST snapshots so old bills never change), `Payment`
  (cash / UPI / card).
- `api/` — the cashier REST API (DRF): login, menu, tables, and an order flow
  (open table, add/merge lines, take payment, kitchen queue).

## Run it

1. Start the database:
   ```
   docker compose up -d
   ```
2. Set up Python:
   ```
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```
3. Create the tables and an admin login:
   ```
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```
4. Start the server and open the admin:
   ```
   python manage.py runserver
   ```
   Visit http://localhost:8000/admin/ and the API at http://localhost:8000/api/

## First steps in the admin

1. Create a Tenant (your restaurant).
2. Create users and set their tenant + role.
3. Add menu categories and items.
4. Add tables.

## Cashier API (scoped to the logged-in user's restaurant)

- `POST /api/auth/login/` → token + role + tenant
- `GET  /api/menu/` · `GET /api/tables/`
- `POST /api/orders/` (open) · `GET /api/orders/?status=active`
- `POST /api/orders/{id}/add_line/` · `update_line/` · `remove_line/`
- `POST /api/orders/{id}/set_status/` · `pay/`
- `GET  /api/orders/kitchen/` (live queue)

## In your own code, scope to the current restaurant

```python
MenuItem.objects.for_current()      # only this restaurant's items
Order.objects.for_current()         # only this restaurant's orders
```

## What's next

- Kitchen display: WebSocket push of order/line status (Redis already in compose).
- Menu onboarding: spreadsheet drop / photo / voice (LLM normalises it).
- Voice ordering: speech-to-text-to-JSON pipeline creates OrderLines.
- React + PWA frontend; Capacitor Android wrapper when the printer needs it.
- Role-based endpoint permissions (who can take payment / change kitchen status).
