# Architecture Decisions

Running log for the v2 rebuild of The Duck Council. Decisions here are
numbered and justified; the reasoning matters as much as the outcome.

Status: **functionality freeze in progress.** Theme/visual design deliberately
deferred until this log is complete.

---

## Context

The user describes a **situation** and the **action** they intend to take.
A council of duck personas each return a suitability score (0-100) and a short
in-character verdict. The app is a **local-first single FastAPI process** with
server-rendered Jinja pages.

---

## Settled

### D1 — Drop CrewAI; call provider SDKs directly
The ducks never collaborate: no delegation, no tools, no shared memory, no
multi-step plans. Thirteen independent single-turn calls is a `map()`, not a
crew. CrewAI cost us a C toolchain in the image (chromadb/onnxruntime pull in
`gcc`/`g++`), agent-loop prompt scaffolding that actively fought our JSON
output, and no control over timeouts, concurrency or structured output.
Replacement is ~100 lines.

**Revisit if** ducks ever debate each other — that is a genuine multi-agent
problem and would justify a framework.

### D2 — One process: FastAPI + Jinja, no separate SPA
Deletes the entire `client/` tree (vite, pnpm, husky, commitlint, shadcn,
tanstack router+query, nginx.conf) and both Dockerfiles. Same-origin removes
CORS entirely, and image URLs become relative paths — which structurally
eliminates the hardcoded `BASE_URL` bug in v1.

### D3 — Scores are picked from ordinal bands, not emitted as numbers
The model returns one of five labels; **the server computes the number.**

    reckless 10 | unwise 30 | defensible 50 | sound 70 | clearly_right 90
    score = band_centre + nudge        (nudge constrained to -10..+10)

Why: LLMs asked for a free 0-100 value cluster in the 65-85 band, favour round
numbers, and are not reproducible run-to-run. Picking from labelled categories
is reliable, guarantees spread across the range, and keeps score arithmetic in
our code where it can be tested. Secondary benefit: a five-way enum is a schema
a small local model can satisfy, which is what makes offline providers viable.

### D4 — Reasoning is generated before the score
Field order in the schema is `read -> band -> nudge -> line`. Generation is
autoregressive: a score emitted before its justification is a guess the model
then rationalises.

### D5 — Personality is split into voice, criteria, and blind spot
v1 fused persona and judgement into one prose backstory and gave all 13 ducks
the *identical* `role`, so they differed in flavour text but agreed on the
number. Split into: `voice` (how it talks), `weighs` (what moves the score),
`blind_spot` (what it under-weights on purpose). The blind spot is what
actually produces divergent scores.

### D6 — One duck, one record
v1 smeared duck identity across six files (`constants.py`, `duck_names.py`,
`duck_data.py`, `agents.yaml`, `tasks.yaml`, and a task map) and they had
already drifted — the rich duck lost its `style` key. Everything derives from
a single record.

### D7 — Structured output enforced by the provider, never parsed from prose
v1 ran `json.loads()` on raw LLM text; one markdown fence lost every duck's
answer including the ones already paid for. Each provider adapter uses its own
native mechanism (Anthropic validates against the Pydantic model directly,
OpenAI uses a strict JSON schema, Ollama uses JSON mode).

### D8 — Ducks run concurrently and fail independently
`asyncio.as_completed` with per-duck error capture. Thirteen sequential calls
is ~26s; concurrent is ~2-3s. One duck failing, timing out, or being refused
costs one duck, not the council. A refusal renders as an empty chair.

### D9 — Results stream into the page over SSE, rendered by Jinja
HTMX (`sse-swap`) with the server rendering `_duck_card.html` per verdict.
No build step, no npm, all rendering stays in Jinja. Ducks land in finish
order, so the council fills in visibly rather than after one long spinner.
The same partial renders both the streamed fragment and the full page reload.

### D10 — Providers sit behind a Protocol; keys are entered in the UI
`Provider` is a `typing.Protocol` with one method. Providers are selectable
per duck, so the council can be mixed (one duck on Claude, another local).

