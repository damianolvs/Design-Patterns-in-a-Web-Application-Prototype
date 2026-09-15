# BIS Store — Design Patterns in a Web Application Prototype

**Part B deliverable — Laboratory Practice: Implementing Design Patterns in a Web Application Prototype**

Damian Olivas · 6522150042 · Group IT92 · 9th term
Ingeniería en Tecnologías de la Información — Universidad Tecnológica de Chihuahua
Instructor: Ramses Requena

---

## What this prototype does

BIS Store is a small computer-peripherals shop with a working checkout. You
can browse a catalogue, add and remove items, change quantities, pick a
shipping method, and place an order. Stock goes down as you add things and
comes back if you remove them.

The interesting part is that the shipping cost is not one formula — it depends
on which delivery method you choose, and each method prices the cart with its
own rules. That is the problem the design patterns are here to solve.

There is no database. All state lives in memory, which the lab explicitly
allows, and which is what makes the Singleton necessary rather than decorative.

---

## Technologies used

| Technology | Version | Role in the project |
|---|---|---|
| **Django** | 5.x / 6.x | Backend framework. Provides the MVT architecture, URL routing, template engine and CSRF protection. |
| **Tailwind CSS** | 4.x | Utility-first styling. Compiled ahead of time into `static/css/app.css`; no build step needed to run the project. |
| **htmx** | 2.0 | Sends the form posts over AJAX and swaps the updated fragment back into the page, so the whole checkout updates without a full reload and without writing any JavaScript. |

All three are technologies I already use. Django is my main backend framework,
Tailwind is what I use for styling, and htmx keeps the frontend interactive
without pulling in a JavaScript framework that would blur the MVT boundaries
this practice is about.

---

## Design patterns implemented

Three patterns, one from each family the lab guide describes in section 2:

