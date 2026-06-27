---
name: Portfolio Dashboard — Indian Markets
description: A low-lit, champagne-gold portfolio terminal where the numbers glow and the chrome recedes.
colors:
  gold: "#C9A87A"
  gain: "#3DDC97"
  gain-deep: "#1F9E6B"
  loss: "#F0564A"
  loss-deep: "#A8362C"
  bg: "#0A0A0A"
  sidebar: "#0C0C0C"
  surface: "#141414"
  surface-container: "#121212"
  surface-hover: "#161616"
  surface-selected: "#18170F"
  shimmer: "#1F1F1F"
  border-hairline: "#1C1C1C"
  border-container: "#232323"
  border-card: "#262626"
  border-control: "#2A2A2A"
  ink: "#EDEDED"
  ink-soft: "#B9B9B9"
  muted: "#8B8B8B"
  muted-deep: "#808080"
  disabled: "#555555"
typography:
  display:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "3.4rem"
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "{typography.display.fontFamily}"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  title:
    fontFamily: "{typography.display.fontFamily}"
    fontSize: "1.65rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "normal"
  body:
    fontFamily: "{typography.display.fontFamily}"
    fontSize: "0.95rem"
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "{typography.display.fontFamily}"
    fontSize: "0.72rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.08em"
  brand:
    fontFamily: "{typography.display.fontFamily}"
    fontSize: "1.3rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "0.18em"
rounded:
  sm: "8px"
  md: "10px"
  lg: "12px"
  xl: "14px"
  xxl: "16px"
spacing:
  xs: "0.2rem"
  sm: "0.5rem"
  md: "0.7rem"
  lg: "1.1rem"
  xl: "1.4rem"
components:
  metric-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.xl}"
    padding: "1rem 1.1rem"
  container-card:
    backgroundColor: "{colors.surface-container}"
    textColor: "{colors.ink}"
    rounded: "{rounded.xxl}"
    padding: "1.1rem"
  button-secondary:
    backgroundColor: "{colors.surface-hover}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0.4rem 0.9rem"
  button-secondary-hover:
    backgroundColor: "{colors.surface-hover}"
    textColor: "{colors.gold}"
    rounded: "{rounded.md}"
    padding: "0.4rem 0.9rem"
  nav-item:
    backgroundColor: "{colors.sidebar}"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.md}"
    padding: "0.5rem 0.7rem"
  nav-item-selected:
    backgroundColor: "{colors.surface-selected}"
    textColor: "{colors.gold}"
    rounded: "{rounded.md}"
    padding: "0.5rem 0.7rem"
  hero-value:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.gold}"
    typography: "{typography.display}"
    padding: "0"
---

# Design System: Portfolio Dashboard — Indian Markets

## 1. Overview

**Creative North Star: "The After-Hours Desk"**

This is the analyst's desk after market close: the room is dark, the screen is the
only light source, and a single warm lamp — champagne gold — pools over the figures
that matter. Everything here is built so the **numbers glow and the chrome recedes**.
The canvas is a near-black `#0A0A0A` room; surfaces are barely-lighter panels stacked
in tight tonal steps (`#0C0C0C` → `#121212` → `#141414` → `#161616`); the only color
with any saturation is the gold accent and the mint/coral of profit and loss. Nothing
blinks, nothing celebrates, nothing hurries. The cadence is reflective — a person
reviewing what they own, not reacting to a tick.

The system is **Restrained** in the strict sense: tinted near-blacks plus one accent
held to roughly a tenth of any screen. Density is welcome where the user wants it —
holdings tables run wide and dense, fundamentals stack many labels — but density is
earned by the data, never manufactured by decoration. Depth is conveyed by tone, not
shadow: this is a flat system where one surface sits above another because it is a
half-step lighter, the way objects separate under low light.

It explicitly **rejects** three things its users have seen too much of: the **loud
retail trading app** (neon green/red, gamified gains, dopamine confetti); the
**cluttered Bloomberg terminal** (wall-to-wall data with no hierarchy or air); and
**cartoonish playful fintech** (mascots, bright illustration, "friendly money"
styling). It also rejects generic SaaS slop — purple gradients, gradient text,
identical icon-card grids, the hero-metric template.

**Key Characteristics:**
- Low-light dark room; data is the only thing that glows.
- One accent (champagne gold), held rare; restraint *is* the identity.
- Tonal layering over shadows — depth from lightness steps, surfaces flat at rest.
- Inter everywhere, in weight — no display/body pairing.
- Numbers are the hero: typography and spacing do the work, decoration does none.
- P&L never relies on color alone — sign and figure carry the meaning too.

## 2. Colors

A near-black room lit by a single warm lamp, with mint and coral reserved strictly for
profit and loss.

### Primary
- **Champagne Gold** (`#C9A87A`): the lamp. The one saturated voice in the system —
  used for the brand wordmark, the hero portfolio value, the selected nav item,
  primary chart lines/gauges, button hover, and the click-spark. It marks *where the
  user is* and *what the headline number is*, nothing decorative. Its rarity is the
  entire point.

