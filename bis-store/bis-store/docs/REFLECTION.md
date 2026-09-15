# Section 11 — Closing Reflection

**Design Patterns in a Web Application Prototype**

Damian Olivas · 6522150042 · Group IT92 · 9th term
Ingeniería en Tecnologías de la Información — Universidad Tecnológica de Chihuahua

---

### Which of the three patterns did you find most intuitive, and which was hardest to justify? Why?

**Most intuitive: Strategy.** The problem states itself. Three delivery
methods with three different pricing formulas, and the question "where does
this code go?" answers itself the moment you write the second `elif`. I didn't
have to convince myself it was needed — the alternative was visibly worse.

**Hardest to justify: Singleton**, and not because it was hard to implement.
It was hard because in Python it is almost redundant. The interpreter caches
modules, so a module-level object already behaves like a singleton without any
of the machinery. I spent a while wondering whether I was writing ceremony
around something the language does for free.

What settled it for me was the difference between *behaving like* one and
*guaranteeing* it. Without the guard in `__init__`, calling `StoreState()`
hands you a second object that looks fine and silently breaks the cart. With
it, you get a `RuntimeError` and find out immediately. The pattern moves the
guarantee from "nobody will do that" into the class itself.

There is a second reason Singleton was hard to justify honestly: the thing I
used it for — a shopping cart — is the wrong thing to make global in a real
application. I ended up justifying it as correct *for this prototype* while
being explicit that it would be wrong in production. That felt more honest
than pretending the pattern had no downside.

---

### Think of a previous personal or school project. Would it have improved with one of these patterns? Which one, and why?

Yes — LineSimulator, a project I built for simulating medium-voltage
distribution lines on a map.

It calculates voltage drop, and the calculation depends on the conductor type
and the line configuration. I wrote that as a chain of conditionals inside the
calculation service, and every time I added a conductor the function got
longer and harder to follow. By the fourth or fifth branch I was afraid to
touch it, because the branches shared local variables and I couldn't tell
which ones mattered to which case.

That is textbook **Strategy**, and I didn't see it at the time. Each conductor
type should have been its own class behind a common interface, with the
service just calling `calculate()`. The tell I missed was that I could not
test one conductor's formula without running the entire service.

A secondary one: the CFE standards catalogue that project loads is read once
and never changes, and I was reloading it in several places. That is a real
**Singleton** — a parsed configuration, genuinely process-wide, which is a
much better fit for the pattern than the cart I used it for here.

---

### At what point could applying a pattern be counterproductive for a small project?

When the pattern solves a problem you don't have yet.

The concrete test I now use: if adding the pattern means writing an interface
and a class for something that will only ever have one implementation, it is
costing you indirection and buying you nothing. A `PaymentStrategy` interface
with exactly one `CashPayment` behind it is three files where one function
would do, and the next person has to read all three to find out that nothing
varies.

I ran into this directly on this assignment. Factory was the obvious fourth
pattern and I left it out, because my shipping strategies are stateless and
instantiated once at import — there is no construction complexity to
centralise. A `ShippingStrategyFactory` would have been a class whose only job
was to have a pattern's name on it.

The other counterproductive case is Singleton specifically, which the guide
warns about in its comparison table: it hides global state. In a small project
that starts as convenience and turns into two parts of the code disagreeing
about what the state is, with no import trail to follow when you debug it.

The version of this I believe: a pattern is worth its cost when the code would
otherwise get *worse as it grows*. If the thing isn't going to grow, the
if-statement wins.

---

### If you had to explain the difference between Factory and MVC to a classmate who has never programmed, what analogy would you use?

I'd use a restaurant, because it has both and they sit in different places.

**Factory is the kitchen window.** You order "a pizza" and a pizza comes out.
You never walk into the kitchen, you don't know which cook made it or which
oven it came from, and you don't care. If the restaurant adds a wood-fired
oven tomorrow, your order doesn't change — you still say "a pizza". Factory is
about *who makes the thing* and hiding that from whoever ordered it.

**MVC is how the whole restaurant is organised.** The kitchen owns the food,
the waiter takes your order and decides what to do with it, and the menu and
plating are what you actually see. Nobody does someone else's job: the waiter
doesn't cook, the kitchen doesn't talk to customers, the menu doesn't make
decisions. If you fire the waiter and hire a new one, the kitchen keeps
working — which is the whole point.

So: Factory is one station inside the restaurant. MVC is the floor plan. You
can have a kitchen window in a badly organised restaurant, and you can have a
well-organised restaurant with no kitchen window at all. They answer different
questions — "who builds this?" versus "who is responsible for what?"

If they wanted one sentence: Factory decides *which thing gets made*, MVC
decides *who is allowed to do what*.