| # | Pattern | Family | Where it lives |
|---|---|---|---|
| 1 | **MVT (Django's MVC)** | Architectural | `store/models.py`, `store/views.py`, `store/templates/` |
| 2 | **Singleton** | Creational | `store/patterns/store_state.py` |
| 3 | **Strategy** | Behavioural | `store/patterns/shipping.py` |

---

### 1. MVT — Model / View / Template (architectural)

Django calls its layers Model, View and Template. The mapping to the classic
MVC in the instructor's example is:

| Classic MVC | Django MVT | File in this project |
|---|---|---|
| Model | Model | `store/models.py` |
| View (presentation) | Template | `store/templates/store/` |
| Controller | View | `store/views.py` |

**Exact locations**

| Layer | File | Lines | What is there |
|---|---|---|---|
| Model | `store/models.py` | 47–59 | `Product` — the data shape |
| Model | `store/models.py` | 76–97 | `ShoppingCart` — subtotal, weight, item count |
| Model | `store/models.py` | 100–179 | `Checkout` — tax, totals, order building |
| View (controller) | `store/views.py` | 70–73 | `index()` — reads state, picks a template |
| View (controller) | `store/views.py` | 101–113 | `set_shipping()` — validates input, swaps the strategy |
| View (controller) | `store/views.py` | 116–132 | `confirm_order()` — validates, then delegates |
| View (controller) | `store/views.py` | 62–67 | `_respond()` — chooses full page vs. htmx fragment |
| Template | `store/templates/store/base.html` | whole file | Page shell |
| Template | `store/templates/store/partials/app.html` | whole file | The fragment htmx swaps |
| Routing | `store/urls.py` | 11–20 | URL → view map, no logic |

**How the separation is enforced, not just claimed**

`store/models.py` imports nothing from Django. That is verified automatically
by a test that parses the module's AST and asserts there are zero `django.*`
imports (`store/tests.py`, lines 111–125). The Model layer would work
unchanged from a CLI script or a unit test.

Templates never calculate anything. Every number they print (`checkout.total`,
`checkout.shipping_cost`, `quote.cost`) is a property computed in
`store/models.py`. The templates only choose how to display it.

Views never contain business rules. The longest one, `confirm_order()`, is 16
lines and every one of them is either input validation or delegation.

---

### 2. Singleton (creational)

**The problem.** The catalogue, the cart and the activity log live in memory.
Every HTTP request Django handles has to see the same objects — otherwise the
cart would reset on every click. Singleton guarantees one state object per
process and gives every module one controlled way to reach it.

**Exact locations**

| What | File | Line |
|---|---|---|
| The private class attribute holding the only instance | `store/patterns/store_state.py` | 58 |
| The lock used for thread safety | `store/patterns/store_state.py` | 59 |
| **The guard that makes a second instance impossible** | `store/patterns/store_state.py` | **65–69** |
| The single public access point, `get_instance()` | `store/patterns/store_state.py` | 87–95 |
| Double-checked locking | `store/patterns/store_state.py` | 90–93 |
| The one line that creates the instance, exactly once | `store/patterns/store_state.py` | **93** |
| Access counter (the proof for the demo) | `store/patterns/store_state.py` | 94 |
| `reset()` escape hatch used by the demo button | `store/patterns/store_state.py` | 97–106 |
| The hardcoded catalogue it holds | `store/patterns/store_state.py` | 178–235 |
| Every consumer calls `get_instance()`, never `StoreState()` | `store/views.py` | 72, 78, 85, 96, 104, 118, 142, 154 |

**Python note.** `__init__` raising when `_instance` already exists is the
Python equivalent of the private constructor in the instructor's TypeScript
example — Python has no `private` keyword, so the guard goes in the
constructor body.

**Proof in the running app.** The "Singleton inspector" panel at the bottom of
the page shows `instance_id`, the creation time, and how many times
`get_instance()` has been called. Click around: the id never changes and the
counter keeps climbing, which is evidence it is the same object accumulating
state. The **Try StoreState() directly** button calls the constructor on
purpose and prints the `RuntimeError` it raises.

**Known trade-off.** The singleton is per *process*. Under Gunicorn with four
workers you would get four independent carts. That is fine for a single-user
prototype and is exactly the "hidden global state" risk the lab guide flags in
section 4. In production the cart would go in a session or a database and the
Singleton would hold something genuinely process-wide instead, like a
connection pool or a parsed configuration.

---

### 3. Strategy (behavioural)

**The problem.** Three shipping methods, three completely different pricing
rules:

- **Standard** — $99 base + $18/kg, free once the subtotal passes $2,500
- **Express** — $219 base + $35/kg, never free
- **Store pickup** — free, but refuses carts over 8 kg

Writing that as `if method == "express": ... elif ...` inside the checkout view
would put pricing rules in an HTTP handler, grow the view every time the
business adds an option, and make it impossible to test one rule on its own.

**Exact locations**

| Role in the pattern | File | Lines |
|---|---|---|
| **Strategy interface** — `ShippingStrategy` (ABC) | `store/patterns/shipping.py` | 47–64 |
| The abstract method every algorithm must implement | `store/patterns/shipping.py` | 55–57 |
| Concrete strategy — `StandardShipping` | `store/patterns/shipping.py` | 67–82 |
| Concrete strategy — `ExpressShipping` | `store/patterns/shipping.py` | 85–97 |
| Concrete strategy — `StorePickup` | `store/patterns/shipping.py` | 100–117 |
| Registry of available strategies | `store/patterns/shipping.py` | 121–125 |
| Lookup with a safe default | `store/patterns/shipping.py` | 130–132 |
| **Context** — `Checkout` holds a strategy | `store/models.py` | 100–113 |
| **The delegation that makes this Strategy** | `store/models.py` | **124** |
| Polymorphic loop that prices the cart with every algorithm | `store/models.py` | 134–157 |
| The runtime swap — one assignment, no pricing logic | `store/views.py` | **109** |

**Why this is Strategy and not Factory.** `SHIPPING_STRATEGIES` is a lookup
table, not a factory — it does not decide *how* to build anything, it hands
back an already-configured object. What is being demonstrated is the
interchangeable algorithm behind a shared interface plus a context
(`Checkout`) that delegates to it. Line 124 of `store/models.py` is the whole
point: the checkout asks for a number and does not know which class answers.

**Proof in the running app.** Add a couple of products, then click between the
three shipping options. The total changes and nothing in the view, template or
model changed — only the strategy object behind the `Checkout`. Load up a heavy
cart (three monitors will do it) and Store pickup greys itself out through
`is_available()`, without the view knowing why.

**Extending it.** Adding "same-day drone delivery" means one new class in
`shipping.py` and one line in the registry. No view, template or model changes.

---

## Running the project

Requires **Python 3.10 or newer**. Nothing else — no Node, no database, no
network access at runtime.

```bash
# 1. Get into the project folder
cd bis-store

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install Django
pip install -r requirements.txt

# 4. Run it
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

You will **not** need to run `migrate` — `DATABASES` is empty on purpose
(`config/settings.py`, line 49) because the prototype has no database.

### Running the tests

```bash
python manage.py test
```

20 tests. They are not there for coverage — each one asserts the property that
makes a pattern that pattern:

- `SingletonTests` — `get_instance()` returns the identical object, direct
  instantiation raises, state survives between calls
- `StrategyTests` — the same cart produces three different prices, the
  strategy can be swapped at runtime, an unknown code falls back safely
- `ModelLayerTests` — the Model layer imports nothing from Django
- `ViewLayerTests` — the full add → choose shipping → order flow works, and an
  htmx request returns only the fragment

### Rebuilding the CSS (optional)

`static/css/app.css` is already compiled and committed, so you never need this
to run the project. If you edit a template and want to rebuild:

```bash
npx @tailwindcss/cli -i tailwind/input.css -o static/css/app.css --minify
```

---

## Project structure

```
bis-store/
├── manage.py
├── requirements.txt
├── README.md
├── config/
│   ├── settings.py          # DATABASES = {} — no database
│   ├── urls.py
│   ├── wsgi.py  ·  asgi.py
├── store/
│   ├── models.py            # MVT: the Model layer + Strategy context
│   ├── views.py             # MVT: the View layer (classic MVC's Controller)
│   ├── urls.py              # thin URL → view map
│   ├── apps.py
│   ├── tests.py             # 20 tests, one group per pattern
│   ├── patterns/
│   │   ├── store_state.py   # SINGLETON
│   │   └── shipping.py      # STRATEGY
│   └── templates/store/
│       ├── base.html        # MVT: the Template layer
│       ├── index.html
│       └── partials/
│           └── app.html     # the fragment htmx swaps
├── static/
│   ├── css/app.css          # compiled Tailwind (committed)
│   └── js/htmx.min.js       # vendored, works offline
├── tailwind/input.css       # Tailwind source, only needed to rebuild CSS
└── docs/
    ├── PART_A_ANALYSIS.md   # Part A: the three completed analysis tables
    ├── JUSTIFICATION.md     # the 1-2 page justification
    ├── DEMO_SCRIPT.md       # timed script for the 5-7 minute demo
    └── REFLECTION.md        # section 11 closing questions
```

---

## Things worth pointing out

**The forms work without JavaScript.** Every button is a real `<form method="post">`
with `hx-post` layered on top. With htmx loaded you get a partial swap; with
JavaScript disabled the same form does a normal POST and the view returns the
full page instead (`store/views.py`, lines 62–67). This was tested with
JavaScript turned off.

**No dead controls.** Every button in the UI does something. "Place order" is
disabled when the cart is empty or when the selected shipping method refuses
the cart, and the interface says why.

**Assets are vendored.** `htmx.min.js` and the compiled Tailwind CSS are both
in `static/`, so the prototype runs with no internet connection.
