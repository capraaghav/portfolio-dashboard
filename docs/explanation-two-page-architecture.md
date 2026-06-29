# Explanation — Why the product is two separate pages

> Diátaxis: **Explanation.** The reasoning behind splitting the marketing page from
> the app, the failure that forced it, and the cost we accepted in return.

## The problem

The product wears two hats, and the two hats want opposite things:

- **The marketing landing** wants to be a fast, static, anonymous, SEO-friendly page
  that loads instantly and sells the idea. No login, no Python runtime, no cold start.
- **The app** wants to be a stateful, authenticated, Python/Streamlit application with
  per-user data, caches, and a server warming up on first hit.

A single page can't be both well. A static HTML page can't run the dashboard; a
Streamlit app makes a poor landing page (cold-start spinner, no SEO, heavyweight for a
"what is this?" visitor). So the product is **two pages on two hosts**:

```
   capraaghav.github.io/portfolio-dashboard/        portfolio-dashboard-1.streamlit.app
   ┌────────────────────────────────────┐          ┌────────────────────────────────────┐
   │  index.html  (GitHub Pages)         │          │  app.py  (Streamlit Cloud)          │
   │  static · anonymous · instant       │          │  login + dashboard · per-user state │
   │                                     │          │                                     │
   │  "Launch dashboard →"  ───────────────────────▶│  (auth gate, then the 13 sections)  │
   │                                     │          │                                     │
   │◀─────────────────  "New here?       │          │  render_landing():                  │
   │                     See what it does"│         │    "New here? See what it does →"   │
   └────────────────────────────────────┘          └────────────────────────────────────┘
            APP_URL constant                                  LANDING_URL constant
```

## The failure that drove it

The obvious-looking shortcut was to keep **one** product surface: embed the marketing
`index.html` *inside* the Streamlit app (in an `iframe` / HTML component) so visitors
land on the app and see the marketing hero first.

That broke in a specific, self-inflicting way. The landing page's primary call to
action is a **"Launch dashboard"** button pointing at the app. But the landing was now
rendered *inside the app's own iframe*. So clicking "Launch dashboard":

```
   app
   └─ iframe: index.html
              └─ click "Launch dashboard" → loads the app
                 └─ iframe: index.html
                            └─ click "Launch dashboard" → loads the app
                               └─ iframe: index.html
                                          └─ … (infinite nesting)
```

The button loaded the app *inside the iframe that was already inside the app* —
the app nested inside itself, recursively, every click. There is no clean fix from
inside that arrangement: the landing's whole purpose is a button that opens the app,
and the moment the landing lives inside the app that button is a recursion trap.

The resolution was to **stop embedding**. The full marketing page lives entirely
separately as static `index.html` on GitHub Pages. The app shows only a *compact*
in-app hero (`render_landing()` in `app.py`) — a few lines of headline plus a text
link back to the real landing — never the landing page itself in a frame.

## The trade-off we accepted

Two pages on two hosts means the cross-links can't be relative; each side hardcodes
the other's absolute URL as a constant:

| Side | File | Constant | Points at |
|------|------|----------|-----------|
| Landing → App | `index.html` | `APP_URL` (`<script>`, ~line 914) | the Streamlit app |
| App → Landing | `app.py` | `LANDING_URL` (top of file) | the GitHub Pages landing |

```
   index.html : const APP_URL = "https://portfolio-dashboard-1.streamlit.app/";
   app.py     : LANDING_URL   = "https://capraaghav.github.io/portfolio-dashboard/"
```

These two constants **must stay in sync** with where each page is actually deployed.
If either deployment URL changes and its partner constant isn't updated, the
cross-link silently points at the wrong place (or nowhere). This is real coupling and
the price of the split — but it is two string constants, checked in plain sight, with
the alternative being the recursion trap above. The reciprocal links keep the two
pages feeling like one product:

- **Landing → App:** every "Launch dashboard" / "Open app" CTA (`data-app-url`,
  rewritten to `APP_URL` by the page's own script).
- **App → Landing:** `render_landing()`'s **"New here? See what it does →"** link, and
  the auth gate's hero, both pointing at `LANDING_URL`.

A logged-out visitor who hits the app directly still gets the compact hero + login
form (not a blank page), with the path back to the full pitch one link away.

## Related explanations

- [explanation-architecture.md](explanation-architecture.md) — what the app does once
  you're past the auth gate.
- [explanation-storage-backends.md](explanation-storage-backends.md) — the auth gate
  and per-user persistence that make the app the "stateful" half of the split.
- [reference-modules.md](reference-modules.md) — `render_landing`, `LANDING_URL`, and
  the auth functions in reference form.
