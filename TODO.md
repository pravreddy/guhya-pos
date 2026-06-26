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
2. **Service modes** (dine_in / takeaway, hybrid). DONE. Order has
   `service_mode` + optional pickup `token`. Takeaway is a TABLE-LESS order (not
   a single virtual-table row) so MANY takeaways run at once alongside dine-in —
   better than the id-0 virtual table idea, which couldn't hold concurrent
   takeaways. Cashier: Dine-in tables + "New takeaway" + a live list of open
   takeaways to resume. Lazy order creation (order is created on FIRST item, not
   on table tap) — fixes the stray-tap-occupies-table bug. At payment the cashier
   can tick "Generate a pickup token" (per-restaurant, per-day, resets daily);
   post-pay confirmation shows the token (or "table freed") — fixes the
   order-vanishes-with-no-feedback gap. Kitchen ticket shows the token.
3. **Capture customer + WhatsApp bill + UPI QR (the CRM Trojan horse).** Phased.
   (3a — FREE, no external accounts, build now): optional phone/name on any order
   (dine-in + takeaway, one-tap-skippable) -> upsert tenant-scoped `Customer`
   (start of the CRM DB); per-tenant UPI VPA setting; dynamic UPI QR at payment
   (`upi://pay?pa=VPA&am=TOTAL&tn=ORDER`) the customer scans + pays, cashier
   confirms (no auto-confirm without a gateway); bill sent via WhatsApp
   click-to-chat (wa.me) link. (3b — LATER, needs accounts/cost): WhatsApp
   Business API + approved UTILITY template for auto-send + the "customer messages
   first -> 24h free-form window" inbound flow; payment gateway (Razorpay) for
   true online pay + auto-reconcile. Thermal/KOT print rides alongside. Full spec
   + constraints in the essentials section below.
4. **Offline — Phase 1 (PULLED FORWARD, but phased).** Cache menu + tables in
   IndexedDB so the screen still loads and an order can be BUILT when wifi drops
   mid-rush, and queue pending order-writes locally. (Phase 2 = full sync +
   conflict/duplicate handling on reconnect — harder, do after.) If staff can't
   take an order during a blip, they abandon the system for pen + paper.
5. **Role-based permissions** — lock endpoints per role before real staff use it.
6. **Void / discount + day-close & weekly/monthly sales reports.**
7. **Inventory — Phase 1 (item-level stock + movement log).** Per item: opening/
   prepped qty for the day, auto-decrement on each sale, SOLD vs REMAINING at a
   glance, auto-"86" at zero, low-stock alert, manual restock/waste/correction
   with a reason, and a full stock-movement LOG (who/what/when). Answers "how
   much did we start with, how much sold, how much left." Ingredient/recipe (BOM)
   costing is Phase 2 (heavier, later). Specced in the Inventory section below.

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
- [x] **Table management (Settings tab).** Owner/admin add / rename / change
      seats / remove dine-in tables via a writable `tables-admin` API (a table
      with an OPEN order can't be deleted). New owner-only **Settings** tab — will
      also host the UPI VPA + branding settings in Phase 3a.
- [x] **Free table override + staff management (Settings tab).** "Free table"
      action (cashier on the bill, owner in Settings) cancels any open order on a
      table and frees it — for stuck/abandoned tables (a table stays occupied
      while it has an unpaid or partially-paid order; that's correct, this is the
      manual clear). Staff & logins: owner/admin add users (cashier / waiter /
      kitchen / admin), reset password, enable/disable, delete — via `users-admin`
      API (owner account protected; usernames globally unique). NOTE: this adds
      user *accounts*; per-role endpoint ENFORCEMENT is still #5 (right now any
      tenant user can hit cashier endpoints).