### D11 — ~~Local Claude means the SDK's own local credentials~~ (superseded by D31)
`ant auth login` writes an OAuth profile that a bare client picks up with no
API key. Rejected the Claude Agent SDK: it is the full Claude Code harness
(built-in file/bash tools, agent loop, permissions) and we would spend our
time suppressing it to get one small JSON object back. Offline use is served
by a local model via Ollama instead.

### D12 — Secrets never reach the browser
Stored in the OS keyring, returned to the UI only as
`{configured: true, hint: "...3f9a"}`. Never `localStorage`, never echoed into
a form field. Server binds `127.0.0.1` only, and every mutating request has its
`Origin`/`Host` checked — a localhost server holding API keys is reachable by
any page the user has open in the same browser.

### D13 — Dependency injection via FastAPI `Depends`, no DI container
Justification is testability and a requirement we actually have, not ceremony:
the `Provider` Protocol means the test suite runs against a `FakeProvider` with
zero network calls and deterministic scores, and multi-provider support is a
stated requirement rather than speculative generality. A third-party DI
container would be over-engineering for a codebase this size.

---

### D14 — Built-in ducks are seeded and read-only; users create their own
Every duck is a row with `origin: 'builtin' | 'user'`. The 13 shipped ducks are
seeded on first run and can be toggled on/off but not edited or deleted; user
ducks get full create/edit/delete. Re-seeding on upgrade never touches user
rows, so adding a 14th built-in later is not a destructive migration, and
"restore defaults" is trivial because the originals were never mutable.

A user duck supplies `name`, `voice`, `weighs`, `blind_spot`. Portraits for
user ducks are generated (monogram + deterministic colour from the duck id)
rather than uploaded — no file handling, no broken images, no moderation.

**Guard:** the council requires at least one active duck; the UI cannot toggle
the last one off.

**Prompt injection is in scope but low-severity.** A user-written persona is
free text that lands in our system prompt, so a user can write a duck that
instructs the model to always return `clearly_right`. Single-user local app, so
this is self-sabotage rather than attack — and D3 caps the blast radius, since
the model picks an enum label and *our* code computes the number. Personas are
length-capped and rendered as data, never concatenated into instructions.

### D15 — SQLite behind a repository Protocol
`~/.duck-council/council.db` (located via `platformdirs`), accessed through
`aiosqlite`. Ducks, run history and non-secret settings. Each repository is a
`Protocol` with a SQLite implementation for production and an in-memory one
for tests — the concrete payoff of D13.

Schema versioning is a `user_version` pragma and a small ordered migration
list. Alembic would be over-engineering at this size and a reviewer would
rightly say so.

### D16 — The council verdict is computed, not generated
Median (not mean — the serial-killer duck is a designed-in outlier and a mean
would launder it) plus the spread, rendered as a dissent bar. No extra LLM
call: instant, deterministic, and unit-testable against fixed inputs. A split
council is the more interesting headline anyway, so we surface the widest
disagreeing pair by name.

Rejected: a "chairman" synthesis call. It can only start once every duck is in,
so it would land after the streaming finished and undercut D9's payoff.

### D17 — Ships with a demo provider that needs no API key
`uv run duck-council` opens a working app with zero configuration. The demo
provider returns deterministic verdicts seeded from
`hash(duck_id, situation, action)` — varied and plausible, not placeholder
text — so a reviewer sees the real UI in under a minute. It is the same fake
the test suite uses, so it costs nothing extra to maintain.