### Secondary
- **Mint Gain** (`#3DDC97`): positive P&L — gains, upside %, bullish signals,
  the warm pole of the treemap heatmap.
- **Coral Loss** (`#F0564A`): negative P&L — losses, downside, bearish signals,
  the cool pole of the heatmap.
- **Deep Gain** (`#1F9E6B`) / **Deep Loss** (`#A8362C`): the saturated extremes for
  *Strong Bullish* / *Strong Bearish* states and the ends of the heatmap scale.

### Neutral
- **Room Black** (`#0A0A0A`): the app canvas — the dark room itself.
- **Panel Steps** (`#0C0C0C` sidebar · `#121212` container cards · `#141414` metric
  cards/surface · `#161616` hover · `#18170F` selected-nav, a gold-tinted black ·
  `#1F1F1F` skeleton shimmer): the stacked surfaces, each a controlled half-step
  lighter than the one beneath. Depth lives entirely in this ramp.
- **Hairline Borders** (`#1C1C1C` dividers/sidebar edge · `#232323` containers ·
  `#262626` metric cards · `#2A2A2A` controls): borders are whispers, never strokes.
- **Ink** (`#EDEDED` primary text · `#B9B9B9` nav default · `#8B8B8B` labels/secondary
  · `#808080` tertiary/muted · `#555555` disabled/N-A): a five-step grey ramp from
  near-white headlines down to disabled. The ramp bottoms out at `#808080` for any
  *text* role (5.0:1 on the canvas — AA-safe); `#555555` and below are for disabled
  glyphs and hairlines only, never readable text.

### Named Rules
**The One Lamp Rule.** Champagne gold appears on no more than ~10% of any screen, and
only to mark the brand, the single headline figure, the current selection, or a state.
The moment gold is used decoratively, the room stops being lit and starts being
painted — and the whole metaphor collapses.

**The P&L Is Not Just Color Rule.** Gains and losses are *never* communicated by mint
vs. coral alone. The sign (`+`/`−`), the formatted figure, or a label always rides
alongside the color, so a color-blind user reads the position correctly. Color is the
amplifier, never the only channel.

## 3. Typography

