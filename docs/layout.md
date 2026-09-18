# Layout Spec

Screen-by-screen build target. Decisions and their reasoning live in
`decisions/README.md`; this file is the *what*, not the *why*.

Theme: **The Green Bench** (D24). Felt green, brass, cream parchment.
Nothing below 11px.

---

## Routes

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | The Filing Desk — ask, and hear, in place |
| `/council` | POST | Create a run, return the board fragment (no redirect, D25) |
| `/council/{id}/stream` | GET | SSE — one verdict per event |
| `/council/{id}` | GET | Read-only past verdict. No animation, no sound |
| `/bench` | GET | The Bench — roster, toggles, presets |
| `/bench/new` · `/bench/{id}/edit` | GET/POST | Commission or amend a duck |
| `/bench/active` | POST | Update the sitting roster |
| `/history` | GET | The Register |
| `/providers` | GET/POST | Provider and model choice, keys (D27) |

Routes are named plainly for anyone reading the code. The theme lives in the
UI labels: *The Bench*, *The Register*, *Chambers*.

---

## 1. `/` — The Filing Desk

### State A — asking

```
┌─ felt green masthead ──────────────────────────────┐
│            ( seal )   THE DUCK COUNCIL             │
└────────────────────────────────────────────────────┘

            The Council will hear your case
        ────────────────────────────────────

   ┌── I. THE SITUATION ──┬── II. THE ACTION PROPOSED ──┐
   │  [ textarea        ] │  [ textarea               ] │
   └──────────────────────┴─────────────────────────────┘

              [  Submit to the Council  ]

        ◉◉◉◉◉◉◉   7 sitting · change the bench

        The Bench  ·  The Register  ·  Chambers
```

- The `I. / II.` block is **the same component** as the case caption in State B.
  Editable here, read-only there. What you fill in becomes the filing.
- Roster strip: active duck portraits, small, brass-ringed, linking to `/bench`.
- Navigation sits **below** the block (D27) — the fields are the product.

### State B — deliberating, then heard

Submit posts via HTMX. No navigation (D25).

1. Form collapses into the read-only case caption (animated height).
2. Board renders **at full size immediately** — one empty seat per sitting
   duck, so the grid height is fixed before any verdict exists (D26).
3. Verdicts stamp into their reserved seats as they arrive over SSE.
4. The finding — medallion score, engraved scale bar — appears after the last
   seat fills, with a single gavel.
5. Footer actions: *Ask something else* (restores the form) ·
   *Change the bench and re-hear*.

**Crisis register (D20)** replaces everything from step 2: no board, no score,
no ducks. One cream panel, plain type, a resource link. The board never renders.

---

## 2. `/bench` — The Bench

The quest board component again, with duck **profiles** instead of verdicts.

```
   [ The Full Council ] [ The Serious Five ] [ Chaos Council ]   ← presets

  ╔═ timber board ══════════════════════════════════════╗
  ║  ┌ notice ─────────┐   ┌ notice ─────────┐          ║
  ║  │ portrait    [on]│   │ portrait   [off]│          ║
  ║  │ Name            │   │ Name  (greyed,  │          ║
  ║  │ voice / weighs  │   │  unpinned, slid)│          ║
  ║  └─────────────────┘   └─────────────────┘          ║
  ║  ┌ + COMMISSION A DUCK ┐                            ║
  ╚═════════════════════════════════════════════════════╝
```

- **Inactive ducks render unpinned** — no brass stud, desaturated portrait,
  sitting slightly lower and more askew, as though fallen off the board.
  The toggle *is* the pin.
- Built-in ducks: toggle only. User ducks: edit and delete (D14).
- Last cell is an empty notice reading **+ Commission a duck**.
- Presets are brass tabs above the board (D23). Selecting one sets the roster.
- Guard: the last active duck cannot be switched off.

---

## 3. `/bench/new` · `/bench/{id}/edit` — Commission a Duck

A single large parchment notice, centred on the board.

| Field | Note |
|---|---|
| Name | The duck's name as it appears on the bench |
| Voice | How it talks — flavour only |
| Weighs | What actually moves its score |
| Blind spot | What it under-weights on purpose |

Live monogram preview beside the fields (initials + deterministic colour, D14).
Helper text explains that *voice* is flavour and *weighs* is the judgement —
that split is the whole reason scores diverge (D5), and a user who misses it
will build a duck that agrees with everyone.

---

## 4. `/history` — The Register

Not the board. A bound ledger: ruled rows on cream, brass rules.

```
  ── THE REGISTER ────────────────────────────────────
   (55)  "quit my job to go full-time on the app"
         9 sitting · split · 2 hours ago
  ────────────────────────────────────────────────────
   (81)  "tell my landlord about the leak"
         5 sitting · agreed · yesterday
```

Score as a small brass medallion. Each row links to `/council/{id}`.

---

## 5. `/providers` — Chambers

Its own page, not a settings tab (D27).

- Provider cards: **Local Claude** · **Anthropic (key)** · **OpenAI (key)** ·
  **Ollama (local)** · **Demo (no key)**.
- Model select per provider. Global default with optional per-duck override (D19).
- Key fields render masked as `configured · …3f9a` and never echo a stored
  value back into the form (D12).
- When `SecretStore` is not writable — in Docker, where there is no OS keyring —
  a brass banner says so and the key form is hidden rather than silently
  failing to save (D18).

---

## Components

| Component | Used by |
|---|---|
| `_caption.html` | `/` state A (editable) and state B (read-only) |
| `_board.html` | `/` state B, `/council/{id}`, `/bench` |
| `_notice.html` | verdict, duck profile, empty seat, commission-a-duck |
| `_medallion.html` | notice scores, register rows, the finding |
| `_scalebar.html` | the finding |
| `_roster_strip.html` | `/` state A |

`_notice.html` carrying four states is the load-bearing reuse. One template,
one visual language, four jobs.

---

## Motion and sound (D26)

```
  0%   opacity 0, scale 1.6, translateY -40px, rotate(--rot)
  60%  opacity 1, scale 0.97, translateY 0        ← impact, sound fires
  78%  scale 1.02                                  ← overshoot
  100% scale 1                                     ← settle
```

Board jolts 2px at impact. Total ~380ms.

- 3–4 stamp samples, chosen at random, `playbackRate` detuned ±4% per duck.
- One gavel for the finding.
- Brass mute toggle, persisted in `localStorage`.
- `prefers-reduced-motion` reduces the slam to a fade; audio is governed by the
  toggle, not the motion query.
- Audio never gates content. If `play()` rejects, the verdict still lands.

### Where to get the sounds

| Source | License | Notes |
|---|---|---|
| [Pixabay SFX](https://pixabay.com/sound-effects/) | Pixabay Content License | **Best choice** — no attribution, commercial OK, nothing to add to the repo |
| [Mixkit](https://mixkit.co/free-sound-effects/) | Mixkit Free License | No attribution required |
| [Freesound](https://freesound.org) | Mixed — filter to **CC0** | Largest library, but CC-BY means an attribution file and CC-BY-NC is unusable here |

Search: `rubber stamp`, `stamp paper`, `wood thud`, `paper slam`, and `gavel`
for the finding. Keep each under ~30KB as `.mp3`, preloaded on submit.

For a portfolio repo, prefer CC0 / no-attribution so licensing never becomes a
thing a reviewer has to check.