Also shipping: `docker compose up` for reviewers without a Python toolchain
(the image is small now that CrewAI's C toolchain is gone), and CI running
lint + type-check + tests.

**Rejected: a hosted public demo.** It contradicts local-first — keys in the
UI, OS keyring, localhost-only binding all assume a single trusted user — and
it costs real money to keep standing.

### D18 — Secret storage is an interface, because Docker has no keyring
D12 (OS keyring) and D17 (Docker) conflict directly: there is no OS credential
store inside a container. So `SecretStore` is a Protocol:

    KeyringSecretStore   -> default, native run
    EnvSecretStore       -> container; read-only, keys come from the environment
    NullSecretStore      -> demo provider only, refuses to store anything

The UI asks the store whether it is writable and hides the key form when it is
not, instead of silently failing to save. Third case where an interface is
earning its place rather than decorating the design.

### D19 — ~~One model default, optional per-duck override~~ (dropped, see D38)
A global provider+model setting covers the normal case; a duck may override it.
Mixed councils (one duck on Claude, another on a local model) fall out for free
because the ducks are independent, and it makes the provider abstraction
visible in the product rather than only in the code.

---

### D20 — The safety gate classifies register, not topic
A topic classifier is wrong for this product. "I'm going to murder my roommate
for eating my leftovers" is the exact input the council exists to roast, and a
gate that keys on the word *murder* would kill the app's whole reason to exist.
The signal we need is **register**: is a real person actually at risk, or is
this hyperbole, a joke, a hypothetical, or fiction?

One cheap call before the fan-out returns one of three registers:

| Register | Meaning | Behaviour |
|---|---|---|
| `play` | Hyperbole, jokes, hypotheticals, fiction, petty grievances | Full council, chaos ducks included. **The default.** |
| `weighty` | A real decision with real stakes — quitting a job, ending a relationship, reporting a crime | Full council. Still funny; the stakes just aren't imaginary. |
| `crisis` | Genuine distress, self-harm, someone in real danger | **No council.** Plain, kind response with a resource link. No score, no ducks. |

Two rules that follow from this:

1. **The gate is tuned to under-trigger.** A false positive — gating a joke —
   destroys the product on the input it was built for. A false negative is
   partially caught downstream by D8, where a provider's own refusal renders as
   an empty chair. Play is the default and the classifier has to argue its way
   out of it.
2. **Register is judged from how it is said, not what it is about.** The
   classifier prompt is few-shot on pairs that share a topic and differ in
   register — that contrast is the only thing that teaches the distinction.
   Same structured-output treatment as the ducks (D7), same enum-not-freeform
   discipline as D3.

`crisis` is the only register that stops the run, and it is deliberately narrow.

**Demo mode** (D17) has no model to call. It ships a small local heuristic that
fails toward `play`, since no real model sees the input and the fake verdicts
are seeded text — but a person in distress can still be on the other side of
the screen, so the crisis path stays reachable.

### D21 — Run history is browsable
`/history` lists past runs with situation, council score, roster size and
whether the council split; opening one restores the full verdict set. The rows
already exist per D15, so this is one route and one template — and it gives the
repository layer real queries (filter, paginate, order) instead of a lone
`list()`, which is what makes the abstraction defensible rather than decorative.

Identical `situation + action + roster + model` returns the stored run instead
of re-calling, so history doubles as the cache.

---

### D22 — The gate runs before the council, never alongside it
Considered and rejected: firing the classifier concurrently with the fan-out
and discarding the duck results if the gate returns `crisis`. It saves ~0.5s
per run and it is wrong.

D9 streams each verdict to the page as it lands, so a fast duck can beat the
gate:

    0.4s  witch duck lands   -> already rendered on screen
    0.5s  gate returns crisis -> too late to stop it

On the single input where the gate matters most, a person in distress would get
a duck verdict flashed at them and then retracted. Streaming is not revocable.

Even setting the race aside, the concurrent version means the ducks *did* run
on a crisis input — a request went to a provider and sits in logs — and the
system merely hid the output. Not doing it is different from doing it quietly.

If the added latency becomes a problem, the fix is a cheaper and faster
classifier model, not overlapping the check with the thing it gates.

### D23 — Presets are user-created, with one shipped default
A preset is a name plus a set of duck ids — full create/edit/delete, same as
user ducks (D14). One default preset exists on first run so the app is usable
before the user has built anything, and so the roster UI has something to
demonstrate on an empty install.

Presets reference duck ids, so deleting a user duck has to be handled: the
preset keeps working with its remaining ducks rather than breaking. A preset
that ends up empty falls back to the shipped default, which satisfies D14's
"never an empty council" guard.

---

### D24 — Visual theme: The Green Bench
Chosen from four explorations (kept in `docs/theme/`). Courthouse institutional:
felt green, brass, cream parchment, with the duck palette carried in the score
colours (orange at reckless, brass through the middle, sage at clearly right).

The reasoning that decided it: **the funniest verdicts land hardest against a
straight face.** A brutalist or 70s treatment competes with the ducks for
attention; a dignified one lets them be the joke. It also holds tone on D20's
`weighty` register, where a sunburst arch would have read badly.

Rejected: *The Docket* (brutalist filing), *The Groovy Tribunal* (70s funk),
*Night Court* (dark brutalist).

Key elements now built: a timber quest board with a carved frame and brass
corner bolts; each verdict a parchment notice with deckled edges, nailed by a
brass stud, hung slightly crooked; scores as brass medallions; the council
finding on an engraved scale bar banded across the five verdict levels.

**Typographic floor: 11px.** Four rounds of review all landed on the same
defect — 9px labels are decorative, not readable. Nothing below 11px ships.

### D25 — Asking and hearing happen on one page
Submitting does not navigate. The filing form collapses into the read-only case
caption and the board fills beneath it.

The deciding reason was **audio**, not aesthetics. Browsers refuse `play()`
until a document has received a user gesture. On a redirect, `/council/{id}`
would load with no interaction, verdicts would start arriving on their own, and
the first stamp sound would be rejected — silently, and only in production-like
conditions. Keeping the submit click and the stamps in the same document means
that click is the gesture that unlocks audio.

`/council/{id}` still exists as a read-only route so History (D21) has somewhere
to link. It renders the finished board with no animation and no sound, which is
correct — you are re-reading a verdict, not watching one happen.

### D26 — Verdicts are stamped onto the board, and the board never moves
The board renders at full size before any verdict arrives: the server knows how
many ducks are sitting, so it emits that many empty seats and the grid height is
fixed at first paint. Each notice then slams into its reserved seat.

To make "never moves" literally true, seats carry a `min-height` and verdict
text is line-clamped. Otherwise a long-winded duck resizes its row and shifts
every notice beside it — which is exactly the reflow the fixed board exists to
prevent.

The animation is an impact, not a fade: the notice drops in over-scale, lands
just under 1.0, and settles, with a 2px jolt on the board itself at the moment
of contact. Sound fires at impact (~230ms), not at animation start.

Sound uses 3-4 stamp variants chosen at random with a slight playback-rate
detune per duck, so thirteen stamps do not sound mechanical; the council finding
gets a single gavel. A brass mute toggle persists in `localStorage`, and
`prefers-reduced-motion` reduces the slam to a fade. Audio never gates content:
if playback fails, the verdict still lands.

### D27 — Navigation sits below the filing block; provider choice is its own page
The two text fields are the product, so they lead and navigation follows them
rather than competing from a masthead.

Provider and model selection gets a dedicated page rather than a settings
sub-section, because for this app it is a primary decision, not a preference:
choosing local Claude versus a key-based provider versus a local model changes
what the council costs, how fast it is, and whether it works offline at all.
Routes stay plainly named for anyone reading the code; the theme lives in the
labels.

### D28 — Teardown scope (executed)
v1 is removed rather than left alongside v2: the first thing anyone opening
this repo sees should not be a dead CrewAI app. Git history retains all of it.

```
REMOVE                                KEEP
  client/                    506K       docs/                    7.4M
  duck_council/**            1.8M       13 duck portraits
    except static/images/                 -> app/static/images/
  docker-compose.yml                    README.md  (rewritten later)
  duck_council/dockerfile               .git
  client/Dockerfile
```

### D29 — Ducks carry a short `epithet` for their card
D5 and D14 gave a duck three judgement fields: `voice`, `weighs`, `blind_spot`.
Written well enough to steer a model, those are full sentences — far too long for
the card label the theme uses ("Weighs liability · blind to joy"). Deriving a
label by truncating them would be fragile, so the card text is its own field,
capped at 48 characters. User-created ducks (D14) supply one too.

### D30 — "Split" means at least a third of the voting ducks on each side
D16 promised to surface a split council without defining one. The rule:
`3 × min(in favour, against) ≥ ducks that voted`, with scores above 50 in favour,
below 50 against, and exactly 50 undecided. A 3–4 council is split; 2–5 is not.
It is an integer comparison, so there is no floating-point edge at exactly a
third, and a single duck can never be split.

### D17 amendment — the demo provider and the test fake are separate
D17 said the demo provider would double as the test fake. In practice tests need
things a demo must never do: refuse on cue, hang past a timeout, fail with a
chosen error. So tests use a small scripted provider (`tests/fakes.py`) and the
demo provider gets its own tests for determinism and character. Both satisfy the
same `Provider` Protocol, which is the part of D17 that mattered.

### D31 — Providers follow the proposal_copilot model; local Claude is Claude Code
Adopted from the owner's other project (`Upwork_mcp/proposal_copilot`,
`src/lib/llm/`): one interface, a few adapter *kinds*, and known vendors kept as
**data** (`app/providers/presets.py`) rather than code.

