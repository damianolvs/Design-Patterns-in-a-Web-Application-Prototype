# Justification — Technology and Design Pattern Choices

**BIS Store · Part B of the Design Patterns in a Web Application Prototype lab**

Damian Olivas · 6522150042 · Group IT92 · 9th term
Ingeniería en Tecnologías de la Información — Universidad Tecnológica de Chihuahua
Full-Stack Web Development · Instructor: Ramses Requena

---

## The problem

BIS Store is a small online shop for computer peripherals: browse a catalogue,
build a cart, pick how the order gets delivered, check out. I picked it because
of one detail — **shipping is not a single formula**. Standard delivery charges
a base fee plus a per-kilo rate and becomes free once the order is big enough;
express costs more and is never free; store pickup is free but refuses carts too
heavy to carry out. Three options, three genuinely different pricing rules, and
a business that will keep adding more. That gives me a real reason to reach for
a pattern instead of inventing one, which is what section 2 of the guide asks
for.

## Why these three technologies

**Django** is the backend framework I use most, and it ships with MVT built in.
I didn't have to bolt an architecture onto the framework, just respect the one
already there. Routing, the template engine and CSRF protection came free, so
the effort went into the patterns instead of the plumbing.

**Tailwind CSS** because part of the grade is that the prototype actually works
end to end, so it has to look like a store rather than an unstyled form. Styling
lives in the templates, and I compiled it ahead of time into a single 13 KB file
so the project needs no Node install and no internet connection.

**htmx** was the choice I thought about longest. React was the obvious move, but
it would pull the presentation layer out of Django templates and into
components, blurring exactly the MVT boundaries I am supposed to be
demonstrating. htmx keeps rendering on the server and still updates the total
without a page reload. Every control is a real HTML form with an `hx-post`
attribute layered on top, so the prototype still works with JavaScript disabled.

## Why these three patterns

Following step 3 of section 8.1, I wrote the plan before writing any code:

> I'll use MVT to separate what the data is from who handles the request from
> what gets rendered; Singleton for the in-memory store state every request has
> to share, since there is no database; and Strategy for the shipping cost,
> because there are three genuinely different pricing formulas and there will be
> more later.

That list did not change during implementation, which I take as a sign the
patterns fit the problem rather than being retrofitted onto it. I deliberately
took one from each family the guide describes in section 2.

### MVT — architectural

Django's Model–View–Template is the instructor's MVC under different names: the
Template is the presentation layer and the View plays the Controller's role. It
was worth demonstrating rather than assuming because Django lets you violate it
— nothing stops you computing a total inside a view. So I enforced it:
`store/models.py` imports nothing from Django at all, and a test parses that
file's AST and fails if a single `django.*` import ever appears. The payoff is
that swapping the hardcoded catalogue for a real database would not change one
line of any view or template, which is the same argument the guide makes in
section 7.3.3.

### Singleton — creational

The lab allows hardcoded data with no database, and that requirement is what
creates the need: the catalogue, cart and activity log live in memory, and every
request has to see the same objects or the cart resets on every click. I made
the guarantee explicit instead of leaning on Python's module caching — the
constructor raises if a second instance is attempted, and `get_instance()` uses
double-checked locking so concurrent requests cannot race into creating two.

The trade-off is real and worth stating: this singleton is per process, so four
Gunicorn workers would mean four independent carts, and a shared cart is wrong
for a multi-user shop anyway. That is the hidden global state the guide flags in
section 4. In production the cart would live in a session and the Singleton
would hold something genuinely process-wide — a connection pool or a parsed
configuration.

### Strategy — behavioural

This is the pattern the problem was chosen for. The alternative is a chain of
if-statements in the checkout view, which puts pricing rules inside an HTTP
handler, grows the view every time the business adds an option, and makes it
impossible to test one rule without going through a request. Instead each
algorithm is its own class behind a shared interface, and `Checkout` just calls
`calculate()` without ever learning which class answered.

Two things convinced me it was a fit rather than a pattern I was forcing in. The
shipping panel prices the cart with every strategy at once using a single loop,
which only works because they share an interface — that loop will keep working
for options that do not exist yet. And `StorePickup` needed to refuse heavy
carts, which became an `is_available()` hook on the interface: the view greys
the option out and shows the reason without knowing what the rule is. Adding a
fourth delivery method is one new class and one line in the registry.

## Why not Factory

Factory was the natural fourth candidate and I left it out on purpose. Nothing
here has construction complicated enough to centralise — the strategies are
stateless and created once at import time. A `ShippingStrategyFactory` would
have been a class that exists to have a pattern's name on it, which is exactly
what section 8.2 says is not accepted.

## How the three fit together

They stack rather than compete. MVT organises the application into layers;
Singleton lives inside the Model layer and owns the data those layers share;
Strategy lives there too, with `Checkout` as its context, keeping the pricing
rules out of the View. The View stayed thin as a result — the longest view
function in the project is sixteen lines, and every one of them is either input
validation or delegation. That is the clearest evidence I have that the patterns
are doing real work: the code that would have grown ugly never grew.