- [x] **Staff attendance + payroll (Attendance tab).** PIN-based clock-in/out
      with SERVER-stamped times — kills arrival-time fudging (staff can't type a
      fake time). Per-staff wage (monthly / daily / hourly) + clock-in PIN set in
      Settings → Pay/PIN. Payroll view (owner/admin) totals hours, days present,
      and pay per person for a date range. Pay rules v1: hourly = hours×rate,
      daily = days×rate, monthly = fixed. LATER: biometric fingerprint device
      pushing punches into the SAME Attendance table (a website can't read a
      thumb scanner directly — needs an ESSL/ZKTeco-style device that POSTs to
      our punch endpoint, or a native app); overtime / half-day / late-mark /
      absent-deduction rules; lock & approve a pay period; payslip / register
      export; selfie-at-punch for anti-buddy-punching.
- [x] **Phase 3a — configurable UPI QR at payment (DONE).** Per-tenant UPI VPA +
      payee name set by the owner in Settings → Payments (stored on Tenant, NOT
      hardcoded). Pay screen: pick UPI → a dynamic QR (`upi://pay?pa&pn&am&cu=INR
      &tn`) renders for the exact amount; customer scans & pays; cashier taps
      Confirm (no gateway/fees; can't auto-confirm — that's Phase 3b Razorpay).
      QR rendered client-side (qrcode-generator via CDN). `GET /tenant/` is
      readable by any tenant user (cashier needs the VPA); PATCH owner/admin only.