| Kind | Covers | How the verdict shape is enforced |
|---|---|---|
| `claude_code` | Claude Code already installed on this PC | `--json-schema`; the answer arrives pre-validated in `structured_output` |
| `anthropic` | Anthropic API with a key | SDK `messages.parse(output_format=Verdict)` |
| `openai_compatible` | OpenAI, OpenRouter, Gemini, DeepSeek, Groq, Ollama, LM Studio | asks for a JSON schema; falls back to described format if the vendor rejects it |
| `command` | any program that reads a prompt and prints a verdict | described format |
| `demo` | nothing installed | scripted |

Every provider has a tiny `check_connection()` so a bad key or missing program
fails in seconds with a sentence a person can act on.

**This supersedes D11.** "Local Claude" meant Claude Code on the subscription
the owner is already signed into: no API key, no per-call bill. D11 rejected the
Claude Code harness as too heavy to suppress; in practice five flags reduce it to
a single structured answer. The Agent SDK is still not used.

Verified against Claude Code 2.1.276 on this machine, and each one tested:

- **Never `--bare`.** It looks like the tidy choice, but it makes Claude Code
  accept only `ANTHROPIC_API_KEY` and never read the subscription login.
- **`--tools ""` and `--restricted`**: a verdict needs no tools, no settings files.
- **Empty temporary working folder per call.** From the project folder, Claude
  Code would read our CLAUDE.md into every duck's context.
