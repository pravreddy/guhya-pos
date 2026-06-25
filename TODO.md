# guhya-pos — roadmap / todo

The POS core (multi-tenant data model + cashier API + blue/green deploy) is
done and pushed. This is the backlog, roughly in priority order. Each item is
staged so we ship something usable at every step rather than a big-bang.

## ✅ DONE
- [x] **Backend** — multi-tenant data model + cashier API, tested.
- [x] **Deployed to pos.guhya.co.in** — live behind shared nginx (avyangah box),
      automated from laptop via `avyangah-infra/stacks/guhya-pos` (cert.sh + deploy.sh).
      `/ping` 200, `/admin/` and `/api/` working. Image from ghcr, blue/green ready.

## ▶ Corrected priority order (2026-06-24, after market scan + review)

Finish the core so a real cafe runs a FULL DAY, then the differentiated wedge.
Near-term, in order:

0. **Prove the loop** (testing now) — table -> items -> split pay -> table frees
   -> kitchen ticket.
1. **Menu management = write API + AI import (MERGED).** Writable
   MenuItem/MenuCategory API (needed either way) + ONE menu-manager screen that
   doubles as the AI "Review & Confirm" screen. Owner uploads a photo /
   spreadsheet, LLM (care-ai pipeline) parses -> owner corrects + confirms on the
   same screen. NOT a big manual CRUD then a separate AI tool. Also the
   onboarding activation engine: upload menu -> see your dishes in <60s.
   (Nuance: we still need a minimal edit UI — you must be able to fix a wrong
   price — but AI does the heavy populate; the "CRUD" IS the review surface.)
2. **Service modes** (dine_in / takeaway / both; default = hybrid) + treat
   Counter/Takeaway as a permanent VIRTUAL TABLE (is_virtual / id 0) so one code
   path serves both — a counter order is just an order on the virtual table.
3. **WhatsApp digital bill + UPI QR** (PULLED UP — a cafe can't run a day without
   a clean UPI flow). Bill on WhatsApp with a UPI deep-link QR: settles the bill
   AND captures the phone number for CRM in one move (the Trojan horse). Thermal
   receipt / KOT print alongside (Web Bluetooth / WebUSB from the PWA; expect
   2-inch thermal formatting quirks — budget time for it).
4. **Offline — Phase 1 (PULLED FORWARD, but phased).** Cache menu + tables in
   IndexedDB so the screen still loads and an order can be BUILT when wifi drops
   mid-rush, and queue pending order-writes locally. (Phase 2 = full sync +
   conflict/duplicate handling on reconnect — harder, do after.) If staff can't
   take an order during a blip, they abandon the system for pen + paper.
5. **Role-based permissions** — lock endpoints per role before real staff use it.
6. **Void / discount + day-close & weekly/monthly sales reports.**