- [x] **Phase 3a — bill delivery channels + configurable GST (DONE).** Send the
      bill from the cashier bill or the post-pay screen via THREE free channels,
      all click-to-send (no API, no per-message cost, and none need the customer
      to message first): WhatsApp (wa.me to the captured customer phone),
      Telegram (t.me/share), and Email (mailto: — opens the cashier's mail app).
      The restaurant WhatsApp number is owner-configurable (Settings → Payments &
      WhatsApp) and shown on the bill. GST is now PER-TENANT configurable
      (Settings → Tax / GST): toggle GST on/off (off = bills show only the total,
      no tax line; recalculate() zeroes tax) and set a default rate used for new
      menu items (each item still keeps its own rate). For no-GST small eateries.
      LATER (3b automation): Telegram BOT + Email SMTP server-send so bills go out
      automatically without the cashier tapping (Telegram bot needs the customer
      to /start it; SMTP auto-send needs a captured customer email — add a
      Customer.email field then; the box already runs mailcow for SMTP). For now
      all three channels are manual click-send.
- [x] **Bill PRINTING — thermal/receipt, customer + restaurant copy (DONE).** A
      "Print bill" button on the cashier bill AND the post-pay screen renders a
      narrow (~72mm) monospace receipt and prints via the browser to ANY installed
      printer (a USB/Bluetooth thermal printer with its driver installed shows up
      as a normal printer). Prints TWO copies in one shot — CUSTOMER COPY +
      RESTAURANT COPY, separated by a cut line. Pure client-side (hidden iframe +
      window.print()), no backend, no hardware integration. Honest limits: relies
      on the OS print dialog (cashier picks the thermal printer once / sets it as
      default); 58mm rolls may scale the 72mm layout to fit. LATER upgrade for a
      one-tap SILENT print = direct ESC/POS via WebUSB / Web Bluetooth (no dialog);
      plus a dedicated KOT (kitchen ticket) print — see the KOT item below.
- [ ] **Phase 3b — automated EMAIL / SMTP bill delivery (design decided 2026-06-25).**
      Today email = a `mailto:` the cashier sends by hand; this is the automatic
      server-side version. Open questions resolved:
      • WHO sends: send from OUR platform address (e.g. bills@guhya.co.in), NOT
        the restaurant's own email. Set From display-name = the restaurant's name
        and Reply-To = the restaurant's own contact email, so the mail reads as
        "Cafe Gopala <bills@guhya.co.in>" and customer replies go to the cafe.
        Standard SaaS pattern (Square/Stripe receipts). Restaurants DON'T run
        their own mail — they just set an optional reply-to/contact email.
        (Sending AS their Gmail is rejected — we can't SPF/DKIM-sign for gmail.com,
        and an app-password per owner is high-friction + a stored-password
        liability. So: platform-sends-on-behalf-of.)
      • PREREQ: add `Customer.email` (capture in the bill customer bar) — can't
        auto-email without the address. Add `tenant.reply_to_email` (+
        `email_enabled`) to Settings.
      • MAILCOW must be configured to SEND (installed but bare). Checklist (mostly
        infra — mirror into avyangah-infra):
          - sending domain + mailbox/relay account (bills@…),
          - DELIVERABILITY DNS (make-or-break): SPF, DKIM (mailcow generates the
            key → publish the TXT), DMARC, and PTR / reverse-DNS on the Hetzner IP
            (missing PTR → Gmail rejects); check the IP isn't on blocklists,
          - confirm Hetzner isn't blocking OUTBOUND port 25 (often blocked by
            default; without it the box can't deliver to other mail servers),
          - Django EMAIL_* → mailcow submission (587 STARTTLS, auth as bills@…),
            creds in avyangah-infra secrets/env, NEVER in code.
      • Make the email backend PLUGGABLE (like the menu-AI provider): plain Django
        EMAIL_BACKEND/SMTP settings so we can swap mailcow ↔ a transactional API
        without code changes.
      • HONEST DELIVERABILITY RISK: self-hosted mail from a fresh domain/IP has no
        reputation; even with SPF/DKIM/DMARC/PTR perfect, early sends can spam-
        folder or throttle. Transactional bills (low volume, expected by the
        recipient) usually inbox OK, but it's the #1 risk. FALLBACK if inboxing is
        poor: a transactional email API with a free tier — Amazon SES (~free low
        volume), Brevo (300/day free), Resend (3k/mo free) — they own reputation/
        deliverability. Decide mailcow-vs-API after testing real placement.
      • THE ACTUAL "FILE" (PDF bill): wa.me + mailto carry TEXT only — they can't
        attach a file. A real PDF / thermal receipt as an ATTACHMENT only works
        over server-side email (SMTP). So "send the customer a proper bill file" =
        this SMTP path + a PDF generator (sub-task below).
- [ ] **PDF / printable bill generation.** Render the bill as a PDF (and a thermal
      2-inch layout) so it can be ATTACHED to the SMTP email above, printed, or
      downloaded. Reuse ONE bill-render template for screen + PDF + KOT. Needed
      before email-with-attachment is meaningful (text-only bills don't need it).
- [ ] **SMS bill channel (NOT free — later).** For customers with no WhatsApp /
      Telegram / email, SMS is the lowest-common-denominator. In India this needs
      a provider (MSG91 / Gupshup / Twilio) + DLT template registration + per-SMS
      cost. Park until there's demand; the printed/thermal receipt is the always-
      works offline fallback meanwhile.
- [ ] **Attendance — biometric device integration (Cafe Gopala already OWNS the
      hardware).** They have a Petpooja payroll/attendance biometric marker
      (Bluetooth/WiFi) — refs: posmarket.in petpooja-payroll-attendance device +
      the Petpooja attendance YouTube demo. GOAL: feed its fingerprint punches
      straight into our `Attendance` table (no PINs once it works). REALITY CHECK
      / it depends entirely on the exact model — these are usually rebranded
      ESSL / ZKTeco / Mantra units:
        • If it's a WiFi/LAN unit that speaks the ADMS / iclock PUSH protocol with
          a CONFIGURABLE server URL → point it at our own ingest endpoint and
          punches flow in. Very doable. (Build: a device adapter endpoint that
          maps the device's user-id → our User and writes Attendance rows; the
          owner maps each device-id to a staff member once.)
        • If it ONLY pairs over Bluetooth to Petpooja's own app, or its firmware is
          LOCKED to Petpooja's cloud → we can't read it; owner needs a generic
          ESSL/ZKTeco WiFi device (cheap, ~₹3–5k) that allows a custom server.
      ACTION: get the exact device model/brand (photo of the back label) to pick
      the path. Meanwhile the PIN clock-in already gives anti-cheat attendance
      today. PAYROLL CALCULATION stays a LATER add-on — capture first; the v1
      hours/days/pay summary already shipped, refine the rules later.
      USB-FINGERPRINT OPTION (cheapest hardware, India): a Mantra MFS100 (~₹2k) /
      SecuGen Hamster Pro / Morpho MSO is the lowest-cost scanner — BUT a browser
      can't talk to it directly; these need the vendor RD-Service/SDK (a small
      Windows/Android helper exposing a localhost endpoint) + a tiny local bridge
      WE build to capture → match a template → POST a punch. Needs a Windows PC at
      the counter + per-staff fingerprint ENROLMENT + 1:N matching that we own.
      Trade-off: USB scanner = cheapest hardware but most dev + tied to one PC;
      standalone ZKTeco/ESSL WiFi (ADMS push) = slightly more hardware cost but
      far less integration and runs as a wall appliance. Both just write the SAME
      Attendance rows through one ingest endpoint — pick by the counter setup
      (Windows billing PC already there → USB viable; no PC / wall mount → WiFi
      device).

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

- [ ] **Capture customer → WhatsApp bill + UPI QR (PULLED UP; the Trojan horse).**
      A cafe can't run a day without clean UPI, and capturing the phone at billing
      seeds the whole CRM wedge (this IS section C's "customer database"). Two phases:

      **Phase 3a — free, works today, no external accounts:**
      - **Customer capture.** Optional phone (+ name) on any order, dine-in OR
        takeaway. MUST be one-tap-skippable so it never slows the queue. Entering
        a phone upserts a tenant-scoped `Customer` (phone unique per tenant) and
        links it to the order — quietly building the customer DB (visit count /
        total spent / last order denormalised for CRM later). Keep a CONSENT flag
        from the start (see privacy note).
      - **Per-tenant UPI settings (CONFIGURABLE, never hardcoded).** Owner enters
        their UPI VPA once (e.g. cafegopala@okhdfcbank) + display name in Settings.
        Stored on the tenant (alongside the future branding record). The UPI QR
        feature activates for a restaurant ONLY once its owner has filled this in
        — Praveen supplies Cafe Gopala's as the first tenant; every other
        restaurant/hotel owner sets their own. Build it configurable so it simply
        switches on once set up correctly.
      - **Dynamic UPI QR at payment.** Generate `upi://pay?pa=<vpa>&pn=<name>&am=
        <total>&tn=<order ref>&cu=INR` and render as a QR. Customer scans → amount
        + note prefilled → pays. FREE to generate (no gateway, no fees). CAVEAT:
        the POS can't AUTO-confirm without a gateway — cashier still taps "paid"
        once money lands in their UPI app. Zero-cost and good enough.
      - **WhatsApp bill via click-to-chat.** Build bill text + a
        `https://wa.me/<phone>?text=<url-encoded bill>` link the cashier taps to
        send. No API, no template approval, no cost. Limitation: manual tap, from
        the cashier's own WhatsApp.

      **Phase 3b — later, needs accounts / approval / cost:**
      - **WhatsApp Business API** (BSP: Meta Cloud API / Gupshup / Twilio) to
        AUTO-send and message at scale. KEY CONSTRAINT: you can't freely message
        customers — business-initiated messages need a Meta-approved UTILITY
        template (bills/receipts qualify); free-form replies only inside the 24h
        window AFTER the customer messages you. Compliant cheap inbound pattern =
        a "WhatsApp us / scan for your bill" QR at the table; once the CUSTOMER
        messages first, reply freely with bill + offers. Per-message cost +
        business verification + approval lead time. (Re-check WhatsApp pricing/
        policy at build time — it changes.)
      - **Payment gateway** (Razorpay / Cashfree / PhonePe PG) + webhook → true
        pay-from-phone AND automatic reconciliation (POS knows it's paid). Fees +
        KYC. This is "online payment later".

      **Thermal receipt / KOT print** rides alongside (Web Bluetooth / WebUSB from
      the PWA; 2-inch formatting quirks — budget time).

      PRIVACY: storing a number for a transactional bill is fine; WhatsApp
      MARKETING later needs explicit opt-in (DLT-style consent) — hence the
      consent flag on `Customer` from day one, so the wedge stays compliant.

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

## Inventory & stock (requested 2026-06-25 — started vs sold vs left, with a log)

Two levels. Do the LIGHT one first; the heavy ingredient/recipe one only when a
bigger kitchen actually needs it and will keep the data accurate during a rush.

- [ ] **Phase 1 — item-level stock (light, right for Cafe Gopala).** Per menu
      item, an OPTIONAL stock count: owner sets the OPENING / prepped qty for the
      day; each sale auto-DECREMENTS it. Cashier/owner sees SOLD vs REMAINING at
      a glance; item auto-marks unavailable ("86'd") at zero; low-stock badge
      under a threshold. Items can be "untracked" (e.g. tea/coffee) so you only
      track what matters (e.g. 30 biryanis prepped today). Manual adjustments —
      restock, waste/spoilage, correction — each with a reason.
- [ ] **Stock movement LOG (the audit trail you asked for).** Every change is one
      row: type (opening / restock / sale / adjustment / waste / void-return),
      item, qty delta, balance-after, reason, linked order (for sales), user,
      timestamp. This is the "how much started, how much sold, how much left, who
      changed it" record. Voids/cancels RETURN stock. Feeds day-close + reports.
- [ ] **Surfacing.** "Orders done today" + per-item sold counts on the owner Home
      / day-close (we already have order + line data; Phase-1 stock adds the
      "remaining" column). Plugs into Reports (#6) and later the AI "Know" layer
      ("how many biryanis left?").
- [ ] **Phase 2 — ingredient / recipe (BOM) inventory (heavy; later, bigger
      kitchens / upsell tier).** Raw-ingredient master with units (kg / L / pcs),
      a recipe per dish (1 masala dosa = X batter + Y potato) so a sale depletes
      INGREDIENTS, not just the dish. Adds supplier/vendor + purchase / GRN
      entries, reorder levels + alerts, food costing / COGS + margin per dish,
      and wastage tracking. **AI invoice digitisation** (scan a supplier bill ->
      stock-in + payables, reuse the Gemini/DocSign pattern) feeds this. Gate it
      behind a higher tier; don't build the inventory mountain before the POS is
      earning its keep.

NOTE: this supersedes the one-line "Inventory + recipe management" in the
competitive table-stakes list (section A) and the Phase-2 inventory bullet in the
"Ask. Know. Act." section — same feature, specced here.

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
- [ ] **Platform support role (`pos_admin`).** A cross-restaurant support/staff
      role (separate from the Django superuser) that can access ANY tenant to
      help with support — read, and assist where needed. Today the only
      cross-tenant account is the Django superuser (now hidden from per-restaurant
      staff lists). Add a proper scoped support role so support staff can help
      tenants WITHOUT sharing the superuser, every action audit-logged. Build when
      there are multiple live tenants / alongside onboarding.

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
- EVERYTHING restaurant-specific is PER-TENANT and owner-configured in Settings —
  never hardcoded for Cafe Gopala. UPI VPA + payee name, GST number, business
  name / address / phone, bill footer, logo + brand colours all live on the
  Tenant, and each owner fills in their own. Praveen supplies Cafe Gopala's as
  the first tenant; every other restaurant/hotel self-configures. Build each such
  feature as CONFIGURABLE so it simply "switches on" once that owner has set it up
  correctly — no code change per customer.
- Match features to the customer: dead-simple for one-person eateries, fuller
  tiers for bigger restaurants. Don't force big-kitchen features on small ones.
- Flat SaaS fee, not per-order commission — "friend to the restaurant."
- The moat is the integrated stack (POS + own online ordering + voice + this
  assistant), which is a reason for a restaurant to stay.
- White-label theming is part of the moat too: it's THEIR brand, not ours.