- **The case goes as the argument directly after `-p`, not on stdin.** Claude Code
  abandons stdin after 3 seconds, and six copies starting together tripped that
  even with the data already waiting (2 of 4 ducks failed). No shell is involved
  and `claude.exe` is a real executable, so an argument is exactly one argument;
  tests push quotes, backslashes, newlines and flag-lookalikes through to prove it.
  Directly after `-p` so a list-taking option like `--tools` can never swallow it.
  Stdin is closed so nothing waits for it.
- **The persona goes in a file** (`--system-prompt-file`).
- **A timed-out duck kills its process.** Cancelling only the Python side left
  `claude.exe` running and using the subscription; a test proves the kill.

Measured: ~17s per duck, of which the model is 4-7s; the rest is Claude Code
starting. Ducks run side by side (concurrency 6), so a six-duck hearing took 30s.

### D32 — Each provider sets its own timeout and concurrency
One global timeout was wrong for most providers: Claude Code needs ~17s per duck,
an HTTP API ~3s, and a local GPU may want one duck at a time. The `Provider`
Protocol now carries `timeout` and `max_concurrency`; the council uses them
unless told otherwise.

### D33 — The CLI reads API keys only from `DUCK_COUNCIL_API_KEY`
Never from a flag: command-line flags are saved in shell history, so a key typed
there outlives the session. Keys are held as `SecretStr` inside the app, so they
cannot leak through a log line or a printed config. Where keys are *stored* for
the web UI is unchanged: the OS keyring (D12, D18). proposal_copilot keeps keys
in its SQLite database; we deliberately do not.

### D7 amendment — two routes read verdicts from text
OpenAI-compatible vendors that reject schema-constrained output, and custom
commands, can only return text. For those, the first JSON object in the reply is
extracted and validated against `Verdict` in full; anything malformed is an empty
chair, never a guess. The schema-enforced routes (Claude Code, Anthropic API,
schema-capable vendors) are unchanged.