THEN the differentiated wedge (grows the restaurant's money, fits our AI/voice):
CRM + loyalty + coupons + WhatsApp campaigns -> AI "Know" (read-only) first ->
voice ordering -> white-label theming. Details in the sections below.

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
- [x] **2. Menu management (write API + AI import, MERGED).** DONE. Writable
      category/item API (owner/admin only) + menu-manager screen. Import modal
      reads a photo / PDF / spreadsheet / CSV (or pasted text) into the SAME
      review table -> owner corrects -> bulk create. AI provider is pluggable
      (MENU_AI_PROVIDER=auto): Gemini API (fast, cloud, same key/pattern as
      DocSign) when a key is set, else local Ollama vision. CSV/XLSX parse
      without AI.
- [x] **Menu export + reformat existing menu.** DONE (CSV/Excel; PDF/Word later).
      Owner can DOWNLOAD the menu (Export CSV) in the same column layout the
      importer reads -> edit in a sheet -> re-import = full reformat loop. Plus
      in-app reorg anytime: a per-item "move to category" dropdown, rename/delete
      categories, and AI re-import with category suggestions. (TODO later: PDF/
      Word printable menu card via the receipt render path; bulk multi-select move.)
- [ ] **DB backups (data safety) — IMPORTANT for a live customer.** `guhya_pos`
      lives in the shared `careai-postgres` container (its own database; the app
      container is stateless). No automated backup yet. Add a nightly `pg_dump`
      of `guhya_pos` (gzip, retain N days, copy off-box), wired into
      avyangah-infra like the monitoring stack. Manual snapshot meanwhile:
      `docker exec careai-postgres pg_dump -U careai guhya_pos | gzip > guhya_pos_$(date +%F).sql.gz`.
- [x] **3. Kitchen display (KDS)** — live ticket queue, start/ready/served,
      auto-refresh every 5s (polling). WebSocket push is the later upgrade.
- [x] **4. Owner home** — role-routed landing: open orders, occupied tables.
      (Richer dashboard — sales totals, top items — later.)

**Seed / demo data:** `manage.py seed_cafe` creates Cafe Gopala + tables +
starter menu, links the superuser as owner, and adds cashier/kitchen logins.

## Operating modes + real-cafe essentials (NEAR-TERM — takes it from "demo" to "runs a full day")

The POS must fit these kinds of place from ONE codebase, chosen per tenant.
HYBRID is the common case for small cafes — a few tables AND a takeaway counter
at the same time — so it's a first-class mode, not an edge case:

  A. **Dine-in / table service** (seats only) — table grid, per-table orders,
     split by table.
  B. **Takeaway-only / small cafe** (no seats) — walk up, order vada / samosa /
     coffee, pay, leave. No table grid; a fast counter flow.
  C. **Hybrid / both** (THE COMMON CASE) — a few tables AND a counter together:
     someone eats in while the next person grabs a coffee to go. This is
     basically what the cashier screen does TODAY (table grid + "Counter /
     Takeaway" button side by side).

- [ ] **Per-tenant service mode** (`service_mode`: dine_in / takeaway / both).
      The cashier screen adapts:
      - dine_in  -> table grid, no counter button
      - takeaway -> counter order only, table grid hidden, opens straight to a
                    new counter order -> bill -> pay -> done
      - both     -> table grid AND counter button together (current behaviour)
      Default = both (hybrid), since that's what most small cafes want. Pure
      takeaway is just this with tables hidden.
      - DATA MODEL: treat "Counter / Takeaway" as a permanent VIRTUAL TABLE
        (is_virtual=True / id 0) so ONE code path serves both — a counter order
        is just an order on the virtual table. Keeps dine-in and takeaway uniform.

- [ ] **Customer bill: WhatsApp + UPI QR first, then thermal print (PULLED UP).**
      A cafe can't run a day without a clean way to take UPI. Lead with:
      - **Digital bill on WhatsApp** with a **UPI deep-link QR** — the Trojan
        horse: it settles the bill AND captures the customer's phone for CRM in
        one move, and saves thermal-paper cost.
      - **Thermal receipt / KOT print** for kitchens that need paper — via Web
        Bluetooth / WebUSB from the PWA. Note: printing to a 2-inch thermal
        printer from a browser has real formatting quirks; budget time for it.
      Online/mobile *card* payment is LATER (point 3). First is: "here's your
      total — pay by UPI (QR on WhatsApp) or cash at the counter."

- [ ] **Offline — Phase 1 (PULLED FORWARD).** Cache menu + tables in IndexedDB so
      the cashier screen still loads and an order can be BUILT when wifi drops
      mid-rush; queue pending order-writes locally. Phase 2 (later) = full sync +
      duplicate/conflict handling on reconnect. Without this, a network blip in
      the morning rush sends staff back to pen + paper and they abandon the app.

- [ ] **KOT (kitchen order ticket) print** — print/send the order to the kitchen
      (matters for dine-in and busier takeaway counters).

- [ ] **Void / cancel + discount** — cancel an order or a single line, and apply
      a discount (flat or %). A real till needs these.

- [ ] **Day-close / sales report** — end-of-day totals: cash vs UPI vs card,
      order count, total sales — so the owner reconciles the till each night.

- [ ] **(Point 3, LATER) Online / mobile payment** — pay-from-phone (UPI intent
      / payment gateway) so the customer settles without cash at the counter.

- [ ] **(LATER) Online ordering + item-receipt verification (signsimple-style).**
      When orders come in online (delivery / pickup / counter collection), add a
      verification step — like signsimple's confirm flow — so both sides confirm
      EVERY item was handed over / received. Cuts "missing item" disputes. Reuse
      signsimple's verify pattern; ties into the receipt (#3) + customer record.

## Competitive feature landscape — what established POS have that we don't (researched 2026)

From Toast / Square / Lightspeed (global) and Petpooja / Reelo / Punchh / uEngage
(India). NOT a list to fully clone — Petpooja has 100k+ outlets and 100+ reports;
matching them feature-for-feature is a losing race. Split into table-stakes
(needed to replace a real till) and differentiators (where a nimble AI-native,
WhatsApp-first, commission-free POS can actually win).

### A. Core operations — table stakes (needed before a real cafe relies on it)
- [ ] **Inventory + recipe management** — stock auto-deducts per sale, low-stock
      alerts, recipe/food costing, wastage tracking. (Petpooja's core strength.)
- [ ] **Modifiers / variations / add-ons / combos** — "extra cheese", sizes,
      meal combos. (We only have full/half today.)
- [ ] **Aggregator sync (Swiggy / Zomato)** — manage online orders from one
      screen (via middleware like UrbanPiper/Dyno; don't block launch on it).
- [ ] **Station-wise KOT routing** — different kitchen stations -> their own printers.
- [ ] **Offline mode** — keep billing + KOT working when the wifi drops (critical).
- [ ] **Reservations / waitlist**, **token/queue management** (QSR takeaway).
- [ ] **Gift cards / vouchers**, **multi-language** bills & UI (15+ Indian langs).
- [ ] **Multi-outlet / franchise** — one owner, many outlets, consolidated view.

### B. Data & insights (you asked) — mostly table stakes
- [ ] **Day-end / Z-report**, **weekly & monthly sales**, **hourly trends**.
- [ ] **Item-wise performance** (best/worst sellers = menu engineering).
- [ ] **Payment-mode split** (cash/UPI/card), **cancelled/void report**.
- [ ] **GST reports** ready for filing. **Staff/biller performance**.
- [ ] Owner dashboard: live + historical, downloadable. (Forecasting later.)

### C. CRM + loyalty + coupons (you asked) — THE WEDGE / differentiator
- [ ] **Customer database** — capture phone at billing, order history per customer.
- [ ] **Loyalty** — points / visit / spend based; tiers (silver/gold/platinum);
      redemption at billing.
- [ ] **Coupons / schemes / discounts** — codes, flat/%, validity, item/category.
- [ ] **Birthday / anniversary** auto-offers; **feedback capture** (post-meal
      rating, alert manager on 1-2 star).
- [ ] **Win-back campaigns** — lapsed list (30/60/90 days) -> personalised offer
      referencing their last order.
- [ ] **WhatsApp-first messaging** — digital bill + UPI QR, offers, win-back.
      WhatsApp ~98% open rate; THE India channel in 2026. Also the way to move
      repeat orders OFF Swiggy/Zomato and escape 25-30% commission.
- [ ] **Prepaid wallets / memberships / referrals** (newer trend: value > discount).

### D. AI (you asked) — plays to our care-ai strengths, ties to voice ordering
- [ ] **AI personalization** — purchase history -> targeted offer ("likes spicy,
      visits Tuesdays -> free spicy item Tuesday"); lifts redemption vs blast.
- [ ] **AI churn prediction** — flag who's about to stop coming, auto re-engage.
- [ ] **AI marketing automation** — system finds inactive customers + revenue
      gaps daily, suggests a ready WhatsApp campaign, owner approves in one tap.
- [ ] **AI invoice digitisation** — scan supplier bill -> inventory + payables.
- [ ] **AI phone / voice agent** — take orders 24/7 (reuse care-ai STT->LLM->JSON
      pipeline). Ties directly to the existing voice-ordering idea below.
- [ ] **AI menu/sales insights** — what to promote, menu engineering suggestions.

**Strategic note:** lead with B (insights) + C (CRM/loyalty/WhatsApp) + D (AI) as
the DIFFERENTIATED wedge — they grow the restaurant's revenue, break aggregator
dependence, and fit our AI/voice strengths and "friend to the restaurant, flat
fee not commission" positioning. Do the A table-stakes (esp. inventory, modifiers,
reports, offline, GST) as needed so we can actually replace the current till.

## Go-to-market: self-service onboarding (GATED: only AFTER POS is proven end-to-end on pos.guhya.co.in with Cafe Gopala)

Goal: a restaurant can sign up online and start using the POS with NO sales call.
We (super admin) only approve or reject. First 3 months free as the launch hook.
The architecture already supports this (row-level multi-tenant) — this is exposing
it, not rebuilding.

- [ ] **Public signup page on a separate URL** (e.g. `get.guhya.co.in` or a page
      on guhya-website). POS app stays behind login; signup is the only public door.
      Collect: restaurant name, owner name, phone, email, city (GST/FSSAI optional).
- [ ] **Tenant lifecycle state.** Add to Tenant: `status` (pending / trial /
      active / suspended / rejected) and `trial_ends_at`. Signup creates a
      `pending` tenant + an owner user (inactive until approved). Do this when
      building onboarding so billing slots in later with no migration scramble.
- [ ] **Admin approve / reject** (one-click in admin, optional notes). Approving
      activates the tenant, starts the 3-month trial, emails the owner their
      login. "Call / email the restaurant first" is an OPTIONAL manual choice,
      never a required step — so it doesn't become a growth bottleneck.
- [ ] **Anti-abuse:** email/phone OTP verification + signup rate-limiting, so the
      manual gate isn't drowning in spam. Never auto-activate.
- [ ] **Activation is the real metric, not signups.** Wire menu onboarding
      (spreadsheet / photo / voice → LLM, see below) into the signup flow so a new
      restaurant gets its menu in FAST — that's what stops trial churn.
- [ ] **Billing (later, when trials convert):** trial-expiry handling + a payment
      rail (Razorpay for India). Trial → paid. Suspend on non-payment.
- [ ] **Mobile / offline:** current app is already a PWA base. Add OFFLINE
      RESILIENCE (queue orders locally, sync on reconnect) — POS must survive a
      wifi blip mid-rush — before Play Store packaging via Capacitor.
- [ ] **Infra:** new public URL = another `stacks/<app>` entry + cert + route in
      avyangah-infra (same pattern as guhya-pos). Note in avyangah-infra BACKLOG.

## Now / next (after frontend foundation)
- [x] **Menu onboarding** — MERGED into "2. Menu management" above (AI import
      populates the same menu-manager / Review & Confirm screen). Kept here as a
      pointer so the link isn't lost: owner drops a spreadsheet / photo / speaks
      the items -> LLM normalises into MenuCategory + MenuItem (veg/non-veg,
      half/full, GST).

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
