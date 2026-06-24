# guhya-pos — roadmap / todo

The POS core (multi-tenant data model + cashier API + blue/green deploy) is
done and pushed. This is the backlog, roughly in priority order. Each item is
staged so we ship something usable at every step rather than a big-bang.

## ✅ DONE
- [x] **Backend** — multi-tenant data model + cashier API, tested.
- [x] **Deployed to pos.guhya.co.in** — live behind shared nginx (avyangah box),
      automated from laptop via `avyangah-infra/stacks/guhya-pos` (cert.sh + deploy.sh).
      `/ping` 200, `/admin/` and `/api/` working. Image from ghcr, blue/green ready.

## Frontend — the real app (THE PRIORITY NOW)

Why: the root URL shows "Not Found" because only `/ping`, `/admin/`, `/api/`
exist. Staff should use a proper app with role-based access THROUGH the app
layer — NOT the Django admin. This is the React PWA we planned early on; it
talks to the `/api/` that's already built, using token login for access per role.

**Architecture (decided):**
- React + Vite single-page app (PWA), token auth against `/api/auth/login/`.
- Served by the EXISTING guhya-pos container (built into the image, Django serves
  index.html at `/` + SPA catch-all; assets via WhiteNoise). No new container,
  no nginx change, root URL works immediately. (Can split into a dedicated
  frontend container later, like docsign, if/when needed — noted, not now.)
- Token + role kept in memory/secure storage; every screen scoped by role
  (owner / admin / cashier / kitchen / waiter).
- Token-first theming from day one (CSS variables from a per-tenant branding
  record) so the white-label work later is a config flip, not a rewrite.

**Build order (each ships something usable):**
- [x] **0. Foundation** — served SPA (React via CDN, no build step) at `/`:
      API client, token auth, login, role-routed app shell. Django serves
      `templates/index.html` + SPA catch-all. Root URL now shows a real login.
- [x] **1. Cashier screen** — tables -> menu -> live GST bill -> split payment
      (cash/UPI/card). Uses the existing order endpoints.
- [ ] **2. Menu setup screen** — owner adds/edits categories + items.
      NEEDS BACKEND FIRST: `MenuViewSet` is read-only; add create/update/delete
      endpoints (+ category write) before the edit UI. (Menu currently shows
      read-only in the cashier screen; seeded via `manage.py seed_cafe`.)
- [x] **3. Kitchen display (KDS)** — live ticket queue, start/ready/served,
      auto-refresh every 5s (polling). WebSocket push is the later upgrade.
- [x] **4. Owner home** — role-routed landing: open orders, occupied tables.
      (Richer dashboard — sales totals, top items — later.)

**Seed / demo data:** `manage.py seed_cafe` creates Cafe Gopala + tables +
starter menu, links the superuser as owner, and adds cashier/kitchen logins.

## Now / next (after frontend foundation)
- [ ] **Menu onboarding** — owner drops a spreadsheet / photo of the menu /
      speaks the items; an LLM normalises into MenuCategory + MenuItem
      (veg/non-veg, half/full, GST). Removes the painful manual menu entry.

## Soon
- [ ] **White-label theming (per-customer UI).** Each tenant's website AND POS
      should be re-skinnable to their own brand — logo, colours, font, theme —
      switchable from a dropdown, looking totally different per customer.
      Approach: NO hardcoded colours/fonts/logos anywhere; store a branding
      record per tenant and drive the whole UI from CSS variables.
      - One source of branding, read by BOTH the website and the POS (change
        the logo once -> updates both).
      - Tier 1 (do first): logo + primary/accent colour + font as tokens.
      - Tier 2: preset themes + layout variants (spacing, button shape, hero)
        so two cafes look genuinely different, not just recoloured. Dropdown.
      - Tier 3 (premium): custom CSS / bespoke template per customer.
      - Build the token layer BEFORE hardcoding any styles — cheap now, painful
        to retrofit later. (Driven by Srinivas / Cafe Gopal wanting UI changes.)
- [ ] **Voice ordering** — reuse the care-ai speech-to-text -> LLM -> JSON
      pipeline to create OrderLines by speaking. Always show a confirm step
      before it commits (never let a misheard command change an order silently).
- [ ] **Role-based endpoint permissions** — who can take payment / change
      kitchen status / edit menu (owner / cashier / kitchen / waiter). Right now
      any authenticated tenant user can hit any cashier endpoint.
- [ ] **GitHub Actions -> ghcr.io** — build & push the API image on each tag so
      the server pulls a prebuilt image instead of building on the box.

## Later — "Ask. Know. Act." AI assistant (the Kitchen-Tracker-style idea)
A natural-language layer ON TOP of the POS data. We own the source of truth
(orders, menu, payments), so this is a feature on our stack, not a pivot.
Staged so it's always honest — a confident wrong answer is worse than none.

- [ ] **Phase 1 — read-only "Know" (cheap, do first).** One endpoint: takes a
      question, pulls real numbers from existing tables, answers in plain
      language. No new models needed. Examples it can already answer truthfully:
      "how many orders pending?", "today's sales so far?", "which tables are
      occupied?", "top item today?". First visible piece of the vision, on real
      data, and plugs into the voice pipeline.
- [ ] **Phase 2 — inventory module (only when a bigger kitchen needs it).**
      Stock levels, depletion per dish, low-stock alerts. This is an upsell /
      higher tier — overkill for a small tiffin place like Cafe Gopala, and it
      only works if the stock data is actually kept accurate during a rush.
      Don't build the inventory mountain before the POS is earning its keep.
- [ ] **Phase 3 — "Act" / write actions, with guardrails.** Update inventory,
      record batches, attribute production to staff — each behind an explicit
      confirmation step. Never let a misheard voice/chat command silently
      change stock or orders.

## Notes / principles
- Match features to the customer: dead-simple for one-person eateries, fuller
  tiers for bigger restaurants. Don't force big-kitchen features on small ones.
- Flat SaaS fee, not per-order commission — "friend to the restaurant."
- The moat is the integrated stack (POS + own online ordering + voice + this
  assistant), which is a reason for a restaurant to stay.
- White-label theming is part of the moat too: it's THEIR brand, not ours.