### D34 — A hearing runs in the background, not inside the browser's connection
Browsers reconnect a dropped event stream on their own. If the hearing lived in
the connection, every reconnect would convene the council again and pay for every
duck twice. So filing a case starts a background task that records each seat as it
lands; the stream only reads what has been recorded, and a reconnect replays it
(tested: a second connection makes zero new provider calls).

Trade-off accepted: closing the tab does not stop a hearing mid-way. It finishes,
and the result is kept for the Register (D21). Background tasks are held in a set
on the app, because asyncio keeps only a weak reference to a task and could
otherwise collect a hearing halfway through.

### D35 — Every asset is served locally
htmx, its SSE extension, both fonts and the stamp sound live in `app/static/`, with
version, source, license and SHA-256 recorded in `app/static/README.md`. The app has
to work fully offline (Ollama, D31), and loading fonts from Google would tell a
third party every time the page opened. A test fails if a page ever references an
external URL.

### D36 — The web app enforces D12 with three layers
Host header must be `127.0.0.1` or `localhost` (defeats DNS rebinding); any
state-changing request must carry an Origin equal to the app's own (defeats other
websites posting to localhost, including other local dev servers on another port);
and every response carries a Content-Security-Policy allowing scripts only from this
server, so text from a user or a model can never run even if escaping failed.
Templates escape by default on top of that. All three are tested.

Decisions from here on are marked **(owner's call)** where the owner chose between
options, so the log shows who decided what.

### D15 amendment — Real SQLite only, no repository interface (owner's call)
D15 planned a repository interface with a SQLite version for the app and an
in-memory version for tests. Built instead: one `Bench` class on SQLite, and the
tests run it against a real database in a temporary file.

Why: a fake store would have to re-implement every rule (the last-duck guard, the
preset fallback) and could pass while the SQL is wrong; SQLite in a temp file is
fast enough to test directly. An interface gets added when a second storage
backend actually exists, not before. Routes still receive the bench through
dependency injection (D13); that does not need an interface.

### D23 amendment — The default preset is "The Quackorum" (owner's call)
A fresh install seats five ducks, not thirteen: the lawyer, the doctor, Sir Bill
Quackington, Quack the Ripper and Flare. Chosen to disagree: two cautious (liability,
harm) and three bold (upside, escalation, freedom), each on a different axis. Five
can never tie, and on Claude Code five ducks run in one wave (~17s) where thirteen
took ~50s. The name puns on quorum, the minimum members needed to decide.

The line-up is defined in `app/ducks.py` and synced into the database on start, like
the ducks themselves; it cannot be deleted. There is deliberately no second
"Full Council" preset: users save their own line-ups.

### D37 — The database arrives with the Bench, not after it
The Bench saves who sits, user ducks and presets, so SQLite (planned for step 5)
came forward into step 4. Details accepted by the owner:

- The bench lives in the user's app-data folder (`%LOCALAPPDATA%\duck-council\council.db`
  on Windows), movable with `--data-dir` or `DUCK_COUNCIL_DATA`.
- Built-in ducks are refreshed from the code on every start (their text cannot
  drift), while the user's choice of who sits is kept.
- A newly commissioned duck sits straight away.
- Removing a user duck is permanent, after a confirmation.
- The bench's rules are enforced inside single SQL statements, so two browser tabs
  cannot both remove the last sitting duck.
- The schema is versioned with `PRAGMA user_version` and an ordered migration list.
- Work happens on the `v2` branch; merging to `main` is the owner's call.

### D38 — Chambers keeps a saved list of providers; no per-duck override (owner's call)
Following proposal_copilot: providers are set up once (Claude Code, an Anthropic
key, Ollama...), each with its own connection check, and one is the default that
hearings use. Switching is a click, not re-entering settings.

Per-duck provider override (D19) is dropped: one provider for the whole council.
Simpler to use and to explain, and it removes a picker from every duck.

### D39 — How Chambers behaves (owner's calls)
Chambers (`/providers`) is the page where the AI is chosen. The name stayed: in a
courthouse, chambers is the judge's office behind the courtroom.

- **The web app no longer takes `--provider`.** Chambers is the one place the AI
  is chosen. The terminal tool keeps its own `--provider` for quick hearings.