**Display Font:** Inter (with `-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`)
**Body Font:** Inter — same family, in weight
**Label/Mono Font:** Inter (no separate mono; tabular figures via Inter's numerals)

**Character:** One humanist-geometric sans carries the entire system — headings,
labels, buttons, body, and dense tabular data. There is no pairing, by design: a
finance tool earns trust through consistency, not typographic flourish. Hierarchy comes
from weight (400→800) and a tight size scale, not from contrasting families. Headings
are weighted and slightly negative-tracked for a composed, edited feel; labels are the
opposite — small, semibold, and positively tracked into quiet uppercase.

### Hierarchy
- **Display** (800, `3.4rem`, line-height 1.05, `-0.02em`): the centered hero portfolio
  value, in gold. Appears once per overview — the headline figure of the whole desk.
- **Brand** (800, `1.3rem`, `+0.18em`, uppercase): the `PORTFOLIO` sidebar wordmark —
  wide-tracked, the one place tracking goes loud, as a logotype not a heading.
- **Title** (700, `1.65rem`): metric-card values — the per-card numbers users scan.
- **Headline** (700, `1.5rem`, `-0.01em`): section titles within a tab.
- **Body** (500, `0.95rem`, line-height 1.5): nav labels, control text, prose. Cap
  prose at 65–75ch; tables and dense panels may run wider.
- **Label** (600, `0.72rem`, `+0.08em`, uppercase): metric-card labels, hero eyebrow —
  the quiet small-caps that name a figure without competing with it.

### Named Rules
**The One Family Rule.** Inter does everything. Introducing a second typeface — a serif
for "elegance", a mono for "data" — is forbidden; it reads as costume, not craft. Range
lives in weight and size, never in family.

**The Quiet Caps Rule.** Uppercase is reserved for small tracked labels (`0.72–0.8rem`)
and the brand wordmark. Never set a heading or a value in caps; shouting is not
hierarchy.

## 4. Elevation

This is a **flat, tonally-layered** system. There are effectively **no drop shadows**.
A panel reads as "above" the canvas because it is a half-step lighter (`#121212` /
`#141414` floating on `#0A0A0A`) and ringed by a hairline border (`#232323`–`#262626`),
exactly the way objects separate under low ambient light. Depth is lightness, not cast
shadow. The only "glow" in the system is the click-spark and the gold accent itself —
light emitted by the data, never a shadow beneath a card.

### Named Rules
**The Tonal-Depth Rule.** Separation between surfaces is achieved with the panel-step
ramp plus a hairline border, never with `box-shadow`. If a surface needs to feel
higher, lighten it one controlled step; do not float it on a shadow. A drop shadow on a
card here is a bug, not a style.

## 5. Components

### Buttons
- **Shape:** softly rounded (`10px`).
- **Secondary (default and only style):** surface `#161616`, ink `#EDEDED`, `1px`
  border `#2A2A2A`, weight 500. There is no filled "primary" button — actions are
  understated; the gold is spent on the data, not on the controls.
- **Hover / Focus:** border and text both shift to champagne gold (`#C9A87A`) over a
  ~150ms transition. The control lights up to the lamp on contact, then releases.

### Cards / Containers
- **Metric card:** surface `#141414`, `1px` border `#262626`, radius `14px`, padding
  `1rem 1.1rem`. Label is small uppercase muted (`#8B8B8B`); value is `1.65rem`/700
  ink; delta carries the mint/coral.
- **Container card:** surface `#121212`, `1px` border `#232323`, radius `16px` — the
  larger wrapper around charts and tables.
- **Shadow Strategy:** none — see Elevation. Tonal step + hairline border only.
- **Corner Style:** consistently rounded; `14–16px` on cards, smaller on controls.
- **Nesting:** never nest a card inside a card. A container card holds content, not
  more cards.

### Inputs / Fields
- **Style:** dark surface, hairline border, rounded to match controls; Inter at body
  size. Inherits the dark BaseWeb theme (`#141414` field on `#0A0A0A`).
- **Focus:** border shifts toward gold; keep the focus ring visible for keyboard users.
- **Placeholder:** must clear 4.5:1 against the field — do not let it fall to the
  muted-deep greys.

### Navigation (Sidebar)
- **Style:** vertical radio group restyled as a nav list on the `#0C0C0C` sidebar, set
  off from content by a `#1C1C1C` right border. The native radio dot is hidden.
- **Default:** label `#B9B9B9`/500, transparent background.
- **Hover:** background lifts to `#161616`.
- **Active/Selected:** background `#18170F` (a gold-tinted black), label gold
  (`#C9A87A`)/600. The selection is the only lit item in the list.
- **Above it:** the `PORTFOLIO` wordmark (gold, wide-tracked) with a muted uppercase
  sub-label.

### Hero Value (signature component)
A centered block — small uppercase eyebrow (`#8B8B8B`), then the portfolio value at
`3.4rem`/800 in gold, then a P&L line where the figure is colored mint/coral by sign
and always carries `+`/`−` and the percentage. This is the single loudest moment in the
entire product, and it is loud only once.

### Skeleton Loader (signature component)
Loading is a **dashboard-shaped skeleton**, never a spinner: shimmer bars
(`linear-gradient(90deg, #141414, #1F1F1F, #141414)` sweeping over ~1.4s) laid out as
the eyebrow, hero, four metric cards, and a chart block — so the page's real geometry
is visible while the cold data load runs. Honor `prefers-reduced-motion`: hold the
mid-tone steady instead of animating the sweep.

### Click-Spark (signature flourish)
A global micro-interaction: gold sparks (`#C9A87A`, 9 sparks, ~30px radius, 400ms)
radiate from every click. The one piece of pure delight in the system — small, fast,
on-brand, and gone before it distracts. Must respect `prefers-reduced-motion`.

## 6. Do's and Don'ts

### Do:
- **Do** keep champagne gold (`#C9A87A`) to ~10% of any screen — brand, the one
  headline figure, current selection, and states only (**The One Lamp Rule**).
- **Do** convey gains/losses with sign and figure *plus* color, never mint/coral alone
  (**The P&L Is Not Just Color Rule**) — this is a finance tool and AA color-blind
  safety is non-negotiable.
- **Do** create depth with the panel-step ramp (`#0C0C0C`→`#161616`) and hairline
  borders, not shadows (**The Tonal-Depth Rule**).
- **Do** set everything in Inter, varying weight (400–800) and size for hierarchy
  (**The One Family Rule**).
- **Do** verify text contrast against the near-black canvas: `#EDEDED`/`#B9B9B9` are
  safe; `#8B8B8B` (5.8:1) and `#808080` (5.0:1) pass AA — never drop *text* below
  `#808080` (`#555555` and darker are for disabled glyphs and hairlines only).
- **Do** show the dashboard-shaped skeleton on cold loads; never a centered spinner.
- **Do** let tables and panels run dense when the data earns it; lead with the
  consolidated picture and keep heavy analysis behind toggles (**depth on demand**).

### Don't:
- **Don't** build the **loud retail trading app** — no neon green/red, no gamified
  gains, no confetti, nothing that nudges impulsive action. Gains are reported, not
  celebrated.
- **Don't** build the **cluttered Bloomberg terminal** — never dump wall-to-wall data
  with no hierarchy or air.
- **Don't** drift toward **cartoonish/playful fintech** — no mascots, bright
  illustration, or "friendly money" styling. (Emoji tab icons are a Streamlit
  affordance, not license for a playful register.)
- **Don't** ship generic SaaS slop: no purple gradients, **no gradient text**, no
  identical icon-card grids, no hero-metric template.
- **Don't** put a `box-shadow` under a card, or use a `border-left`/`border-right`
  greater than 1px as a colored accent stripe.
- **Don't** introduce a second font family, or set headings/values in uppercase.
- **Don't** spend gold on decoration — a gold divider, a gold-filled button row, a gold
  background — the moment it stops marking meaning, the lamp metaphor dies.
- **Don't** nest a card inside a card.
