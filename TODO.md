# guhya-pos — roadmap / todo

The POS core (multi-tenant data model + cashier API + blue/green deploy) is
done and pushed. This is the backlog, roughly in priority order. Each item is
staged so we ship something usable at every step rather than a big-bang.

## Now / next
- [ ] **Deploy to pos.guhya.co.in** and run `migrate` on the server (test box).
- [ ] **Kitchen display (KDS)** over WebSockets — live order/line status push.
      Redis is already in the compose file. Cashier "send to kitchen" -> screen
      updates instantly; kitchen marks items ready -> flows back to the floor.
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