- **A fresh install uses the demo**, and if Claude Code is found on this computer,
  Chambers offers it in one click. Nothing is ever used without being chosen.
- **A provider that fails its test is saved anyway**, marked failing with the reason,
  and cannot become the default until it passes. Useful when Ollama is simply off.
- **The model is typed**, pre-filled from the preset, so any vendor and any new
  model works without the app needing to know its catalogue.
- **Custom commands stay terminal-only.** A web form that makes the server run a
  program you name is the one field an attacker would most want; the safest version
  of that field is the one that does not exist.

Built to match, each covered by a test:

- Adding or amending a provider tests it at once; amending clears the old result,
  since new settings make it meaningless.
- Keys live in the OS credential store (D12) and never in SQLite: a test reads the
  database files byte by byte after saving one. They are never sent back to a page,
  not even into a form redisplayed after an error; the person types it again.
- `KeyStore` is an interface because it has two real implementations: the OS store,
  and an in-memory one so tests never write into the owner's credential store. (The
  same rule as D15's amendment: an interface when there is a second implementation.)
- At most one default provider, enforced by a partial unique index in the database.
- Changing the default takes effect on the next hearing, without a restart.
- The providers table arrived as migration 2; migration 1 was left untouched.

### D40 — Clipped text is read by lifting the notice off the board (owner's call)
Notices have a fixed height so the board never moves (D26), which clips long
verdicts. Growing the card to show more would push every row below it. Instead,
"Read more" lifts a copy of the notice off the board: it grows and glides to the
middle of the screen with the full text, and "Put it back", a click outside it, or
Esc animates it back to its place. Its spot on the board stays empty meanwhile.

- "Read more" appears only on notices whose text is actually clipped; the page
  measures each one, again after fonts load and when the window is resized.
- The lifted verdict also shows what the duck noticed before it scored (the model's
  `read`). A lifted Bench notice adds the duck's voice, which the card omits.
- Bench notices get the same treatment (owner's call).
- The motion is FLIP: measure the notice (First) and its enlarged copy (Last),
  transform the copy onto the original (Invert), animate the transform away (Play).
  Only transforms move, so it stays smooth. Reduced-motion users get no travel.
- It is a native `<dialog>`, so focus, Esc and screen readers work without extra code.
  The copy drops its buttons and forms, so nothing can be submitted twice, and it is
  never `stamped`, so lifting a verdict does not ring the stamp again.

---

## Next session starts here

**State:** step 4 is done. The Filing Desk, the Bench and Chambers all work, on
SQLite, with keys in the OS credential store. 150 tests pass; ruff and
`mypy --strict` clean. Verified against a real server: first run offers Claude
Code, one click tests it (13s) and makes it the default.

Run it: `uv run --system-certs duck-council-web`, then choose the AI in Chambers.
**Visual check in a browser is pending: the owner tests by hand.**

**Build order:**

1. ~~Engine + CLI.~~ Done.
2. Tune the bands. Deferred until after the UI. Known: verdict lines run 3-5
   sentences (clamped to 5 lines on the board); every duck adds a safety caveat,
   which may pull the chaos ducks toward the middle.
3. ~~Web app: Filing Desk and live board.~~ Done.
4. ~~The Bench and Chambers.~~ Done.
5. The Register (history of hearings). Hearings are still kept in memory only.

**Not yet built from the frozen decisions:** the safety gate (D20/D22); Docker
(D17, D18's env-var key store); CI (D17).

**Open issue:** an intermittent pytest warning seen in a few early runs; not
reproduced in 30+ runs since. Suspected: a test ending while a background hearing
is still running.

**Untested against the live service:** the Anthropic API and OpenAI-compatible
adapters (no key used yet). Claude Code is tested for real, including from Chambers.

**Environment gotchas:** pass `--system-certs` to every `uv` command (something
intercepts TLS here). While `duck-council-web` is running, also pass `--no-sync`:
Windows locks the running program and uv cannot reinstall it. The uv-installed
Python cannot do HTTPS downloads here (`OPENSSL_Applink`); Windows'
`C:\Windows\System32\curl.exe` can. Python 3.12 is pinned in `.python-version`.

