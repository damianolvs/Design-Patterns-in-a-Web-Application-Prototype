# Demo Script — 5 to 7 minutes

**BIS Store · Design Patterns in a Web Application Prototype**
Damian Olivas · Group IT92

---

## Before you start

Have these open and ready, in this order:

1. **Browser** at `http://127.0.0.1:8000/`, freshly reloaded (click **Rebuild
   the singleton** once so the log is clean)
2. **Editor** with four tabs already open, in this order:
   - `store/patterns/store_state.py`
   - `store/patterns/shipping.py`
   - `store/models.py`
   - `store/views.py`
3. **Second terminal** ready to run `python manage.py test`

Turn the editor font up. Nobody can read 11px from the back of a classroom.

---

## 0:00 — 0:40 · What it is and what it's built with

> "This is BIS Store, a checkout prototype for a computer peripherals shop.
> Built with Django, Tailwind and htmx. There's no database — the lab allowed
> hardcoded data, and that turned out to matter, because it's what forces one
> of my three patterns.
>
> Three patterns, one from each family the guide describes: MVT is the
> architectural one, Singleton is creational, Strategy is behavioural."

**Do:** point at the three tags in the header bar.

---

## 0:40 — 1:40 · Show it working first

> "Quickly, so you know it actually runs."

**Do, in this order:**
- Add a **USB-C hub** — point out the stock going from 20 to 19
- Add a **keyboard**, bump the quantity with `+`
- Point at the total updating without a page reload

> "No page reloads — that's htmx. Every one of these is a normal HTML form
> with an `hx-post` attribute on top, so it still works with JavaScript
> switched off. I tested that."

**Don't** spend more than a minute here. The patterns are the grade.

---

## 1:40 — 3:00 · Strategy (the one with the best visual)

**Do:** click between **Standard**, **Express** and **Store pickup**. Let the
total change three times.

> "Three delivery methods, three completely different pricing rules. Standard
> is a base fee plus per-kilo and goes free over $2,500. Express costs more
> and is never free. Pickup is free but refuses heavy carts.
>
> The obvious way to write this is a chain of if-statements in the checkout.
> That puts pricing rules inside an HTTP handler, and the handler grows every
> time the business adds an option."

**Do:** switch to `store/patterns/shipping.py`. Scroll so **line 47** is
visible.

> "So instead: `ShippingStrategy` at line 47 is the interface. One abstract
> method, `calculate`, at line 55. Then three concrete classes — Standard at
> 67, Express at 85, Pickup at 100 — each implementing it their own way."

**Do:** switch to `store/models.py`, go to **line 124**.

> "And here's the whole point. Line 124. The Checkout asks
> `self.strategy.calculate(...)` and has no idea which class answers. That
> delegation is what makes this Strategy instead of an if-chain."

**Do:** switch to `store/views.py`, **line 109**.

> "Switching at runtime is one assignment. Line 109. No pricing logic anywhere
> near the request."

**Do:** back to the browser. Add **three monitors**. Store pickup greys out.

> "And `is_available()` is on the interface too, so Pickup can refuse a cart
> over 8 kg — and the view greys it out and shows the reason without ever
> knowing what the rule is. Adding drone delivery tomorrow is one new class
> and one line in the registry."

---

## 3:00 — 4:15 · Singleton

**Do:** scroll to the **Singleton inspector** panel.

> "There's no database, so the catalogue, the cart and this log all live in
> memory. Every Django request has to reach the same object or the cart resets
> on every click."

**Do:** click **Add to cart** two or three times. Point at the panel.

> "`instance_id` never changes. The `get_instance()` counter keeps climbing.
> Same object, accumulating state — same thing the instructor's example shows
> with `connectionId` and `totalQueries`."

**Do:** switch to `store/patterns/store_state.py`, **lines 58 through 95**.

> "Line 58 is the private field holding the only instance. Lines 65 to 69 are
> the guard — `__init__` raises if you ever try to build a second one. Python
> has no `private` keyword, so the guard goes in the constructor body; it's
> the same idea as the private constructor in the TypeScript example.
>
> Line 93 is the only line in the whole project that creates the object, and
> it's wrapped in double-checked locking so two concurrent requests can't race
> into making two."

**Do:** back to the browser. Click **Try StoreState() directly**. The
RuntimeError appears.

> "That button calls the constructor on purpose, just to show it's actually
> enforced and not just documented."

---

## 4:15 — 5:15 · MVT

**Do:** switch to `store/models.py`, scroll to the top so the imports show.

> "Third pattern is the architecture itself. Django calls it MVT — Model,
> View, Template — but the View plays the Controller's role, so it maps
> directly onto the MVC example.
>
> Model is this file. Look at the imports: there's nothing from Django in
> here. No request, no HttpResponse, no template name. Just dataclasses and
> business rules."

**Do:** switch to `store/views.py`, scroll to `confirm_order` at **line 116**.

> "The View layer is the only place that knows HTTP exists. This is the
> longest view in the project — sixteen lines, and every one of them is either
> validating input or delegating. No calculation."

**Do:** switch to `store/templates/store/partials/app.html`, scroll to the
totals block.

> "And the Template just prints `checkout.total`. It doesn't add anything up —
> that number was computed in the Model."

**Do:** run `python manage.py test` in the second terminal.

> "Twenty tests. One of them parses `models.py` into an AST and fails if a
> single Django import ever shows up. So the layer separation isn't something
> I'm claiming — it's checked."

---

## 5:15 — 5:45 · Close

> "So: MVT organises the app into layers. Singleton lives in the Model layer
> and owns the shared state. Strategy lives in the Model layer too and keeps
> the pricing rules out of the View. Three patterns, three different kinds of
> problem.
>
> The clearest evidence they're doing real work is that the code that would
> have grown ugly never grew — the longest view in the project is sixteen
> lines."

That leaves you roughly a minute of slack before the 7:00 limit. Use it if a
click is slow, or stop and take questions.

---

## Likely follow-up questions

**"Why didn't you use Factory?"**
> Nothing here has complicated construction. The strategies are stateless and
> built once at import. A `ShippingStrategyFactory` would have been a class
> with a pattern's name on it and no actual job, which section 8.2 of the
> guide says doesn't count. I'd rather have three patterns that earn their
> place.

**"Isn't a Python module already a singleton?"**
> Yes — the interpreter caches modules, so a module-level object behaves like
> one by accident. I implemented it explicitly so the guarantee lives in the
> class instead of depending on import mechanics. Without the guard,
> `StoreState()` quietly hands you a second, broken copy. With it, you get a
> `RuntimeError`.

**"What breaks if you deploy this?"**
> The singleton is per process. Under Gunicorn with four workers you'd get
> four independent carts, and a shared cart is wrong for a multi-user shop
> anyway. That's the hidden-global-state risk the guide flags in section 4.
> In production the cart goes in a session, and the Singleton holds something
> genuinely process-wide — a connection pool or a parsed config.

**"How would you add a fourth shipping method?"**
> One new class in `shipping.py` implementing `ShippingStrategy`, and one line
> in the `SHIPPING_STRATEGIES` registry. Nothing in the views, templates or
> models changes.

**"Why htmx and not React?"**
> React would have moved the presentation layer out of Django templates into
> components, which blurs exactly the MVT boundaries I'm demonstrating. htmx
> keeps rendering on the server and still gives you partial updates.

**"What's the difference between Strategy and Factory?"**
> Factory decides *which object to build*. Strategy decides *which algorithm
> to run* on an object you already have. My shipping objects all exist from
> startup — nothing is being constructed — they're just being swapped.
