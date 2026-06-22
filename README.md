# guhya-pos — restaurant POS (backend)

Multi-tenant restaurant POS built on Django. One database, one codebase;
every restaurant (tenant) sees only its own data, scoped by a middleware —
the same pattern as your other apps. Owners/admins manage everything from the
Django admin.

## What's inside (version one foundation)

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
   Visit http://localhost:8000/admin/

## First steps in the admin

1. Create a Tenant (your restaurant).
2. Create users and set their tenant + role.
3. Add menu categories and items.
4. Add tables.

## In your app code (API / views), scope to the current restaurant:

```python
MenuItem.objects.for_current()      # only this restaurant's items
Order.objects.for_current()         # only this restaurant's orders
```

`for_current()` reads the tenant the middleware set for the request. Plain
`.objects` is unscoped and is what the admin uses (a superuser sees all
restaurants, with a tenant filter on every list).

## What's next (not in this foundation yet)

- REST API for the cashier flow (open table, add lines, take payment).
- Kitchen display: WebSocket push of order/line status.
- Menu onboarding: spreadsheet drop / photo / voice (your LLM normalises it).
- Voice ordering: your speech-to-text-to-JSON pipeline creates OrderLines.
- React + PWA frontend; Capacitor Android wrapper when the printer needs it.
- Aggregator lane: manual entry first, connector (UrbanPiper/Dyno) later.
