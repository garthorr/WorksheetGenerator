"""Conceptual Physics: written-response questions with a model answer, and no calculation.

Every unit has two kinds of question:

- "What happens if…": proportional reasoning from one physics relation ("if the distance between
  two charges triples, the force becomes 1/9 as strong"). The answer follows from the relation's
  exponents, so it is right by construction, and ``facts["scaling"]`` lets the tests recheck it
  against their own copy of each relation.
- Explain / predict / compare questions about one idea (objects fall together, action and reaction,
  series and parallel bulbs), drawn from tables of settings, each with a model answer written for it.

The answer key shows a short model answer; there are no worked steps.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction as F

from .core import Ctx, Problem, topic, variant

REASON = "Explain your reasoning."


def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def W(question: str, answer: str, **facts) -> Problem:
    """A written-response problem: the question and a model answer, no worked steps."""
    return Problem(question, answer, facts={"written": True, **facts})


def C(id: str, category: str, name: str, description: str) -> None:
    topic(id, "physics", category, name, f"Written response: {description}", courses=["conceptual"], written=True)


def the(noun: str) -> str:
    """'a baseball' -> 'the baseball'."""
    return "the " + noun.split(" ", 1)[1] if noun.startswith(("a ", "an ")) else noun


# =================================================================== "What happens if…"

@dataclass
class V:
    """A quantity the result depends on: result ∝ sym**exp."""
    sym: str  # as written in the relation (LaTeX), e.g. "r"
    noun: str  # in the question: "the distance between them"
    short: str  # in the answer: "the distance"
    exp: F
    why_not: str = ""  # exp 0: why the result doesn't depend on it


@dataclass
class Law:
    key: str  # names the relation for the tests
    rule: str  # subject of the explanation: "The electric force"
    adj: str  # "strong": "becomes 1/9 as strong"
    vars: list[V]
    scenes: list[tuple[str, str]]  # (setting, what the result is called there)


CHANGE = {F(2): ("doubled", "doubling {x}"), F(3): ("tripled", "tripling {x}"), F(4): ("quadrupled", "quadrupling {x}"),
          F(9): ("made 9 times as large", "making {x} 9 times as large"), F(1, 2): ("cut in half", "halving {x}"),
          F(1, 3): ("reduced to one third", "reducing {x} to one third"),
          F(1, 4): ("reduced to one quarter", "reducing {x} to one quarter")}
# Changes to try, by how strongly the result depends on the quantity (|exponent|)
STEPS = {F(1): [F(2), F(3), F(1, 2), F(1, 3)], F(2): [F(2), F(3), F(1, 2), F(1, 3)], F(1, 2): [F(4), F(9), F(1, 4)]}
EASY = [F(2), F(3), F(1, 2)]  # level 1
BIG = [F(4), F(1, 3), F(1, 4)]  # level 2, in a unit whose relations have no squares or roots


def tex(f: F) -> str:
    return str(f.numerator) if f.denominator == 1 else rf"\frac{{{f.numerator}}}{{{f.denominator}}}"


def power(k: F, e: F) -> F:
    """k**e exactly (e may be ±1/2, with k a perfect square)."""
    if e.denominator == 1:
        return k ** int(e)
    root = F(math.isqrt(k.numerator), math.isqrt(k.denominator))
    assert root * root == k, k
    return root ** int(2 * e)


def becomes(f: F, adj: str) -> str:
    if f == 1:
        return "does not change"
    if f == 2:
        return "doubles"
    if f == 3:
        return "triples"
    if f.denominator == 1:
        return f"becomes {f.numerator} times as {adj}"
    if f == F(1, 2):
        return f"becomes half as {adj}"
    return f"becomes ${tex(f)}$ {'times ' if f > 1 else ''}as {adj}"


def as_much(f: F, adj: str) -> str:
    """A target: "twice as strong", "$\\frac{1}{4}$ as strong"."""
    if f == 2:
        return f"twice as {adj}"
    if f.denominator == 1:
        return f"{f.numerator} times as {adj}"
    if f == F(1, 2):
        return f"half as {adj}"
    return f"${tex(f)}$ as {adj}"


def depends(v: V) -> str:
    s = v.sym
    return {F(1): f"is proportional to ${s}$", F(-1): f"is inversely proportional to ${s}$",
            F(2): f"depends on ${s}^2$", F(-2): f"depends on $1/{s}^2$",
            F(1, 2): rf"depends on $\sqrt{{{s}}}$", F(-1, 2): rf"depends on $1/\sqrt{{{s}}}$"}[v.exp]


def effect(v: V, k: F) -> str:
    """What changing ``v`` by ``k`` does to the result: "divides it by $3^2 = 9$"."""
    m = k.numerator if k > 1 else k.denominator
    by = {F(1): f"{m}", F(2): f"${m}^2 = {m * m}$", F(1, 2): rf"$\sqrt{{{m}}} = {math.isqrt(m)}$"}[abs(v.exp)]
    return f"{'multiplies' if (k > 1) == (v.exp > 0) else 'divides'} it by {by}"


def doing(v: V, k: F) -> str:
    return CHANGE[k][1].format(x=v.short)


def _facts(law: Law, changes: list[tuple[V, F]], factor: F, form: str) -> dict:
    return {"scaling": {"law": law.key, "changes": {v.sym: k for v, k in changes}, "factor": factor, "form": form}}


def _one(ctx: Ctx, law: Law, v: V, k: F) -> Problem:
    scene, result = ctx.rng.choice(law.scenes)
    f = power(k, v.exp)
    if ctx.rng.random() < 0.5:
        q = f"{scene} If {v.noun} is {CHANGE[k][0]}, what happens to {result}? {REASON}"
    else:
        q = f"{scene} How does {result} change if {v.noun} is {CHANGE[k][0]}? {REASON}"
    a = f"{cap(result)} {becomes(f, law.adj)}. {law.rule} {depends(v)}, so {doing(v, k)} {effect(v, k)}."
    return W(q, a, **_facts(law, [(v, k)], f, "one"))


def _two(ctx: Ctx, law: Law) -> Problem:
    rng = ctx.rng
    live = [v for v in law.vars if v.exp]
    for _ in range(100):  # until the overall change is simple: a whole number or 1/n
        v1, v2 = rng.sample(live, 2)
        k1, k2 = rng.choice(STEPS[abs(v1.exp)]), rng.choice(STEPS[abs(v2.exp)])
        f1, f2 = power(k1, v1.exp), power(k2, v2.exp)
        f = f1 * f2
        if (f.numerator == 1 and f.denominator <= 16) or (f.denominator == 1 and f <= 16):
            break
    scene, result = rng.choice(law.scenes)
    d1, d2 = depends(v1), depends(v2)
    if d1.startswith("is ") and d2.startswith(d1.rsplit(" to ", 1)[0]):  # "is proportional to $I$ and to $V$"
        d2 = "to " + d2.rsplit(" to ", 1)[1]
    q = f"{scene} If {v1.noun} is {CHANGE[k1][0]} and {v2.noun} is {CHANGE[k2][0]}, what happens to {result}? {REASON}"
    a = (f"{cap(result)} {becomes(f, law.adj)}. {law.rule} {d1} and {d2}: {doing(v1, k1)} "
         f"{effect(v1, k1)}, and {doing(v2, k2)} {effect(v2, k2)}, so overall it changes by a factor of "
         f"${tex(f1)} \\times {tex(f2)} = {tex(f)}$.")
    return W(q, a, **_facts(law, [(v1, k1), (v2, k2)], f, "two"))


def _inverse(ctx: Ctx, law: Law) -> Problem:
    v = ctx.rng.choice([v for v in law.vars if v.exp])
    k = ctx.rng.choice(STEPS[abs(v.exp)])
    f = power(k, v.exp)
    scene, result = ctx.rng.choice(law.scenes)
    q = (f"{scene} With nothing else changed, what must happen to {v.noun} to make {result} "
         f"{as_much(f, law.adj)}? {REASON}")
    a = f"{cap(v.short)} must be {CHANGE[k][0]}. {law.rule} {depends(v)}, so {doing(v, k)} {effect(v, k)}."
    return W(q, a, **_facts(law, [(v, k)], f, "inverse"))


def _independent(ctx: Ctx, law: Law) -> Problem:
    v = ctx.rng.choice([v for v in law.vars if v.exp == 0])
    k = ctx.rng.choice(EASY)
    scene, result = ctx.rng.choice(law.scenes)
    q = f"{scene} If {v.noun} is {CHANGE[k][0]}, what happens to {result}? {REASON}"
    return W(q, f"{cap(result)} does not change. {v.why_not}", **_facts(law, [(v, k)], F(1), "independent"))


def _what_if(ctx: Ctx, laws: list[Law], level: int) -> Problem:
    """Level 1: one quantity, direct or inverse. Level 2: squares and square roots. Level 3: two
    quantities at once, the change needed for a target, or a quantity that doesn't matter."""
    rng = ctx.rng
    linear = [(law, v) for law in laws for v in law.vars if abs(v.exp) == 1]
    if level == 1:
        law, v = rng.choice(linear)
        return _one(ctx, law, v, rng.choice(EASY))
    if level == 2:
        curved = [(law, v) for law in laws for v in law.vars if abs(v.exp) in (2, F(1, 2))]
        if curved:
            law, v = rng.choice(curved)
            return _one(ctx, law, v, rng.choice(STEPS[abs(v.exp)]))
        law, v = rng.choice(linear)
        return _one(ctx, law, v, rng.choice(BIG))
    forms = {_two: [law for law in laws if sum(bool(v.exp) for v in law.vars) >= 2],
             _inverse: [law for law in laws if any(v.exp for v in law.vars)],
             _independent: [law for law in laws if any(v.exp == 0 for v in law.vars)]}
    form = rng.choice([f for f, ok in forms.items() if ok])
    return form(ctx, rng.choice(forms[form]))


def what_if(topic_id: str, laws: list[Law]) -> None:
    """Register the unit's proportional-reasoning skill at all three levels."""
    for level in (1, 2, 3):
        def fn(ctx: Ctx, level: int = level) -> Problem:
            return _what_if(ctx, laws, level)
        fn.__name__ = f"_{topic_id}_what_if_{level}"
        variant(topic_id, level, "What happens if… (proportional reasoning)")(fn)


def pick(ctx: Ctx, table):
    return ctx.rng.choice(table)


# =================================================================== motion

C("concept_motion", "Kinematics", "Motion concepts",
  "falling objects, the top of a throw, sideways launches, and what happens if…")

FALL_PAIRS = [("a bowling ball", "a tennis ball"), ("a brick", "a marble"), ("a full water bottle", "an empty water bottle"),
              ("a steel ball", "a wooden ball of the same size"), ("a large rock", "a small pebble"),
              ("a heavy dumbbell", "a light dumbbell"), ("a watermelon", "a grape"), ("a cannonball", "a musket ball"),
              ("a hammer", "a nail"), ("a heavy wrench", "a light screwdriver")]
FALL_PLACES = ["from the top of a ladder", "from a second-floor balcony", "from a bridge over a dry creek bed",
               "off the roof of a garage", "from the top of a tall building", "from a hot-air balloon"]


@variant("concept_motion", 1, "Falling objects")
def _falling(ctx: Ctx) -> Problem:
    a, b = pick(ctx, FALL_PAIRS)
    where = pick(ctx, FALL_PLACES)
    if ctx.rng.random() < 0.5:
        return W(f"{cap(a)} and {b} are dropped at the same moment {where}. Ignore air resistance. "
                 f"Which one hits the ground first? {REASON}",
                 f"They hit the ground at the same time. Without air resistance every falling object has the same "
                 f"acceleration, $g$, whatever its mass, so {the(a)} and {the(b)} speed up at the same rate.")
    return W(f"{cap(a)} is much heavier than {b}. Both are released together {where}, with no air resistance. "
             f"Compare their speeds just before they land. {REASON}",
             f"{cap(the(a))} and {the(b)} land at the same speed. Both fall with the same acceleration, $g$, for the "
             f"same time, because mass doesn't change how fast an object speeds up in free fall.")


UP_OBJECTS = ["a baseball", "a set of keys", "a volleyball", "an apple", "a juggling pin", "a soccer ball", "a coin",
              "a water balloon", "a beanbag", "a tennis ball"]


@variant("concept_motion", 2, "The top of a throw")
def _top(ctx: Ctx) -> Problem:
    o = pick(ctx, UP_OBJECTS)
    t = the(o)
    kind = ctx.rng.randrange(4)
    if kind == 0:
        return W(f"{cap(o)} is thrown straight up. At the highest point of its flight, what are its velocity and its "
                 f"acceleration? {REASON}",
                 f"At the top its velocity is zero for an instant, but its acceleration is still $g$, downward. "
                 f"Gravity pulls down on {t} the whole time, which is why it stops rising and starts to fall.")
    if kind == 1:
        return W(f"A student says that {o} thrown straight up has zero acceleration at the top of its path, because "
                 f"it stops there. Is the student right? {REASON}",
                 f"No. The velocity of {t} is zero for an instant at the top, but its acceleration is still $g$, "
                 f"downward. If its acceleration were zero there, it would hang in midair instead of falling back down.")
    if kind == 2:
        return W(f"{cap(o)} is tossed straight up and caught at the same height. Compare the direction and size of "
                 f"its acceleration on the way up and on the way down. {REASON}",
                 f"The acceleration is the same both ways: $g$, pointing down. Going up, gravity slows {t}; coming "
                 f"down, it speeds {t} up, but the pull is downward the whole time.")
    return W(f"{cap(o)} is thrown straight up and falls back to the same height. Ignore air resistance. How does the "
             f"time it takes to rise compare with the time it takes to fall back? {REASON}",
             f"The times are equal. With only gravity acting, {t} loses speed on the way up at the same rate it gains "
             f"speed on the way down, so the rise and the fall mirror each other.")


SIDE_OBJECTS = ["ball", "marble", "coin", "rock", "golf ball", "tennis ball", "baseball", "ball bearing"]
SIDE_PLACES = ["the edge of a table", "a cliff", "a balcony", "a bridge", "the roof of a shed", "a lab bench"]


@variant("concept_motion", 3, "Dropped vs. launched sideways")
def _sideways(ctx: Ctx) -> Problem:
    o, place = pick(ctx, SIDE_OBJECTS), pick(ctx, SIDE_PLACES)
    setup = (f"At the same instant, one {o} is dropped from {place} and an identical {o} is launched horizontally "
             f"from the same height. Ignore air resistance.")
    if ctx.rng.random() < 0.5:
        return W(f"{setup} Which {o} reaches the ground first? {REASON}",
                 f"Both {o}s land at the same time. Sideways motion doesn't affect falling: each {o} starts with no "
                 f"downward velocity and falls with acceleration $g$, so they fall for the same time. The launched "
                 f"one just lands farther away.")
    return W(f"{setup} Which {o} is moving faster just before it lands? {REASON}",
             f"The launched {o} is moving faster. Both have the same downward speed when they land, because they fall "
             f"the same height with the same acceleration, but the launched {o} also keeps its sideways speed.")


FALL_WHY_NOT = "Without air resistance every object falls with the same acceleration, $g$, so {} doesn't depend on mass."
what_if("concept_motion", [
    Law("average_speed", "Average speed", "fast",
        [V("d", "the distance covered", "the distance", F(1)), V("t", "the time it takes", "the time", F(-1))],
        [("A runner completes a training route.", "the runner's average speed"),
         ("A family drives from one town to the next.", "the car's average speed"),
         ("A cyclist rides a loop through the park.", "the cyclist's average speed"),
         ("A delivery drone flies to a customer's house.", "the drone's average speed")]),
    Law("fall_speed", "The falling speed", "fast",
        [V("t", "the time since it was dropped", "the falling time", F(1)),
         V("m", "its mass", "the mass", F(0), FALL_WHY_NOT.format("its speed after a given time"))],
        [("A rock is dropped from a tall cliff. Ignore air resistance.", "the rock's speed"),
         ("An apple falls from a high branch. Ignore air resistance.", "the apple's speed"),
         ("A coin is dropped down a deep well. Ignore air resistance.", "the coin's speed")]),
    Law("fall_distance", "The distance fallen", "great",
        [V("t", "the time it falls", "the falling time", F(2)),
         V("m", "its mass", "the mass", F(0), FALL_WHY_NOT.format("the distance it falls in a given time"))],
        [("A stone falls from a high bridge. Ignore air resistance.", "the distance the stone falls"),
         ("A coin is dropped down a deep well. Ignore air resistance.", "the distance the coin falls"),
         ("A walnut falls from a tall tree. Ignore air resistance.", "the distance the walnut falls")]),
    Law("braking", "The stopping distance", "long",
        [V("v", "its speed when the brakes are applied", "the speed", F(2))],
        [("A car brakes to a stop on a dry road, slowing at the same rate every time.", "the car's stopping distance"),
         ("A cyclist brakes to a stop, slowing at the same rate every time.", "the bike's stopping distance"),
         ("A train brakes to a stop at a station, slowing at the same rate every time.",
          "the train's stopping distance")]),
])


# =================================================================== Newton's laws

C("concept_forces", "Forces & dynamics", "Newton's laws concepts",
  "action and reaction, inertia, balanced forces, mass and weight, and what happens if…")

COLLISIONS = [("a loaded truck", "a small car", "crashes into"), ("a bowling ball", "a single pin", "strikes"),
              ("a city bus", "a bicycle", "bumps into"), ("a linebacker", "a much smaller running back", "tackles"),
              ("a hammer", "a nail", "strikes"), ("a car", "a bug", "hits"), ("a baseball bat", "a baseball", "hits"),
              ("a tugboat", "a rowboat", "bumps into"), ("an adult on ice skates", "a child on ice skates", "bumps into"),
              ("a large asteroid", "a small satellite", "collides with")]


@variant("concept_forces", 1, "Action and reaction")
def _reaction(ctx: Ctx) -> Problem:
    big, small, verb = pick(ctx, COLLISIONS)
    if ctx.rng.random() < 0.5:
        return W(f"{cap(big)} {verb} {small}. Which one feels the larger force during the collision? {REASON}",
                 f"The forces are equal in size. By Newton's third law, {big} pushes on {small} exactly as hard as "
                 f"{small} pushes back on {big}, in the opposite direction.")
    return W(f"A student says that when {big} {verb} {small}, {the(big)} pushes harder because it is bigger. "
             f"Do you agree? {REASON}",
             f"No. The two pushes are an action-reaction pair, so by Newton's third law they are equal in size and "
             f"opposite in direction, whichever object is bigger. {cap(the(small))} is affected more only because "
             f"it has less mass.")


@variant("concept_forces", 3, "Action and reaction")
def _reaction_effects(ctx: Ctx) -> Problem:
    big, small, verb = pick(ctx, COLLISIONS)
    if ctx.rng.random() < 0.5:
        return W(f"{cap(big)} {verb} {small}. Compare the forces they exert on each other, and compare their "
                 f"accelerations during the collision. {REASON}",
                 f"The forces are equal in size and opposite in direction (Newton's third law). But {the(small)} has "
                 f"much less mass, so the same size force gives it a much larger acceleration ($a = F/m$).")
    return W(f"{cap(big)} {verb} {small}. Which one has the bigger change in velocity? {REASON}",
             f"{cap(the(small))} does. Both feel the same size force for the same time (Newton's third law), but "
             f"{the(small)} has less mass, so that force gives it a larger acceleration and a bigger change in velocity.")


VEHICLES = ["a bus", "a subway train", "a school bus", "a streetcar"]
SLIDERS = ["a phone on the dashboard", "a backpack on the back seat", "a cup on the dashboard",
           "a bag of groceries on the seat"]
TABLETOP = [("a set of dishes", "dishes"), ("several glasses", "glasses"), ("plates and cups", "plates and cups"),
            ("a stack of plates", "plates")]
ON_CARD = ["a coin", "a marble", "an eraser", "a button"]
CARTS = ["shopping cart", "wagon", "wheelbarrow", "luggage cart"]
DRIFTERS = ["wrench", "camera", "screwdriver", "water bottle"]


@variant("concept_forces", 2, "Inertia")
def _inertia(ctx: Ctx) -> Problem:
    kind = ctx.rng.randrange(6)
    if kind == 0:
        v = pick(ctx, VEHICLES)
        return W(f"Standing passengers on {v} lurch forward when it brakes suddenly. Explain why, using the idea of "
                 f"inertia.",
                 f"Their bodies have inertia, so they keep moving forward at the original speed. The brakes slow "
                 f"{the(v)}, but nothing slows the passengers until the floor or a handrail pushes on them.")
    if kind == 1:
        v = pick(ctx, VEHICLES)
        return W(f"When {v} pulls away quickly, standing passengers stumble backward. Explain why, using the idea of "
                 f"inertia.",
                 f"Their bodies have inertia, so they tend to stay at rest. {cap(the(v))} moves forward under them, "
                 f"so they seem to fall backward until the floor or a handrail pushes them along.")
    if kind == 2:
        obj, (turn, side) = pick(ctx, SLIDERS), pick(ctx, [("left", "right"), ("right", "left")])
        return W(f"A car turns sharply to the {turn}, and {obj} slides toward the {side} side of the car. "
                 f"Explain why.",
                 f"{cap(the(obj.split(' on ')[0]))} keeps moving in a straight line because of its inertia, while "
                 f"the car turns {turn} beneath it. No force pushes it to the {side}; the car turns out from under it.")
    if kind == 3:
        what, ref = pick(ctx, TABLETOP)
        return W(f"A magician yanks a tablecloth out from under {what}, and the {ref} hardly move. Explain why.",
                 f"The {ref} have inertia: at rest, they tend to stay at rest. The cloth moves so fast "
                 f"that friction pulls on them for only a very short time, too short to get them moving much.")
    if kind == 4:
        what = pick(ctx, ON_CARD)
        return W(f"{cap(what)} rests on an index card on top of a glass. The card is flicked away quickly, and "
                 f"{the(what)} drops into the glass. Explain why.",
                 f"{cap(the(what))} has inertia, so it stays where it is while the card shoots out from under it. "
                 f"With nothing left to hold it up, gravity pulls it straight down into the glass.")
    if ctx.rng.random() < 0.5:
        cart = pick(ctx, CARTS)
        return W(f"Why is it harder to stop a full {cart} than an empty one moving at the same speed? {REASON}",
                 f"The full {cart} has more mass, so it has more inertia: it resists changes to its motion more. "
                 f"Stopping it takes a bigger force, or the same force for a longer time.")
    tool = pick(ctx, DRIFTERS)
    return W(f"An astronaut in deep space, far from any planet, lets go of a {tool} that is drifting along with her. "
             f"What does the {tool} do afterward? {REASON}",
             f"The {tool} keeps moving in a straight line at the same speed. With no net force on it, nothing changes "
             f"its motion (Newton's first law), so it drifts on until something pushes or pulls it.")


STEADY = [("A skydiver falls at a steady terminal speed.", "the skydiver",
           "Air resistance pushing up balances the skydiver's weight."),
          ("A car cruises at a steady speed on a straight, level highway.", "the car",
           "The forward push of the road on the tires balances air resistance and other friction."),
          ("An elevator rises at a constant speed.", "the elevator", "The cable's upward pull balances its weight."),
          ("A hockey puck glides across smooth ice at a constant speed.", "the puck",
           "The ice pushes up as hard as gravity pulls down, and there is almost no friction."),
          ("A worker pushes a crate across the floor at a constant speed.", "the crate",
           "The worker's push balances the friction from the floor."),
          ("A jet flies level at a constant speed.", "the jet",
           "Lift balances its weight, and the engines' thrust balances air resistance."),
          ("A raindrop falls at a steady speed near the ground.", "the raindrop",
           "Air resistance pushing up balances its weight."),
          ("A boat motors across a calm lake at a constant speed.", "the boat",
           "The push from the propeller balances the drag of the water."),
          ("A cyclist rides at a steady speed along a flat road.", "the cyclist",
           "The push from the road balances air resistance and rolling friction.")]


@variant("concept_forces", 2, "Balanced forces")
def _steady(ctx: Ctx) -> Problem:
    scene, who, balance = pick(ctx, STEADY)
    if ctx.rng.random() < 0.5:
        return W(f"{scene} What is the net force on {who}? {REASON}",
                 f"The net force on {who} is zero. {balance} An object moving in a straight line at a constant speed "
                 f"has no acceleration, so the forces on it must balance.")
    return W(f"{scene} A student says there must be an overall force on {who} in the direction it moves, or it would "
             f"stop. Do you agree? {REASON}",
             f"No. {cap(who)} moves at a constant velocity, so its acceleration and the net force on it are zero. "
             f"{balance} A net force would change its speed; none is needed to keep it moving.")


TRAVELERS = [("an astronaut", 70), ("an astronaut", 60), ("a rover", 900), ("a robot", 150), ("a bag of tools", 20),
             ("a space probe", 400), ("a scientist", 80)]
WORLDS = [("the Moon", r"about $\frac{1}{6}$ of", "gravity on the Moon is much weaker"),
          ("Mars", r"about $\frac{3}{8}$ of", "gravity on Mars is weaker"),
          ("deep space, far from any planet or star", "nearly zero, much less than",
           "there is almost no gravity pulling on it there"),
          ("a planet where gravity is twice as strong as on Earth", "twice", "gravity there is twice as strong")]


@variant("concept_forces", 3, "Mass and weight")
def _mass_weight(ctx: Ctx) -> Problem:
    who, m = pick(ctx, TRAVELERS)
    if ctx.rng.random() < 0.6:
        place, share, why = pick(ctx, WORLDS)
        return W(f"{cap(who)} with a mass of ${m}\\,\\mathrm{{kg}}$ travels from Earth to {place}. How do its mass and "
                 f"its weight there compare with on Earth? {REASON}",
                 f"The mass of {the(who)} is still ${m}\\,\\mathrm{{kg}}$: mass measures the amount of matter, which "
                 f"doesn't change from place to place. Its weight, the pull of gravity on it, is {share} its weight "
                 f"on Earth, because {why}.")
    place, share, why = pick(ctx, WORLDS[:2])
    return W(f"A student says that {who} with a mass of ${m}\\,\\mathrm{{kg}}$ has less mass on {place} because it "
             f"weighs less there. Do you agree? {REASON}",
             f"No. Its weight drops to {share} its Earth weight because {why}, but its mass is still "
             f"${m}\\,\\mathrm{{kg}}$. Mass is the amount of matter in {the(who)}, and that doesn't depend on where it is.")


what_if("concept_forces", [
    Law("newton2", "Acceleration", "large",
        [V("F", "the net force on it", "the net force", F(1)), V("m", "its mass", "the mass", F(-1))],
        [("A team pushes a stalled car along a level road.", "the car's acceleration"),
         ("A hockey puck is pushed across frictionless ice.", "the puck's acceleration"),
         ("A rocket's engines push it through deep space.", "the rocket's acceleration"),
         ("A tugboat pulls a barge across a calm lake.", "the barge's acceleration"),
         ("A student pushes a cart across a smooth floor.", "the cart's acceleration")]),
    Law("weight", "Weight", "large",
        [V("m", "its mass", "the mass", F(1)), V("g", "the strength of gravity", "the strength of gravity", F(1))],
        [("A space probe lands on a distant planet.", "the probe's weight"),
         ("An astronaut stands on a scale on another planet.", "the astronaut's weight"),
         ("A rover is parked on the surface of a moon.", "the rover's weight")]),
])


# =================================================================== momentum

C("concept_momentum", "Momentum", "Momentum concepts",
  "cushioning a stop, recoil, objects that stick together, and what happens if…")

CUSHIONS = [("airbags", "a driver in a crash"), ("bending your knees", "your legs when you land a jump"),
            ("a gymnastics mat", "a gymnast who lands on it"), ("crumple zones in a car's front end",
                                                                  "the passengers in a crash"),
            ("moving your hands back as you catch a raw egg", "the egg"),
            ("a padded dashboard", "a passenger's head in a crash"), ("a thick catcher's mitt", "the catcher's hand"),
            ("a big air cushion", "a stunt performer who falls onto it"),
            ("a net under a trapeze", "a performer who falls into it"),
            ("a bicycle helmet's foam lining", "a rider's head in a fall")]


@variant("concept_momentum", 1, "Cushioning a stop")
@variant("concept_momentum", 2, "Cushioning a stop")
def _cushion(ctx: Ctx) -> Problem:
    thing, who = pick(ctx, CUSHIONS)
    q = (f"Explain how {thing} reduces the force on {who}." if ctx.rng.random() < 0.5
         else f"Use the idea of impulse to explain why {thing} protects {who}.")
    return W(q, f"{cap(thing)} makes the stop last longer. The change in momentum is the same either way, and since "
                f"impulse (force × time) equals that change, a longer stopping time means a smaller force on {who}.")


RECOILS = [("A large skater and a small skater stand still on the ice and push off each other.",
            "the large skater", "the small skater"),
           ("A cannon on wheels, at rest, fires a cannonball.", "the cannon", "the cannonball"),
           ("A hunter holding a rifle at rest fires it.", "the rifle", "the bullet"),
           ("An astronaut floating at rest in space throws a wrench away from her.", "the astronaut", "the wrench"),
           ("A father and his young daughter stand at rest on ice skates and push each other apart.",
            "the father", "the daughter"),
           ("A space station at rest pushes a small satellite away from itself.", "the space station",
            "the satellite"),
           ("A bowler standing at rest on frictionless ice throws a bowling ball forward.", "the bowler", "the ball"),
           ("A toy cannon on a skateboard, at rest, fires a foam ball.", "the cannon and skateboard",
            "the foam ball")]


@variant("concept_momentum", 2, "Recoil")
def _recoil(ctx: Ctx) -> Problem:
    setup, heavy, light = pick(ctx, RECOILS)
    if ctx.rng.random() < 0.5:
        return W(f"{setup} Compare the momentum of {heavy} and of {light} just afterward. {REASON}",
                 f"They have equal and opposite momentum. The total momentum was zero before, so it must still be "
                 f"zero after: the momentum of {heavy} cancels the momentum of {light}.")
    return W(f"{setup} Which moves away faster, and why?",
             f"{cap(light)} moves faster. Both get equal and opposite momentum, because the total stays zero, and "
             f"{light} has less mass, so it needs a larger speed to have the same size momentum.")


STICKERS = [("cart", "on a frictionless track"), ("train car", "on a level track"), ("glider", "on an air track"),
            ("toy car", "on a smooth floor")]
SHARE = {1: ("an identical {x}", "half", 2), 2: ("a {x} with twice its mass", "one third", 3),
         3: ("a {x} with three times its mass", "one quarter", 4)}


@variant("concept_momentum", 3, "Objects that stick together")
def _stick(ctx: Ctx) -> Problem:
    x, where = pick(ctx, STICKERS)
    n = ctx.rng.choice([1, 2, 3])
    other, part, total = SHARE[n]
    other = other.format(x=x)
    setup = f"A moving {x} {where} collides with {other} at rest, and they stick together."
    if ctx.rng.random() < 0.5:
        return W(f"{setup} How does their speed afterward compare with the first {x}'s speed before? {REASON}",
                 f"They move at {part} of the original speed. Momentum is conserved, and afterward the same momentum "
                 f"is shared by {total} times the mass, so the speed is divided by {total}.")
    return W(f"{setup} A student predicts the pair will move at the same speed the first {x} had. Do you agree? "
             f"{REASON}",
             f"No. Momentum is conserved, not speed: afterward the same momentum is carried by {total} times the mass, "
             f"so they move at only {part} of the original speed.")


what_if("concept_momentum", [
    Law("momentum", "Momentum", "large",
        [V("m", "its mass", "the mass", F(1)), V("v", "its speed", "the speed", F(1))],
        [("A bowling ball rolls down the lane.", "the ball's momentum"),
         ("A freight train rolls along a straight track.", "the train's momentum"),
         ("A hockey player skates toward the goal.", "the player's momentum"),
         ("A delivery truck drives along a highway.", "the truck's momentum"),
         ("A soccer ball rolls across the field.", "the ball's momentum")]),
    Law("stopping_force", "The average stopping force", "large",
        [V(r"\Delta t", "the time it takes to stop", "the stopping time", F(-1)),
         V(r"\Delta p", "the momentum it loses", "the change in momentum", F(1))],
        [("A catcher stops a fastball with her mitt.", "the average force on the mitt"),
         ("An airbag stops a passenger in a crash.", "the average force on the passenger"),
         ("A stunt performer lands on a large air cushion.", "the average force on the performer"),
         ("A gymnast lands on a mat.", "the average force on the gymnast")]),
])


# =================================================================== energy

C("concept_energy", "Work, energy & power", "Energy concepts",
  "energy changes, frictionless ramps and roller coasters, work and power, and what happens if…")

TRANSFORMS = [
    ("an apple falls from a tree", "Gravitational potential energy becomes kinetic energy as the apple speeds up, "
                                   "with a little turned into heat by air resistance."),
    ("a bow shoots an arrow", "Elastic potential energy stored in the bent bow becomes the arrow's kinetic energy."),
    ("a car brakes to a stop", "The car's kinetic energy becomes thermal energy (heat) in the brakes and tires."),
    ("a flashlight is switched on", "Chemical energy in the batteries becomes electrical energy, which the bulb "
                                    "turns into light (and some heat)."),
    ("a roller coaster car rolls down its first hill", "Gravitational potential energy becomes kinetic energy as the "
                                                       "car loses height and speeds up."),
    ("a wind turbine runs", "The wind's kinetic energy turns the blades, and the generator turns that motion into "
                            "electrical energy."),
    ("you rub your hands together on a cold day", "The kinetic energy of your moving hands becomes thermal energy "
                                                  "through friction, so your hands warm up."),
    ("a pendulum swings up from the bottom of its arc", "Kinetic energy becomes gravitational potential energy as "
                                                        "the bob slows down and rises."),
    ("a gas stove heats a pot of water", "Chemical energy in the gas becomes thermal energy in the flame, which "
                                         "heats the pot and the water."),
    ("a trampoline launches a jumper upward", "Elastic potential energy in the stretched trampoline becomes kinetic "
                                              "energy, then gravitational potential energy as the jumper rises."),
    ("a solar panel powers a calculator", "Light energy from the Sun becomes electrical energy in the panel."),
    ("a ball rolls to a stop on grass", "The ball's kinetic energy becomes thermal energy through friction with "
                                        "the grass."),
    ("a battery-powered fan runs", "Chemical energy in the battery becomes electrical energy, which the motor turns "
                                   "into the blades' kinetic energy."),
    ("a firework explodes", "Chemical energy becomes light, sound, thermal energy and the kinetic energy of the "
                            "flying pieces."),
]


@variant("concept_energy", 1, "Energy changes")
def _transform(ctx: Ctx) -> Problem:
    scene, answer = pick(ctx, TRANSFORMS)
    q = (f"Describe the energy changes when {scene}." if ctx.rng.random() < 0.5
         else f"When {scene}, where does the energy come from and where does it go? {REASON}")
    return W(q, answer)


SLOPES = [("two identical kids", "slides", "slide"), ("two identical carts", "ramps", "ramp"),
          ("two identical skiers", "slopes", "slope"), ("two identical marbles", "tracks", "track"),
          ("two identical skateboarders", "ramps", "ramp")]
RIDERS = [("cart", "ramp"), ("marble", "track"), ("sled", "hill"), ("toy car", "track")]


@variant("concept_energy", 2, "Frictionless ramps and roller coasters")
def _ramps(ctx: Ctx) -> Problem:
    kind = ctx.rng.randrange(5)
    if kind < 2:
        who, pl, one = pick(ctx, SLOPES)
        shape = ("One {s} is steep and short; the other is gentle and long." if kind == 0
                 else "One {s} is straight; the other curves and dips along the way.").format(s=one)
        return W(f"{cap(who)} start from rest at the same height on two frictionless {pl}. {shape} Compare their "
                 f"speeds at the bottom. {REASON}",
                 f"They reach the bottom at the same speed. With no friction, gravitational potential energy turns "
                 f"into kinetic energy, and both drop the same height, so they gain the same kinetic energy whatever "
                 f"the shape of the {one}.")
    if kind == 2:
        x, track = pick(ctx, RIDERS)
        return W(f"A heavy {x} and a light {x} start from rest at the top of the same frictionless {track}. Compare "
                 f"their speeds at the bottom. {REASON}",
                 f"They reach the same speed. The heavy {x} has more potential energy to start with, but it also needs "
                 f"more kinetic energy for any given speed, so the mass cancels out.")
    h = ctx.rng.choice([30, 40, 50, 60])
    if kind == 3:
        return W(f"A roller coaster car starts from rest at the top of a ${h}\\,\\mathrm{{m}}$ hill, and the track has "
                 f"no friction. Where on the ride is it moving fastest? {REASON}",
                 f"At the lowest point of the track. Its total energy stays the same, so it has the most kinetic energy, "
                 f"and the highest speed, where it has the least gravitational potential energy.")
    return W(f"A roller coaster car starts from rest at the top of a ${h}\\,\\mathrm{{m}}$ hill, and the track has no "
             f"friction. Can it get over a later hill that is ${h + 10}\\,\\mathrm{{m}}$ tall? {REASON}",
             f"No. It starts with only enough energy to climb back to ${h}\\,\\mathrm{{m}}$. Reaching "
             f"${h + 10}\\,\\mathrm{{m}}$ would need more gravitational potential energy than its total energy, and "
             f"energy can't be created.")


CARRIERS = [("A student carries a heavy box", "her arms", "box"), ("A waiter carries a tray of drinks", "his hand", "tray"),
            ("A hiker carries a backpack", "the shoulder straps", "backpack"),
            ("A shopper carries a bag of groceries", "her arms", "bag"), ("A mover carries a chair", "his arms", "chair"),
            ("A child carries a stack of books", "her arms", "stack of books"),
            ("A worker carries a toolbox", "his hand", "toolbox"), ("A nurse carries a tray of supplies", "her hands", "tray")]
PUSHES = [("A student pushes hard on a brick wall for a full minute", "the wall"),
          ("A player pushes against a parked car that doesn't budge", "the car"),
          ("A worker pushes on a stuck door that won't open", "the door"),
          ("A child pushes on a heavy piano that doesn't move", "the piano")]
LIFTS = [("A crane lifts a steel beam straight up, then swings it sideways at the same height.", "the beam", "crane"),
         ("A forklift raises a pallet, then drives it across the warehouse at the same height.", "the pallet",
          "forklift"),
         ("A parent lifts a toddler up, then carries her across the room at the same height.", "the toddler",
          "parent")]
STAIRS = [(10, 20), (8, 16), (12, 24), (6, 12), (5, 15), (10, 30), (9, 18)]


@variant("concept_energy", 3, "Work and power")
def _work(ctx: Ctx) -> Problem:
    kind = ctx.rng.randrange(4)
    if kind == 0:
        who, holder, obj = pick(ctx, CARRIERS)
        return W(f"{who} across a level room at a constant speed. How much work does the upward force of {holder} do "
                 f"on the {obj}? {REASON}",
                 f"No work at all. A force does work only when the object moves along the direction of the force, and "
                 f"the {obj} moves sideways while the force on it points up.")
    if kind == 1:
        who, obj = pick(ctx, PUSHES)
        return W(f"{who}. How much work is done on {obj}? {REASON}",
                 f"No work is done on {obj}. Work needs a force and a movement in the direction of the force, and "
                 f"{obj} doesn't move, even though the person pushing gets tired (energy is used inside the muscles).")
    if kind == 2:
        scene, obj, machine = pick(ctx, LIFTS)
        return W(f"{scene} During which part does the {machine} do work on {obj}? {REASON}",
                 f"Only while lifting. Raising {obj} moves it in the direction of the upward force, so work is done; "
                 f"moving it sideways at the same height doesn't, because the upward force is perpendicular to that "
                 f"motion.")
    fast, slow = pick(ctx, STAIRS)
    times = {2: "twice", 3: "three times"}[slow // fast]
    return W(f"Two students with the same weight run up the same flight of stairs. One takes {fast} seconds and the "
             f"other takes {slow} seconds. Compare the work they do and their power. {REASON}",
             f"They do the same work, because they lift the same weight through the same height. Power is work done "
             f"per second, so the student who takes {fast} seconds has {times} the power.")


what_if("concept_energy", [
    Law("kinetic", "Kinetic energy", "large",
        [V("m", "its mass", "the mass", F(1)), V("v", "its speed", "the speed", F(2))],
        [("A car drives along a highway.", "the car's kinetic energy"),
         ("A runner sprints down a track.", "the runner's kinetic energy"),
         ("A baseball flies toward home plate.", "the ball's kinetic energy"),
         ("A cyclist coasts along a flat road.", "the cyclist's kinetic energy")]),
    Law("potential", "Gravitational potential energy", "large",
        [V("m", "its mass", "the mass", F(1)), V("h", "its height above the ground", "the height", F(1))],
        [("A box sits on a high shelf.", "the box's gravitational potential energy"),
         ("A hiker stands on a hilltop.", "the hiker's gravitational potential energy"),
         ("A flowerpot sits on a windowsill.", "the flowerpot's gravitational potential energy")]),
    Law("power", "Power", "large",
        [V("W", "the work done", "the work", F(1)), V("t", "the time it takes", "the time", F(-1))],
        [("A motor lifts an elevator to the top floor.", "the motor's power"),
         ("A student runs up a flight of stairs.", "the student's power"),
         ("A crane lifts a steel beam onto a building.", "the crane's power")]),
])


# =================================================================== torque

C("concept_torque", "Torque & rotational dynamics", "Torque and balance concepts",
  "lever arms, balancing a seesaw, stability, and what happens if…")

LEVERS = [
    ("a doorknob is placed on the side of a door farthest from the hinges",
     "The torque on the door is the force times its distance from the hinges (the lever arm). With the knob far from "
     "the hinges, the same push makes more torque, so the door swings easily."),
    ("it is easier to loosen a tight bolt with a long wrench than with a short one",
     "A long wrench gives a longer lever arm, so the same force on the handle makes more torque on the bolt."),
    ("it is hard to open a door by pushing close to its hinges",
     "Close to the hinges the lever arm is tiny, so even a big push makes only a small torque on the door."),
    ("a bus has a much larger steering wheel than a go-kart",
     "Pushing on the rim of a large wheel gives a long lever arm, so the driver's force makes more torque to turn the "
     "heavy steering."),
    ("long-handled pruning shears can cut branches that short scissors can't",
     "The long handles give a long lever arm, so the same squeeze makes a much bigger torque, and a bigger cutting "
     "force at the blades."),
    ("plumbers sometimes slip a pipe over the handle of a wrench",
     "The pipe makes the handle longer, so the lever arm is longer and the same force makes more torque on a stuck "
     "fitting."),
    ("a screwdriver with a thick handle is easier to turn than one with a thin handle",
     "A thick handle puts your grip farther from the screwdriver's axis, so your hand's force acts with a longer lever "
     "arm and makes more torque."),
    ("a long crowbar can pry up a rock that you couldn't lift",
     "Pushing far from the pivot gives a long lever arm, so a small force makes a large torque, enough to lift the "
     "heavy rock close to the pivot."),
    ("a load in a wheelbarrow is easier to lift when it sits close to the wheel",
     "The wheel is the pivot. A load close to the wheel has a short lever arm, so it makes less torque, and your hands "
     "at the far end of the handles need less force to balance it."),
    ("a merry-go-round is easiest to start by pushing at its outer edge",
     "At the edge your push has the longest lever arm, so it makes the most torque on the merry-go-round."),
]


@variant("concept_torque", 1, "Lever arms")
def _lever(ctx: Ctx) -> Problem:
    statement, answer = pick(ctx, LEVERS)
    q = (f"Using the idea of torque, explain why {statement}." if ctx.rng.random() < 0.5
         else f"Explain, in terms of torque and lever arms, why {statement}.")
    return W(q, answer)


KIDS = ["Maya", "Leo", "Ava", "Sam", "Zoe", "Eli", "Nina", "Omar", "Ruby", "Theo", "Ivy", "Jake"]


def _two_kids(ctx: Ctx) -> tuple[str, str]:
    heavy, light = ctx.rng.sample(KIDS, 2)
    return heavy, light


@variant("concept_torque", 2, "Balancing a seesaw")
def _seesaw(ctx: Ctx) -> Problem:
    heavy, light = _two_kids(ctx)
    if ctx.rng.random() < 0.4:
        return W(f"{heavy} is heavier than {light}. To balance on a seesaw, who should sit closer to the pivot? "
                 f"{REASON}",
                 f"{heavy} should sit closer. For balance the two torques must be equal, and torque is weight times "
                 f"distance from the pivot, so the heavier person needs the shorter distance.")
    d = ctx.rng.choice([1.2, 1.6, 2.0, 2.4, 3.0])
    return W(f"{heavy} weighs twice as much as {light}. {light} sits ${d:g}\\,\\mathrm{{m}}$ from the pivot of a "
             f"seesaw. Where should {heavy} sit to balance it? {REASON}",
             f"{heavy} should sit ${d / 2:g}\\,\\mathrm{{m}}$ from the pivot, on the other side. For balance the two "
             f"torques (weight × distance) must be equal, so twice the weight needs half the distance.")


@variant("concept_torque", 3, "Balancing a seesaw")
def _seesaw_hard(ctx: Ctx) -> Problem:
    heavy, light = _two_kids(ctx)
    d = ctx.rng.choice([1.5, 1.8, 2.4, 3.0, 3.6])
    if ctx.rng.random() < 0.5:
        return W(f"{heavy} weighs three times as much as {light}. {light} sits ${d:g}\\,\\mathrm{{m}}$ from the pivot "
                 f"of a seesaw. Where should {heavy} sit to balance it? {REASON}",
                 f"${d / 3:g}\\,\\mathrm{{m}}$ from the pivot, on the other side. The torques (weight × distance) must "
                 f"be equal, so three times the weight needs one third of the distance.")
    return W(f"{heavy} and {light} balance on a seesaw, {heavy} ${d / 3:g}\\,\\mathrm{{m}}$ from the pivot and "
             f"{light} ${d:g}\\,\\mathrm{{m}}$ from it. How do their weights compare? {REASON}",
             f"{heavy} weighs three times as much as {light}. Balanced torques mean weight × distance is the same on "
             f"both sides, and {light} sits three times as far out, so {heavy} must be three times as heavy.")


STABLE = [
    ("race cars are built low and wide",
     "A low center of gravity and a wide base let the car tilt a long way before its center of gravity moves past its "
     "wheels, so it is hard to tip over in a fast turn."),
    ("tall delivery vans tip over more easily than sports cars in sharp turns",
     "A tall van has a high center of gravity, so a small tilt moves it outside the wheels and gravity then tips the "
     "van over. A low sports car must tilt much farther before that happens."),
    ("you lean forward when you wear a heavy backpack",
     "Leaning forward keeps the center of gravity of you and the pack above your feet, so gravity doesn't make a "
     "torque that tips you backward."),
    ("you lean to the left when you carry a heavy bucket in your right hand",
     "Leaning left moves your body's weight to balance the bucket, keeping the combined center of gravity above your "
     "feet so you don't tip toward the bucket."),
    ("a lamp with a wide, heavy base is hard to knock over",
     "The heavy base keeps the center of gravity low and the wide base gives it a lot of room to move before it "
     "passes the edge, so the lamp rights itself instead of tipping."),
    ("wrestlers crouch low with their feet spread apart",
     "Crouching lowers their center of gravity and spreading their feet widens their base, so they can be pushed a "
     "long way before their center of gravity passes outside their feet."),
    ("heavy books belong on the bottom shelves of a tall bookcase",
     "Heavy books low down keep the bookcase's center of gravity low, so it would have to tilt much farther before "
     "tipping over."),
    ("a canoe tips more easily when someone stands up in it",
     "Standing raises the center of gravity of the canoe and its riders, so a smaller tilt carries it past the point "
     "where gravity tips the canoe over."),
    ("traffic cones are wide and heavy at the bottom",
     "The wide, heavy base keeps the center of gravity low and the base broad, so wind or a bump can't easily tilt "
     "the center of gravity past the edge."),
]
TIPPY = [("a tall, narrow vase", "a short, wide bowl"),
         ("a bookcase with heavy books on its top shelf", "the same bookcase with the books on its bottom shelf"),
         ("a person standing up straight", "a person crouching with feet apart"),
         ("an SUV with heavy cargo on its roof rack", "the same SUV with the cargo inside on the floor"),
         ("a full glass of water", "a wide, shallow bowl holding the same water")]


@variant("concept_torque", 3, "Stability")
def _stability(ctx: Ctx) -> Problem:
    if ctx.rng.random() < 0.65:
        statement, answer = pick(ctx, STABLE)
        return W(f"Using the idea of center of gravity, explain why {statement}.", answer)
    tippy, steady = pick(ctx, TIPPY)
    first = ctx.rng.random() < 0.5
    a, b = (tippy, steady) if first else (steady, tippy)
    return W(f"Which is easier to tip over: {a} or {b}? {REASON}",
             f"{cap(tippy)} is easier to tip over. Its center of gravity is higher (or its base narrower), so a smaller "
             f"tilt moves the center of gravity past the edge of its base, and then gravity tips it over.")


what_if("concept_torque", [
    Law("torque", "Torque", "large",
        [V("F", "the force applied", "the force", F(1)),
         V("r", "the distance from the pivot to where the force is applied", "the lever arm", F(1))],
        [("A mechanic loosens a bolt with a wrench.", "the torque on the bolt"),
         ("A student pushes on a door to open it.", "the torque on the door"),
         ("A cyclist pushes down on a pedal.", "the torque on the pedal crank"),
         ("A child pushes a merry-go-round at its edge.", "the torque on the merry-go-round")]),
])


# =================================================================== circular motion & gravity

C("concept_circular", "Circular motion & gravitation", "Circular motion and gravity concepts",
  "the path after letting go, the force toward the center, orbits and weightlessness, and what happens if…")

WHIRLS = [("A ball on a string is whirled in a horizontal circle, and the string breaks.", "the ball"),
          ("A stone is whirled around in a sling and then let go.", "the stone"),
          ("A hammer thrower spins around and lets go of the hammer.", "the hammer"),
          ("Mud flies off the rim of a spinning bicycle wheel.", "each bit of mud"),
          ("Water drops fly off the basket of a spinning salad spinner.", "each drop"),
          ("Sparks fly off a spinning grinding wheel.", "each spark"),
          ("A car going around a curve hits a patch of ice that takes away all friction.", "the car"),
          ("A charm on a necklace is twirled in a circle, and the chain snaps.", "the charm"),
          ("A yo-yo is swung in a horizontal circle, and the string snaps.", "the yo-yo")]


@variant("concept_circular", 1, "Leaving the circle")
def _let_go(ctx: Ctx) -> Problem:
    event, obj = pick(ctx, WHIRLS)
    if ctx.rng.random() < 0.5:
        return W(f"{event} Seen from above, what path does {obj} follow after it leaves the circle? {REASON}",
                 f"{cap(obj)} moves off in a straight line along the tangent to the circle, in the direction it was "
                 f"moving at that instant, not straight out from the center. Once nothing pulls it toward the center, "
                 f"it keeps going straight (Newton's first law).")
    return W(f"{event} A student says {obj} flies straight outward, away from the center. Is that right? {REASON}",
             f"No. {cap(obj)} moves off along the tangent, in the direction it was already moving. There is no outward "
             f"force on it; the inward pull simply stops, so it continues in a straight line.")


CIRCLERS = [("A car rounds a flat curve at a constant speed.", "the car", "friction from the road on the tires"),
            ("A satellite orbits the Earth in a circle.", "the satellite", "the Earth's gravity"),
            ("A ball on a string is whirled in a horizontal circle at a steady speed.", "the ball",
             "the pull of the string"),
            ("A runner jogs around a circular track at a steady pace.", "the runner",
             "friction from the track on the runner's shoes"),
            ("The Moon orbits the Earth.", "the Moon", "the Earth's gravity"),
            ("A cyclist rounds a corner at a steady speed.", "the bike and rider",
             "friction from the road on the tires"),
            ("A child rides a merry-go-round that turns at a steady rate.", "the child",
             "the pull of the bar the child holds on to"),
            ("The Earth orbits the Sun.", "the Earth", "the Sun's gravity")]


@variant("concept_circular", 2, "The force toward the center")
def _center(ctx: Ctx) -> Problem:
    scene, obj, force = pick(ctx, CIRCLERS)
    if ctx.rng.random() < 0.5:
        return W(f"{scene} What force keeps {obj} moving in a circle, and which way does it point? {REASON}",
                 f"{cap(force)} keeps {obj} on its circle, and it points toward the center of the circle. Anything "
                 f"moving in a circle needs a net force toward the center; without it, {obj} would move off in a "
                 f"straight line.")
    return W(f"{scene} Is {obj} accelerating, even though its speed is constant? {REASON}",
             f"Yes. The direction of {obj} keeps changing, so its velocity changes, and that is acceleration. The "
             f"acceleration points toward the center of the circle, the same way as the net force from {force}.")


CRAFT = ["the International Space Station", "an orbiting space lab", "a space capsule in orbit",
         "a space shuttle in orbit"]
ORBITERS = [("the Moon", "the Earth"), ("a satellite", "the Earth"), ("the Earth", "the Sun"),
            ("Jupiter's moon Io", "Jupiter")]
FREE_FALL_RIDES = [("a drop-tower ride", "as the ride car falls", "the ride car"),
                   ("a roller coaster", "going over the top of a steep hill", "the coaster car"),
                   ("an airplane flying a steep dive for astronaut training", "during the dive", "the plane")]
PULLERS = ["you", "a falling apple", "the Moon", "a satellite"]


@variant("concept_circular", 3, "Orbits and weightlessness")
def _orbits(ctx: Ctx) -> Problem:
    kind = ctx.rng.randrange(4)
    if kind == 0:
        craft = pick(ctx, CRAFT)
        return W(f"Astronauts aboard {craft} float around the cabin. A student says this is because there is no "
                 f"gravity in space. Do you agree? {REASON}",
                 f"No. In low orbit, gravity is still about 90% as strong as on the ground. The astronauts float "
                 f"because they and {craft} are falling around the Earth together, so nothing presses them against "
                 f"the floor.")
    if kind == 1:
        small, big = pick(ctx, ORBITERS)
        return W(f"Gravity pulls {small} toward {big}. Why doesn't {small} fall into {big}? {REASON}",
                 f"It is falling: gravity pulls it toward {big} all the time. But {small} also moves sideways so fast "
                 f"that as it falls it keeps missing {big}, so it falls around it in an orbit instead of into it.")
    if kind == 2:
        ride, when, car = pick(ctx, FREE_FALL_RIDES)
        return W(f"Why do people on {ride} feel weightless {when}? {REASON}",
                 f"They are in free fall: they and {car} fall together, so nothing pushes up on them. "
                 f"The feeling of weight comes from the push of the floor or seat, not from gravity, which is still "
                 f"pulling on them.")
    who = pick(ctx, PULLERS)
    return W(f"Does the Earth pull on {who} harder than {who} pull{'' if who == 'you' else 's'} on the Earth? "
             f"{REASON}",
             f"No. The two pulls are an action-reaction pair, so they are equal in size (Newton's third law). The "
             f"Earth barely moves in response because its mass is enormous, so the same force gives it a tiny "
             f"acceleration.")


what_if("concept_circular", [
    Law("centripetal", "The force needed to keep it on the circle", "large",
        [V("m", "its mass", "the mass", F(1)), V("v", "its speed", "the speed", F(2)),
         V("r", "the radius of its circle", "the radius", F(-1))],
        [("A car rounds a flat curve on the highway.", "the friction force needed to keep the car on the curve"),
         ("A ball on a string is whirled in a horizontal circle.", "the pull needed from the string"),
         ("A runner jogs around a circular track.", "the sideways force the runner needs from the ground"),
         ("A cyclist rounds a curve in the road.", "the friction force needed to keep the bike on its curve")]),
    Law("gravity", "The gravitational force", "strong",
        [V("m", "the mass of one of them", "that mass", F(1)),
         V("r", "the distance between their centers", "the distance", F(-2))],
        [("A moon orbits a planet.", "the gravitational force between the moon and the planet"),
         ("Two asteroids drift near each other in space.", "the gravitational force between the asteroids"),
         ("A satellite orbits the Earth.", "the gravitational force between the satellite and the Earth"),
         ("Two spaceships float in deep space, far from any planet.", "the gravitational pull between the ships")]),
])


# =================================================================== fluids

C("concept_fluids", "Fluids", "Pressure and buoyancy concepts",
  "floating and sinking, pressure and depth, buoyancy, and what happens if…")

MATERIALS = [("oak", "0.75"), ("pine", "0.50"), ("cork", "0.24"), ("ice", "0.92"), ("candle wax", "0.90"),
             ("aluminum", "2.7"), ("steel", "7.9"), ("copper", "8.9"), ("glass", "2.5"), ("gold", "19.3"),
             ("brick", "1.9"), ("rubber", "1.2"), ("granite", "2.7"), ("plastic foam", "0.05"), ("lead", "11.3")]
LIQUIDS = [("fresh water", "1.0"), ("corn syrup", "1.4"), ("mercury", "13.6")]
GCC = r"\,\mathrm{g/cm^3}"


@variant("concept_fluids", 1, "Float or sink")
@variant("concept_fluids", 2, "Float or sink")
def _float(ctx: Ctx) -> Problem:
    (mat, d), (liq, dl) = pick(ctx, MATERIALS), pick(ctx, LIQUIDS)
    floats = float(d) < float(dl)
    lead = (f"A block of {mat} has a density of ${d}{GCC}$. Will it float or sink in {liq}, whose density is "
            f"${dl}{GCC}$? {REASON}" if ctx.rng.random() < 0.5 else
            f"A solid {mat} ball (density ${d}{GCC}$) is dropped into a tank of {liq} (density ${dl}{GCC}$). Does it "
            f"float or sink? {REASON}")
    return W(lead, f"It {'floats' if floats else 'sinks'}. An object floats in a liquid that is denser than it and "
                   f"sinks in one that is less dense, and {mat} is {'less' if floats else 'more'} dense than {liq}.")


DEPTH = [
    ("Why is a dam built much thicker at the bottom than at the top?",
     "Water pressure increases with depth, so the water pushes hardest on the bottom of the dam. The dam has to be "
     "strongest there."),
    ("Why do your ears hurt when you swim to the bottom of a deep pool?",
     "The pressure of the water increases with depth, so near the bottom it pushes hard on your eardrums, harder than "
     "the air inside your ears pushes back."),
    ("A tall plastic bottle full of water has small holes at three heights. Why does water spurt out farthest from "
     "the lowest hole?",
     "The water pressure is greatest at the lowest hole, because the most water is above it, so the water is pushed "
     "out fastest there."),
    ("Why must a submarine's hull be stronger to dive deeper?",
     "Water pressure grows with depth, so the deeper the submarine goes, the harder the water pushes in on every part "
     "of its hull."),
    ("Why are city water towers built high above the houses they serve?",
     "The water pressure at a tap depends on how far the water level is above it. A high tower puts the water far "
     "above the houses, so it arrives with plenty of pressure."),
    ("A tall, thin tube and a wide tank are filled with water to the same depth. How does the pressure at the bottom "
     "of the tube compare with the pressure at the bottom of the tank?",
     "It is the same. Pressure in a liquid depends only on the depth and the liquid's density, not on the shape of "
     "the container or how much liquid it holds."),
    ("Why does an IV bag of fluid hang high above a hospital patient?",
     "The higher the bag, the deeper the column of fluid above the needle, so the greater the pressure pushing the "
     "fluid into the vein."),
    ("Why are the walls of a large aquarium tank thickest near the bottom?",
     "The water pressure is greatest at the bottom of the tank, because it is deepest there, so the walls need the "
     "most strength there."),
    ("A scuba diver feels the water pressure increase as she swims down, but not as she swims sideways at the same "
     "depth. Explain why.",
     "Water pressure depends on depth. Swimming sideways keeps her at the same depth, so the pressure stays the same; "
     "swimming down puts more water above her, so the pressure rises."),
    ("Why is a deep swimming pool built with thicker walls at the bottom of the deep end?",
     "The pressure of the water increases with depth, so the water pushes hardest at the bottom of the deep end, and "
     "the walls must be strongest there."),
    ("Why does water come out of a ground-floor tap with more force than a tap on the top floor of the same "
     "building?",
     "The ground-floor tap is farther below the water level in the tank or tower, so there is more depth of water "
     "above it and the pressure is greater."),
    ("Divers who go very deep need special training and equipment, while snorkelers near the surface don't. "
     "Explain why.",
     "Water pressure increases steadily with depth, so deep divers face much greater pressure on their bodies and in "
     "the air they breathe, while near the surface the extra pressure is small."),
]


@variant("concept_fluids", 2, "Pressure and depth")
@variant("concept_fluids", 3, "Pressure and depth")
def _depth(ctx: Ctx) -> Problem:
    q, a = pick(ctx, DEPTH)
    return W(q if not q.endswith("?") or q.startswith("Why") else f"{q} {REASON}", a)


BUOYANCY = [
    ("A steel ship floats even though steel is much denser than water. Explain how.",
     "The hull is shaped to push aside a large volume of water. The buoyant force equals the weight of the water "
     "pushed aside, and the ship sinks just until that weight equals its own weight."),
    ("A boat floats higher in salt water than in fresh water. Explain why.",
     "Salt water is denser, so a smaller volume of it weighs as much as the boat. The boat needs to push aside less "
     "water to get enough buoyant force, so it rides higher."),
    ("About nine tenths of an iceberg is under water. Explain why it floats, and why so much of it is submerged.",
     "Ice is slightly less dense than sea water, so it floats. It must push aside its own weight of water, and since "
     "ice is about nine tenths as dense, about nine tenths of it has to be under water."),
    ("A rock feels lighter when you lift it under water. Explain why.",
     "The water pushes up on the rock with a buoyant force equal to the weight of the water the rock pushes aside. "
     "That upward push supports part of the rock's weight, so you need less force to lift it."),
    ("A helium balloon rises in air. Explain why, using the idea of buoyancy.",
     "The balloon pushes aside air that weighs more than the balloon and its helium. The buoyant force from the air "
     "is bigger than the balloon's weight, so the net force is upward."),
    ("A submarine dives by letting sea water into its ballast tanks. Explain how this makes it sink.",
     "The water in the tanks makes the submarine heavier without changing its volume, so its weight becomes greater "
     "than the buoyant force and it sinks. Pumping the water out makes it rise."),
    ("It is easier to float in the very salty Dead Sea than in a swimming pool. Explain why.",
     "The salty water is much denser, so the water a swimmer pushes aside weighs more. The buoyant force is larger, "
     "and the swimmer floats with more of the body above the surface."),
    ("A ball of clay sinks, but the same clay shaped into a bowl floats. Explain why.",
     "As a bowl, the clay pushes aside much more water. The buoyant force equals the weight of that water, which is "
     "now enough to balance the clay's weight; the solid ball pushes aside too little."),
    ("A hot-air balloon rises when the air inside it is heated. Explain why.",
     "Heated air expands and becomes less dense, so the balloon's air weighs less than the cooler air it pushes "
     "aside. The buoyant force then exceeds the weight of the balloon and its load."),
    ("A fish can rise or sink by changing the amount of gas in its swim bladder. Explain how.",
     "More gas makes the fish's body take up more volume without adding much weight, so it pushes aside more water "
     "and the buoyant force grows. Less gas does the opposite."),
    ("A life jacket helps a swimmer float. Explain how.",
     "The jacket adds a lot of volume but very little weight, so the swimmer and jacket together push aside more "
     "water. The extra buoyant force holds the swimmer's head above the surface."),
    ("An empty, sealed soda can floats in water, but a full one sinks. Explain why.",
     "Both push aside the same volume of water when under it, so they get the same buoyant force. The empty can "
     "weighs less than that force and floats; the full can weighs more and sinks."),
]


@variant("concept_fluids", 3, "Buoyancy")
def _buoyancy(ctx: Ctx) -> Problem:
    return W(*pick(ctx, BUOYANCY))


what_if("concept_fluids", [
    Law("pressure", "Pressure", "large",
        [V("F", "the force pressing down", "the force", F(1)), V("A", "the area in contact", "the contact area", F(-1))],
        [("A hiker stands on soft snow.", "the pressure on the snow"),
         ("A carpenter pushes a thumbtack into a board.", "the pressure on the board"),
         ("A crate rests on a wooden floor.", "the pressure on the floor"),
         ("An elephant stands on soft ground.", "the pressure on the ground")]),
    Law("depth", "The pressure from a liquid", "large",
        [V("h", "the depth", "the depth", F(1)), V(r"\rho", "the density of the liquid", "the density", F(1))],
        [("A diver swims down into a lake. Count only the pressure from the water, not the air above it.",
          "the water pressure on the diver"),
         ("A submarine dives in the ocean. Count only the pressure from the water, not the air above it.",
          "the water pressure on the hull"),
         ("A tall tank is filled with liquid. Count only the pressure from the liquid, not the air above it.",
          "the pressure at the bottom of the tank")]),
    Law("buoyant", "The buoyant force", "large",
        [V("V", "the volume of liquid it pushes aside", "the volume pushed aside", F(1)),
         V(r"\rho", "the density of the liquid", "the density", F(1))],
        [("A beach ball is held under the water in a pool.", "the buoyant force on the ball"),
         ("A diver holds a sealed jar under water.", "the buoyant force on the jar"),
         ("A block hangs from a spring scale, completely under water.", "the buoyant force on the block")]),
])


# =================================================================== heat

C("concept_heat", "Heat", "Heat and temperature concepts",
  "conduction, convection and radiation, specific heat, phase changes, thermal energy, expansion, "
  "and what happens if…")

TRANSFERS = [
    ("A metal spoon left in a pot of hot soup gets hot all the way up the handle.", "conduction",
     "Heat passes along the solid spoon by direct contact, as fast-moving particles bump into their neighbors."),
    ("You warm your hands in front of a campfire.", "radiation",
     "The fire gives off infrared radiation that travels through the air and is absorbed by your skin."),
    ("A heater near the floor warms the air near the ceiling first.", "convection",
     "Air warmed by the heater becomes less dense and rises, carrying heat upward, while cooler air sinks to take its "
     "place."),
    ("The Sun warms the Earth across millions of kilometers of empty space.", "radiation",
     "No material is needed: the Sun's energy travels as electromagnetic radiation through the vacuum of space."),
    ("Water at the bottom of a pot on the stove heats up and rises, while cooler water sinks.", "convection",
     "The heated water expands, becomes less dense and rises, so the circulating water carries heat through the pot."),
    ("An ice cube melts in your hand.", "conduction",
     "Heat flows from your warm hand into the ice through direct contact."),
    ("A tile floor feels colder under bare feet than a rug in the same room.", "conduction",
     "Both are at room temperature, but tile conducts heat much better, so it carries heat away from your feet faster "
     "and feels colder."),
    ("On a sunny afternoon a cool breeze blows from the sea onto the warm land.", "convection",
     "Air over the warm land heats up and rises, and cooler air from over the sea flows in to take its place."),
    ("A car's dashboard gets hot when the car sits in the sun.", "radiation",
     "Sunlight passes through the windows and is absorbed by the dark dashboard, which warms up."),
    ("A clothes iron smooths a shirt.", "conduction",
     "The hot metal plate touches the cloth, so heat flows straight into it by direct contact."),
    ("A space heater's glowing coils warm you from across the room.", "radiation",
     "The hot coils give off infrared radiation that crosses the room and is absorbed by your body."),
    ("Smoke and hot air rise up a chimney.", "convection",
     "The hot gases are less dense than the cooler air around them, so they rise, carrying heat with them."),
]


@variant("concept_heat", 1, "Conduction, convection and radiation")
def _transfer(ctx: Ctx) -> Problem:
    scene, mode, why = pick(ctx, TRANSFERS)
    q = (f"{scene} Is this mainly conduction, convection or radiation? {REASON}" if ctx.rng.random() < 0.5
         else f"{scene} Name the main way heat is transferred here, and explain how it works.")
    return W(q, f"Mainly {mode}. {why}")


HEAT_PAIRS = [("water", "sand", ""), ("water", "iron", ""), ("water", "aluminum", ""), ("water", "granite", ""),
              ("water", "concrete", ""),
              ("aluminum", "copper", r"The specific heat of aluminum is $0.90\,\mathrm{J/(g\,^\circ C)}$ and that of "
                                     r"copper is $0.39\,\mathrm{J/(g\,^\circ C)}$."),
              ("water", "cooking oil", r"The specific heat of water is $4.2\,\mathrm{J/(g\,^\circ C)}$ and that of "
                                       r"cooking oil is $2.0\,\mathrm{J/(g\,^\circ C)}$.")]
HEAT_STEMS = ["absorb the same amount of heat", "sit in the same sunlight for an hour",
              "are heated on identical burners for the same time"]
HIGH_C = [("Why does a beach's sand get burning hot on a sunny day while the water stays cool?",
           "Water has a much higher specific heat than sand, so the same sunshine raises the water's temperature much "
           "less. The sand needs less energy per degree, so it heats up quickly."),
          ("Why do cities on the coast usually have milder temperatures than cities far inland?",
           "The ocean's water has a very high specific heat, so it warms and cools slowly, soaking up heat in summer "
           "and giving it back in winter. That keeps the nearby air from getting very hot or very cold."),
          ("Why is water used to carry heat away from a car's engine?",
           "Water has a very high specific heat, so each kilogram can absorb a lot of heat from the engine while its "
           "own temperature rises only a little."),
          ("Why does a hot-water bottle stay warm for so long?",
           "Water has a very high specific heat, so the hot water holds a lot of thermal energy and gives it off "
           "slowly while cooling only a little at a time.")]


@variant("concept_heat", 2, "Specific heat")
def _specific_heat(ctx: Ctx) -> Problem:
    if ctx.rng.random() < 0.2:
        return W(*pick(ctx, HIGH_C))
    high, low, data = pick(ctx, HEAT_PAIRS)
    a, b = (high, low) if ctx.rng.random() < 0.5 else (low, high)
    stem = pick(ctx, HEAT_STEMS)
    return W(f"Equal masses of {a} and {b} {stem}. {data + ' ' if data else ''}Which one's temperature rises more? "
             f"{REASON}",
             f"The {low} warms up more. It has a lower specific heat than {high}, so each gram needs less energy to "
             f"warm by one degree, and the same heat raises its temperature more.")


PHASES = [
    ("Ice at 0 °C is heated steadily. While it melts, its temperature stays at 0 °C. Where does the energy go?",
     "Into melting the ice. The energy breaks the bonds that hold the water molecules in the solid (the latent heat of "
     "melting) instead of making them move faster, so the temperature can't rise until all the ice has melted."),
    ("A pot of water boils on a stove. The burner keeps adding heat, but the water stays at 100 °C. Explain why.",
     "The added energy goes into turning liquid water into steam (the latent heat of vaporization), pulling "
     "molecules apart instead of speeding them up, so the temperature stays at the boiling point."),
    ("A burn from steam at 100 °C is usually worse than a burn from water at 100 °C. Explain why.",
     "When steam touches your skin it condenses, giving up its large latent heat of vaporization, and then the hot "
     "water cools as well. That delivers far more energy than the water alone."),
    ("Sweating helps cool your body on a hot day. Explain how.",
     "As sweat evaporates, the fastest molecules escape, and turning liquid into vapor takes energy. That energy comes "
     "from your skin, so your body cools down."),
    ("Ice cubes cool a drink more than the same mass of ice-cold water would. Explain why.",
     "Before it can warm up, the ice has to melt, and melting absorbs a lot of energy (latent heat) from the drink. "
     "Cold water can only absorb heat by warming up."),
    ("Farmers sometimes spray their fruit trees with water on nights when frost is expected. Explain how this "
     "protects the fruit.",
     "As the water freezes on the fruit it gives off its latent heat of freezing, which keeps the fruit at about "
     "0 °C instead of letting it get colder and freeze."),
    ("Rubbing alcohol feels cold on your skin, even when it is at room temperature. Explain why.",
     "The alcohol evaporates quickly, and evaporating takes energy. It draws that energy from your skin, which cools "
     "down."),
    ("A refrigerator cools its inside by letting a special liquid evaporate in coils inside it. Explain why "
     "evaporation cools the inside.",
     "Turning the liquid into gas takes energy (latent heat). The liquid absorbs that energy from the inside of the "
     "fridge as it evaporates, so the inside cools."),
    ("Dew forms on grass on a cool morning. Where does the water come from, and does the air gain or lose heat as "
     "it forms?",
     "Water vapor in the air condenses on the cold grass. Condensing releases latent heat, so the vapor gives off "
     "heat to its surroundings as the dew forms."),
    ("You feel chilly stepping out of a swimming pool on a breezy day, even when the air is warm. Explain why.",
     "The water on your skin evaporates quickly in the breeze, and evaporation takes energy. It takes that energy "
     "from your body, so you cool down."),
    ("A glass of ice water stays at about 0 °C until all the ice has melted. Explain why.",
     "Heat from the room goes into melting the ice rather than warming the water. As long as there is ice left to "
     "melt, the mixture stays at the melting point."),
    ("A pot of soup takes much longer to boil away than it takes to heat up to boiling. Explain why.",
     "Turning water into steam takes far more energy per gram (the latent heat of vaporization) than warming it to "
     "the boiling point, so the stove needs much longer to supply it."),
]


@variant("concept_heat", 2, "Phase changes")
@variant("concept_heat", 3, "Phase changes")
def _phase(ctx: Ctx) -> Problem:
    return W(*pick(ctx, PHASES))


THERMAL_PAIRS = [("a bathtub full of warm water", "a cup of boiling water"),
                 ("a swimming pool at 25 °C", "a cup of hot tea"), ("an iceberg", "a cup of hot coffee"),
                 ("a large lake on a summer day", "a pot of boiling soup"),
                 ("a warm room full of air", "a lit match")]


@variant("concept_heat", 3, "Temperature vs. thermal energy")
def _thermal(ctx: Ctx) -> Problem:
    if ctx.rng.random() < 0.15:
        return W("The sparks from a sparkler are over 1000 °C, but they don't burn your hand. Explain why.",
                 "Each spark is tiny, so even at a very high temperature it holds very little thermal energy. It "
                 "cools before it can deliver enough energy to burn your skin.")
    big, hot = pick(ctx, THERMAL_PAIRS)
    if ctx.rng.random() < 0.5:
        return W(f"Compare {big} and {hot}. Which has the higher temperature, and which has more thermal energy? "
                 f"{REASON}",
                 f"{cap(hot)} has the higher temperature, but {big} has more thermal energy. Temperature measures the "
                 f"average energy of the particles, while thermal energy is the total for all of them, and {big} has "
                 f"vastly more particles.")
    return W(f"A student says that {hot} has more thermal energy than {big} because it is hotter. Do you agree? "
             f"{REASON}",
             f"No. {cap(hot)} has the higher temperature, which means its particles have more energy on average. But "
             f"thermal energy is the total energy of all the particles, and {big} has so many more that its total is "
             f"far greater.")


EXPANSION = [
    ("A tight metal lid on a glass jar loosens when you run hot water over it. Explain why.",
     "Heating makes the metal lid expand, and metal expands more than glass for the same temperature rise, so the lid "
     "gets slightly bigger than the jar's rim and loosens."),
    ("Bridges have gaps called expansion joints. Explain why they are needed.",
     "The bridge expands on hot days and contracts on cold days. The gaps give it room to change length without "
     "pushing on itself hard enough to buckle or crack."),
    ("Power lines sag more on hot summer days than on cold winter days. Explain why.",
     "The metal wires expand when they warm up, so the same wire is a little longer between the poles and droops "
     "lower."),
    ("Railroad tracks can buckle on very hot days. Explain why.",
     "The steel rails expand as they heat up. If there isn't enough room for the extra length, the rails push against "
     "each other and bend out of line."),
    ("The liquid in a thermometer rises as it warms up. Explain why.",
     "The liquid expands when it is heated, and the narrow tube turns that small change in volume into a large rise "
     "in the liquid's height."),
    ("A thermostat uses a strip of two different metals bonded together, which bends as it warms. Explain why it "
     "bends.",
     "The two metals expand by different amounts for the same temperature change. One side gets longer than the "
     "other, so the strip curls toward the metal that expands less."),
    ("Concrete sidewalks are poured in sections with gaps between them. Explain why.",
     "Concrete expands in summer heat and contracts in winter cold. The gaps give each section room to expand so it "
     "doesn't crack or push up against its neighbors."),
    ("Dentists use filling materials that expand about as much as teeth do when heated. Explain why this matters.",
     "Hot and cold food make teeth and fillings expand and contract. If a filling expanded more or less than the "
     "tooth, the mismatch could crack the tooth or open a gap around the filling."),
    ("A glass dish can crack if it is taken from a hot oven and put straight into cold water. Explain why.",
     "The outside of the glass cools and contracts quickly while the inside is still hot and expanded. The two parts "
     "pull against each other, and the strain can crack the glass."),
    ("A balloon left in a hot car gets bigger. Explain why.",
     "The air inside warms up, and heated gas expands: its particles move faster and push harder on the inside of the "
     "balloon, stretching it."),
]


@variant("concept_heat", 3, "Thermal expansion")
def _expansion(ctx: Ctx) -> Problem:
    return W(*pick(ctx, EXPANSION))


what_if("concept_heat", [
    Law("heat", "The heat needed", "large",
        [V("m", "the mass being heated", "the mass", F(1)),
         V(r"\Delta T", "the temperature rise", "the temperature rise", F(1))],
        [("A kettle heats water for tea.", "the heat the kettle must supply"),
         ("A pot of soup is warmed on the stove.", "the heat the stove must supply"),
         ("A heater warms a swimming pool.", "the heat the heater must supply"),
         ("A microwave warms a mug of milk.", "the energy the microwave must supply")]),
    Law("warming", "The temperature rise", "large",
        [V("Q", "the heat added", "the heat added", F(1)), V("m", "the mass being heated", "the mass", F(-1)),
         V("c", "the specific heat of the material", "the specific heat", F(-1))],
        [("A burner heats a pot of water.", "the water's temperature rise"),
         ("Sunlight warms a patch of sand.", "the sand's temperature rise"),
         ("A heater warms a block of metal.", "the block's temperature rise")]),
])


# =================================================================== oscillations

C("concept_oscillations", "Oscillations", "Pendulum and spring concepts",
  "speed and energy in a swing, what sets a pendulum's period, and what happens if…")

SWINGERS = [("A child swings back and forth on a playground swing.", "the swing", "pendulum"),
            ("A grandfather clock's pendulum swings back and forth.", "the pendulum bob", "pendulum"),
            ("A wrecking ball swings from a crane.", "the wrecking ball", "pendulum"),
            ("A lantern on a long chain sways back and forth.", "the lantern", "pendulum"),
            ("A kid on a rope swing swings out over a lake and back.", "the kid", "pendulum"),
            ("A tire swing hanging from a tree branch swings back and forth.", "the tire", "pendulum"),
            ("A mass hangs from a spring and bounces up and down.", "the mass", "spring"),
            ("A block on a frictionless table is attached to a spring and slides back and forth.", "the block",
             "spring"),
            ("A toy bobs up and down on the end of a spring.", "the toy", "spring"),
            ("A car bounces up and down on its springs after going over a bump.", "the car", "spring")]


@variant("concept_oscillations", 1, "Speed and energy in a swing")
def _swing_speed(ctx: Ctx) -> Problem:
    setup, obj, kind = pick(ctx, SWINGERS)
    pend = kind == "pendulum"
    if ctx.rng.random() < 0.5:
        q = f"{setup} Ignore friction. Where is {obj} moving fastest, and where is it momentarily at rest? {REASON}"
    else:
        q = f"{setup} Ignore friction. Describe how the speed of {obj} changes during one full back-and-forth."
    if pend:
        a = (f"{cap(obj)} moves fastest at the bottom of the swing, where it has turned the most potential energy into "
             f"kinetic energy. It is momentarily at rest at each end, where it is highest, stops and turns around.")
    else:
        a = (f"{cap(obj)} moves fastest as it passes through the middle (its rest position), where the spring's stored "
             f"energy has all become kinetic energy. It is momentarily at rest at the two ends, where the spring is "
             f"stretched or squeezed the most.")
    return W(q, a)


@variant("concept_oscillations", 3, "Speed and energy in a swing")
def _swing_force(ctx: Ctx) -> Problem:
    setup, obj, kind = pick(ctx, SWINGERS)
    pend = kind == "pendulum"
    if ctx.rng.random() < 0.5:
        if pend:
            return W(f"{setup} Ignore friction. Where is the force pulling {obj} back toward the bottom of its swing "
                     f"greatest, and where is it zero? {REASON}",
                     f"It is greatest at the ends of the swing, where {obj} is farthest from the bottom and the part of "
                     f"gravity pulling it back is largest. At the bottom that pull back is zero, so {obj} stops "
                     f"speeding up there.")
        return W(f"{setup} Ignore friction. Where is the acceleration of {obj} greatest, and where is it zero? {REASON}",
                 f"It is greatest at the ends, where the spring is stretched or squeezed the most and pushes or pulls "
                 f"hardest. At the middle (the rest position) the spring's net force is zero, so the acceleration is "
                 f"zero there.")
    if pend:
        return W(f"{setup} Ignore friction. Where does {obj} have the most potential energy, and where does it have the "
                 f"most kinetic energy? {REASON}",
                 f"Most potential energy at the ends of the swing, where it is highest; most kinetic energy at the "
                 f"bottom, where it is fastest. The total stays the same, and energy keeps changing back and forth "
                 f"between the two forms.")
    return W(f"{setup} Ignore friction. Where is the energy stored in the spring greatest, and where does {obj} have "
             f"the most kinetic energy? {REASON}",
             f"The stored energy is greatest at the ends, where the spring is stretched or squeezed the most; the "
             f"kinetic energy is greatest at the middle, where {obj} moves fastest. The total stays the same as energy "
             f"changes back and forth between the two forms.")


CLOCKS = ["grandfather clock", "wall clock", "mantel clock"]
WEAKER = [("the Moon", "weaker"), ("Mars", "weaker"), ("a planet where gravity is stronger than on Earth", "stronger")]


@variant("concept_oscillations", 2, "What sets a pendulum's period")
def _pendulum(ctx: Ctx) -> Problem:
    kind = ctx.rng.randrange(4)
    clock = pick(ctx, CLOCKS)
    if kind == 0:
        slow = ctx.rng.random() < 0.5
        return W(f"A pendulum {clock} runs {'slow' if slow else 'fast'}. Should its pendulum be made shorter or "
                 f"longer to fix it? {REASON}",
                 f"{'Shorter' if slow else 'Longer'}. A {'shorter' if slow else 'longer'} pendulum has a "
                 f"{'shorter' if slow else 'longer'} period, so it swings {'faster' if slow else 'more slowly'} and the "
                 f"clock {'speeds up' if slow else 'slows down'}.")
    if kind == 1:
        place, gravity = pick(ctx, WEAKER)
        slower = gravity == "weaker"
        return W(f"A pendulum {clock} that keeps perfect time on Earth is taken to {place}. Will it run fast or slow "
                 f"there? {REASON}",
                 f"It will run {'slow' if slower else 'fast'}. Gravity there is {gravity}, so it pulls the pendulum "
                 f"back {'less' if slower else 'more'} strongly, and the period gets {'longer' if slower else 'shorter'}.")
    if kind == 2:
        ratio = pick(ctx, ["twice", "three times"])
        return W(f"Two pendulums have the same length, but one bob is {ratio} as heavy as the other. How do their "
                 f"periods compare? {REASON}",
                 f"Their periods are the same. A pendulum's period depends on its length and on gravity, not on the "
                 f"mass of the bob: the heavier bob needs more force to speed up, but gravity pulls on it {ratio} as "
                 f"hard.")
    who = pick(ctx, ["an adult", "a large dog", "a heavy backpack"])
    return W(f"A child swings on a playground swing, then {who} sits on the same swing and swings the same way. How "
             f"does the period of the swing change? {REASON}",
             f"It stays the same. Like any pendulum, the swing's period depends on the length of its chains and on "
             f"gravity, not on how heavy the load is.")


what_if("concept_oscillations", [
    Law("hooke", "The stretch of a spring", "great",
        [V("F", "the weight hung on it", "the weight", F(1)),
         V("k", "the stiffness of the spring", "the spring's stiffness", F(-1))],
        [("A weight hangs from a spring.", "the spring's stretch"),
         ("A fish hangs from a spring scale.", "the stretch of the scale's spring"),
         ("A bag of apples hangs from a produce scale with a spring inside.", "the stretch of the scale's spring")]),
    Law("pendulum", "A pendulum's period", "long",
        [V("L", "its length", "the length", F(1, 2)),
         V("g", "the strength of gravity", "the strength of gravity", F(-1, 2)),
         V("m", "the mass of the swinging object", "the mass", F(0),
           "A pendulum's period depends only on its length and on gravity, not on the mass: a heavier object needs more "
           "force to speed up, but gravity pulls on it harder by the same factor.")],
        [("A pendulum swings in a grandfather clock.", "its period"),
         ("A child swings on a playground swing.", "the swing's period"),
         ("A wrecking ball swings from a crane.", "the wrecking ball's period"),
         ("A lantern swings from a long chain.", "the lantern's period")]),
    Law("spring_period", "The period of a mass on a spring", "long",
        [V("m", "the mass on the spring", "the mass", F(1, 2)),
         V("k", "the stiffness of the spring", "the spring's stiffness", F(-1, 2)),
         V("A", "the amplitude (how far it is pulled before release)", "the amplitude", F(0),
           "For an ideal spring the period doesn't depend on the amplitude: a bigger stretch makes a bigger restoring "
           "force, so the mass moves faster and covers the longer path in the same time.")],
        [("A mass bounces up and down on a spring.", "its period"),
         ("A toy bobs on the end of a spring.", "the toy's period"),
         ("A block slides back and forth on a spring across a frictionless table.", "the block's period")]),
])


# =================================================================== waves & sound

C("concept_waves", "Waves & sound", "Wave and sound concepts",
  "kinds of waves, pitch and loudness, what sound travels through, the Doppler effect, and what happens if…")

WAVE_KINDS = [
    ("sound traveling through air", "longitudinal",
     "The air molecules vibrate back and forth along the direction the sound travels, making compressions and "
     "rarefactions."),
    ("a wave on a plucked guitar string", "transverse",
     "The string moves up and down, at right angles to the direction the wave travels along it."),
    ("a stadium wave, where fans stand up and sit down in turn", "transverse",
     "Each fan moves up and down while the wave travels sideways around the stadium."),
    ("a pulse made by pushing and pulling one end of a stretched Slinky along its length", "longitudinal",
     "The coils move back and forth along the Slinky, in the same direction the pulse travels."),
    ("a wave made by shaking one end of a rope up and down", "transverse",
     "Each bit of rope moves up and down, at right angles to the direction the wave travels along the rope."),
    ("light", "transverse",
     "Light is an electromagnetic wave: its electric and magnetic fields vibrate at right angles to the direction it "
     "travels."),
    ("an earthquake's P wave (primary wave)", "longitudinal",
     "The rock is squeezed and stretched along the direction the wave travels."),
    ("an earthquake's S wave (secondary wave)", "transverse",
     "The rock is shaken side to side, at right angles to the direction the wave travels."),
    ("the ultrasound used to image a baby before birth", "longitudinal",
     "Ultrasound is sound, so the tissue vibrates back and forth along the direction the wave travels."),
    ("a radio wave", "transverse",
     "A radio wave is an electromagnetic wave, like light, so its fields vibrate at right angles to its direction."),
]


@variant("concept_waves", 1, "Kinds of waves")
def _wave_kind(ctx: Ctx) -> Problem:
    wave, kind, why = pick(ctx, WAVE_KINDS)
    q = (f"Is {wave} a transverse wave or a longitudinal wave? {REASON}" if ctx.rng.random() < 0.5
         else f"Classify {wave} as transverse or longitudinal, and describe the vibration that makes it so.")
    return W(q, f"It is {kind}. {why}")


SOUNDS = [
    ("A guitarist plucks the same string harder.", "amplitude",
     "It gets louder, but the pitch stays the same. Plucking harder makes the string vibrate with a larger amplitude, "
     "and loudness depends on amplitude; the pitch depends on frequency, which doesn't change."),
    ("A guitarist presses a string against a fret, so a shorter part of it vibrates.", "frequency",
     "The pitch goes up. A shorter string vibrates faster, so the frequency increases, and we hear a higher frequency "
     "as a higher pitch."),
    ("A singer moves from a low note to a high note at the same volume.", "frequency",
     "The pitch rises while the loudness stays the same. The singer's vocal cords vibrate faster, raising the "
     "frequency of the sound."),
    ("You turn up the volume on a speaker playing a steady tone.", "amplitude",
     "It gets louder at the same pitch. The speaker cone moves farther back and forth, so the sound wave's amplitude "
     "increases while its frequency stays the same."),
    ("A drummer tightens the skin of a drum.", "frequency",
     "The pitch goes up. A tighter drum skin vibrates faster, so the sound has a higher frequency."),
    ("You pour more water into a glass bottle and blow across the top.", "frequency",
     "The pitch goes up. The column of air above the water gets shorter, and a shorter air column vibrates at a higher "
     "frequency."),
    ("A violinist draws the bow more gently across the same string.", "amplitude",
     "It gets quieter at the same pitch. A gentler bow makes the string vibrate with a smaller amplitude; the "
     "frequency, and so the pitch, doesn't change."),
    ("A tuning fork is struck harder.", "amplitude",
     "It gets louder, but the pitch stays the same. Striking harder gives the prongs a larger amplitude; a tuning "
     "fork always vibrates at its own frequency."),
    ("A guitarist tightens a tuning peg, stretching a string tighter.", "frequency",
     "The pitch goes up. A tighter string vibrates faster, so the frequency of the sound increases."),
]


@variant("concept_waves", 1, "Pitch and loudness")
@variant("concept_waves", 2, "Pitch and loudness")
def _pitch(ctx: Ctx) -> Problem:
    scene, prop, answer = pick(ctx, SOUNDS)
    if ctx.rng.random() < 0.5:
        return W(f"{scene} How does the sound change, in pitch and in loudness? {REASON}", answer)
    return W(f"{scene} Which property of the sound wave changes: its frequency or its amplitude? {REASON}",
             f"Its {prop}. {answer}")


MEDIUM = [
    ("In many science-fiction movies, explosions in space make a loud boom. Is that realistic? Explain.",
     "No. Sound is a vibration that has to travel through a material such as air. Space is nearly empty, so there is "
     "nothing to carry the sound, and the explosion would be silent."),
    ("An alarm clock rings inside a sealed glass jar. As the air is pumped out of the jar, the ringing fades even "
     "though the clapper keeps moving. Explain why.",
     "Sound needs a material to travel through. As the air is removed, there is less and less to carry the "
     "vibrations from the bell to the glass and out to your ears."),
    ("Astronauts on a spacewalk talk to each other by radio, even when they are close together. Explain why.",
     "There is no air in space to carry sound waves between them. Radio waves are electromagnetic waves, which can "
     "travel through empty space."),
    ("You can see the Sun but can't hear the huge explosions on its surface. Explain why.",
     "Light can travel through the empty space between the Sun and Earth, but sound needs a material to travel "
     "through, so the sound can't cross the vacuum."),
    ("You can hear a friend tapping on the other side of a wooden door. What carries the sound to you?",
     "The tapping makes the wood vibrate, and the vibrations travel through the solid door and then through the air "
     "to your ears. Sound can travel through solids, liquids and gases."),
    ("Whales can hear each other's calls across hundreds of kilometers of ocean. What carries the sound, and why "
     "does it travel so well?",
     "The water carries it. Sound travels well through water, faster than through air, and in the ocean it can "
     "travel very long distances without fading much."),
    ("If you put your ear to a railroad track, you can hear a distant train before you hear it through the air. "
     "Explain why.",
     "Sound travels much faster through solid steel than through air, so the vibrations in the rail reach you "
     "first."),
    ("On the Moon, two astronauts can hear each other faintly by touching their helmets together. Explain how.",
     "There is no air on the Moon to carry sound, but sound can travel through solids, so the vibrations pass from "
     "one helmet into the other."),
    ("A doctor listens to your heart through a stethoscope. What carries the sound to the doctor's ears?",
     "Your heartbeat makes the chest piece vibrate, and the sound travels through the air inside the tubes to the "
     "doctor's ears. The tubes keep the sound from spreading out and fading."),
    ("Double-pane windows, with a thin gap between the two sheets of glass, block traffic noise well. Explain why.",
     "Sound passes poorly from glass into the thin layer of gas and back into glass, and the gap carries little "
     "vibration across, so much less sound gets through than through a single solid pane."),
    ("Your own voice sounds different when you hear a recording of it. Explain why.",
     "When you speak, you hear your voice partly through the bones of your head, which carry the low sounds well. "
     "A recording reaches you only through the air, so it sounds different."),
    ("You can hear music from a car's stereo through its closed windows. Explain how the sound gets out.",
     "The sound makes the car's windows and body vibrate, and those vibrations then pass into the air outside. Sound "
     "travels through the solid glass and metal as well as through the air."),
]


@variant("concept_waves", 2, "What sound travels through")
@variant("concept_waves", 3, "What sound travels through")
def _medium(ctx: Ctx) -> Problem:
    return W(*pick(ctx, MEDIUM))


SIRENS = [("an ambulance with its siren on", "siren"), ("a fire truck sounding its siren", "siren"),
          ("a train blowing its horn", "horn"), ("a race car", "engine"), ("a police car with its siren on", "siren"),
          ("a motorcycle", "engine")]
BELLS = ["the bell at a railroad crossing", "a factory whistle", "a church bell", "a fire alarm on a building"]


@variant("concept_waves", 3, "The Doppler effect")
def _doppler(ctx: Ctx) -> Problem:
    kind = ctx.rng.randrange(3)
    if kind < 2:
        source, sound = pick(ctx, SIRENS)
        if kind == 0:
            return W(f"You stand beside the road as {source} approaches, passes you and moves away. Describe how the "
                     f"pitch you hear changes, and explain why.",
                     f"The pitch of the {sound} sounds higher as it approaches and drops lower after it passes. Moving "
                     f"toward you, the source bunches its sound waves together, so more waves reach you each second "
                     f"(a higher frequency); moving away, it spreads them out (the Doppler effect).")
        return W(f"{cap(source)} passes you. Does its driver hear the pitch of the {sound} change? {REASON}",
                 f"No. The driver moves along with the {sound}, so its sound waves reach the driver at the frequency "
                 f"they are made. The change in pitch is heard only by listeners the source moves toward or away from.")
    bell = pick(ctx, BELLS)
    return W(f"You ride in a car that speeds past {bell} while it is sounding. How does the pitch you hear change? "
             f"{REASON}",
             f"It sounds higher as you approach and lower after you pass. Moving toward the sound, you meet its waves "
             f"more often each second, a higher frequency; moving away, you meet them less often (the Doppler effect).")


what_if("concept_waves", [
    Law("wavelength", "The wavelength", "long",
        [V("f", "the frequency", "the frequency", F(-1)), V("v", "the wave speed", "the wave speed", F(1))],
        [("A student shakes one end of a long rope to send waves along it.", "the wavelength of the waves"),
         ("A speaker plays a steady note.", "the wavelength of the sound"),
         ("A wave machine makes ripples in a tank of water.", "the wavelength of the ripples")]),
    Law("wave_speed", "The wave speed", "fast",
        [V("f", "the frequency of the source", "the frequency", F(0),
           "The speed of a wave is set by the material it travels through, not by its source. Changing the frequency "
           "changes the wavelength instead.")],
        [("A speaker plays a note in a quiet room.", "the speed of the sound"),
         ("A student shakes one end of a long rope.", "the speed of the waves along the rope")]),
    Law("loudness", "The sound intensity", "intense",
        [V("P", "the power of the source", "the power", F(1)),
         V("r", "your distance from the source", "the distance", F(-2))],
        [("You stand near a speaker at an outdoor concert.", "the sound intensity where you stand"),
         ("A siren sounds from the top of a pole in an open field.", "the sound intensity you hear")]),
])


# =================================================================== electricity

C("concept_electricity", "Electricity", "Electricity concepts",
  "electric charge, conductors and insulators, series and parallel circuits, and what happens if…")

CHARGES = [
    ("After you rub a balloon on your hair, your hair is pulled toward the balloon.",
     "Rubbing moves electrons from your hair onto the balloon, so the balloon becomes negatively charged and your hair "
     "positively charged. Opposite charges attract."),
    ("Two balloons that have both been rubbed on your hair push each other away.",
     "Both balloons picked up extra electrons, so they have the same kind of charge (negative), and like charges "
     "repel."),
    ("A balloon rubbed on your hair sticks to a wall that has no charge.",
     "The charged balloon pushes the electrons in the wall's surface slightly away, leaving the nearby surface "
     "slightly positive. That nearby opposite charge attracts the balloon more than the farther charge repels it."),
    ("You get a small shock when you touch a metal doorknob after shuffling across a carpet.",
     "Shuffling transfers electrons between your shoes and the carpet, so your body builds up a charge. When your "
     "hand nears the metal, the charge jumps across the gap as a spark."),
    ("A plastic comb that has been run through dry hair picks up small bits of paper.",
     "Combing charges the comb. Near the paper, it pulls the paper's opposite charges slightly closer and pushes the "
     "like charges away, so the paper is attracted to the comb."),
    ("Clothes cling together when they come out of a dryer.",
     "Tumbling rubs the fabrics together and moves electrons between them, so some clothes end up positively charged "
     "and some negatively charged. Opposite charges attract."),
    ("A charged plastic rod held near a thin stream of tap water makes the stream bend toward it.",
     "Water molecules have a positive end and a negative end. The rod pulls their opposite ends toward it more "
     "strongly than it pushes the like ends away, so the stream bends toward the rod."),
    ("Plastic wrap clings to a bowl after it is pulled off its roll.",
     "Pulling the wrap off the roll separates charges, so the wrap becomes charged. It then attracts the bowl by "
     "pulling opposite charges in the bowl's surface toward it."),
    ("A glass rod rubbed with silk and a plastic rod rubbed with wool pull toward each other.",
     "Rubbing leaves the glass rod positively charged and the plastic rod negatively charged, and opposite charges "
     "attract."),
    ("Lightning flashes between a storm cloud and the ground.",
     "Inside the storm cloud, charges separate, leaving a large negative charge near the cloud's base. When enough "
     "charge builds up, it jumps through the air to the ground as a giant spark."),
]


@variant("concept_electricity", 1, "Electric charge")
@variant("concept_electricity", 3, "Electric charge")
def _charge(ctx: Ctx) -> Problem:
    scene, answer = pick(ctx, CHARGES)
    q = f"{scene} Explain why." if ctx.rng.random() < 0.5 else f"{scene} Explain this using the idea of electric charge."
    return W(q, answer)


CONDUCTORS = ["copper", "aluminum", "steel", "silver", "gold", "salt water", "graphite"]
INSULATORS = ["rubber", "glass", "plastic", "dry wood", "air", "ceramic", "cotton cloth"]
WIRING = [
    ("Electrical wires are made of copper covered in plastic. Explain why each material is used.",
     "Copper is a good conductor, so current flows easily through the wire. Plastic is an insulator, so the current "
     "stays inside the wire and can't flow into your hand or into other wires."),
    ("Electricians use screwdrivers with rubber or plastic handles. Explain why.",
     "Rubber and plastic are insulators, so if the metal tip touches a live wire, current can't flow through the "
     "handle into the electrician's hand."),
    ("Power lines are held up by glass or ceramic insulators on the poles. Explain why.",
     "Glass and ceramic don't conduct, so current can't leak from the wires into the poles and the ground."),
    ("It is dangerous to use a metal ladder near overhead power lines. Explain why.",
     "Metal is a good conductor. If the ladder touches a line, current can flow through the ladder and through the "
     "person holding it to the ground."),
    ("A lightning rod is a metal rod connected to the ground by a thick wire. Explain how it protects a building.",
     "Metal is a good conductor, so if lightning strikes, the charge flows safely through the rod and wire into the "
     "ground instead of through the building."),
    ("Workers who handle live wires wear thick rubber gloves. Explain why.",
     "Rubber is an insulator, so it keeps current from flowing from the wire through the worker's hands and body."),
]


@variant("concept_electricity", 1, "Conductors and insulators")
@variant("concept_electricity", 2, "Conductors and insulators")
def _conductors(ctx: Ctx) -> Problem:
    if ctx.rng.random() < 0.4:
        return W(*pick(ctx, WIRING))
    cs, ins = ctx.rng.sample(CONDUCTORS, 2), ctx.rng.sample(INSULATORS, 2)
    items = cs + ins
    ctx.rng.shuffle(items)
    return W(f"Sort these into conductors and insulators: {', '.join(items[:3])} and {items[3]}. What makes a "
             f"material a good conductor?",
             f"Conductors: {cs[0]} and {cs[1]}. Insulators: {ins[0]} and {ins[1]}. A conductor has charges that are "
             f"free to move through it (electrons in metals, ions in salt water); in an insulator the charges are held "
             f"in place.")


COUNTS = {2: "Two", 3: "Three", 4: "Four"}
HOUSE = [
    ("Why are the outlets in a house wired in parallel rather than in series?",
     "In parallel, each outlet has its own path to the supply, so every appliance gets the full voltage and can be "
     "switched on or off without affecting the others. In series, unplugging one would cut off all of them."),
    ("Old strings of holiday lights went completely dark when a single bulb burned out. How were the bulbs connected? "
     "Explain.",
     "In series. A series circuit has only one path for the current, so one broken bulb breaks the whole path and "
     "every bulb goes out."),
    ("A car's two headlights are wired so that one can burn out while the other stays lit. How are they connected? "
     "Explain.",
     "In parallel. Each headlight has its own path to the battery, so a break in one path doesn't stop the current "
     "in the other."),
]


@variant("concept_electricity", 2, "Series and parallel circuits")
def _series_parallel(ctx: Ctx) -> Problem:
    if ctx.rng.random() < 0.15:
        return W(*pick(ctx, HOUSE))
    n, kind = ctx.rng.choice([2, 3, 4]), ctx.rng.choice(["series", "parallel"])
    setup = f"{COUNTS[n]} identical bulbs are connected in {kind} to a battery."
    rest = "The other bulb" if n == 2 else f"The other {n - 1} bulbs"
    ask = ctx.rng.randrange(3)
    if ask == 0:
        q = f"{setup} One bulb burns out. What happens to the other {'bulb' if n == 2 else 'bulbs'}? {REASON}"
    elif ask == 1:
        q = (f"{setup} One bulb is unscrewed. How does the brightness of the remaining "
             f"{'bulb' if n == 2 else 'bulbs'} change? {REASON}")
    else:
        q = f"{setup} How does the current through each bulb compare with the current from the battery? {REASON}"
    if ask == 2:
        a = ("It is the same. In series there is only one path, so the same current flows through the battery and "
             "every bulb." if kind == "series" else
             f"Each bulb carries 1/{n} of the battery's current. In parallel the battery current splits among the "
             f"{n} identical paths, so the battery supplies the total.")
        a = a.replace(f"1/{n}", f"$\\frac{{1}}{{{n}}}$")
    elif kind == "series":
        a = (f"{rest} go{'es' if n == 2 else ''} out. In a series circuit there is only one path for the current, so a "
             f"break anywhere stops the current through every bulb.")
    else:
        a = (f"{rest} stay{'s' if n == 2 else ''} lit at the same brightness. In a parallel circuit each bulb has its "
             f"own path to the battery, so a break in one path doesn't stop the current in the others.")
    return W(q, a)


@variant("concept_electricity", 3, "Adding bulbs")
def _adding(ctx: Ctx) -> Problem:
    n, kind = ctx.rng.choice([1, 2, 3, 4]), ctx.rng.choice(["series", "parallel"])
    setup = ("A single bulb is connected to a battery." if n == 1 else
             f"{COUNTS[n]} identical bulbs are connected in {kind} to a battery.")
    added = f"Another identical bulb is added in {kind}."
    if ctx.rng.random() < 0.5:
        q = f"{setup} {added} What happens to the brightness of each bulb and to the current from the battery? {REASON}"
        a = ("Each bulb gets dimmer, and the battery's current decreases. Adding a bulb in series adds resistance to "
             "the single path, so the same battery pushes less current through every bulb." if kind == "series" else
             "Each bulb stays at the same brightness, but the battery's current increases. Each bulb still has the full "
             "battery voltage on its own path, and the new path draws extra current, so the battery runs down sooner.")
    else:
        q = f"{setup} {added} What happens to the total resistance of the circuit? {REASON}"
        a = ("It increases. In series the current must pass through every bulb in turn, so each added bulb adds its "
             "resistance to the total." if kind == "series" else
             "It decreases. Each bulb added in parallel opens another path for the current, so more current can flow "
             "for the same voltage, which means less total resistance.")
    return W(q, a)


what_if("concept_electricity", [
    Law("ohm", "The current", "large",
        [V("V", "the battery's voltage", "the voltage", F(1)), V("R", "the resistance", "the resistance", F(-1))],
        [("A battery drives a current through a resistor.", "the current through the resistor"),
         ("A battery is connected to a heating coil whose resistance stays the same.", "the current in the coil"),
         ("A battery drives a current through a long wire.", "the current in the wire")]),
    Law("coulomb", "The electric force", "strong",
        [V("q", "the charge on one of them", "that charge", F(1)),
         V("r", "the distance between them", "the distance", F(-2))],
        [("Two charged balloons hang near each other.", "the electric force between the balloons"),
         ("Two small charged spheres sit on insulating stands.", "the electric force between the spheres"),
         ("Two charged pith balls hang from threads.", "the electric force between the pith balls")]),
    Law("electric_power", "The power", "large",
        [V("V", "the voltage across it", "the voltage", F(2)), V("R", "its resistance", "the resistance", F(-1))],
        [("An electric heater is connected to a power supply.", "the heater's power"),
         ("A resistor is connected to a battery.", "the power the resistor uses"),
         ("A toaster's heating coil is connected to a power supply.", "the coil's power")]),
])


# =================================================================== light

C("concept_light", "Light & optics", "Light concepts",
  "reflection, color, refraction, light and sound, lenses, and what happens if…")

SURFACES = ["a flat mirror", "the surface of a still pond", "a polished metal sheet"]
REFLECTIONS = [
    ("You can see your reflection in a smooth mirror but not in a sheet of white paper, even though both reflect "
     "light. Explain why.",
     "A smooth mirror reflects all the light in the same direction, so the rays keep their pattern and form an image. "
     "Paper is rough on a tiny scale, so it scatters the light in every direction (diffuse reflection) and no image "
     "forms."),
    ("The word AMBULANCE is printed backward on the front of an ambulance. Explain why.",
     "Drivers ahead see the ambulance in their rear-view mirrors, and a mirror reverses left and right. Printed "
     "backward, the word reads correctly in the mirror."),
    ("A wet road at night glares with the reflections of headlights much more than a dry road does. Explain why.",
     "The film of water makes the road's surface smooth, so it reflects light like a mirror in one direction, into "
     "drivers' eyes. A dry road is rough and scatters the light in all directions."),
]


@variant("concept_light", 1, "Reflection")
@variant("concept_light", 3, "Reflection")
def _reflection(ctx: Ctx) -> Problem:
    if ctx.rng.random() < 0.2:
        return W(*pick(ctx, REFLECTIONS))
    theta, surface = ctx.rng.choice(range(20, 65, 5)), pick(ctx, SURFACES)
    return W(f"A ray of light strikes {surface} at ${theta}^\\circ$ from the normal. At what angle from the normal does "
             f"it reflect? {REASON}",
             f"At ${theta}^\\circ$ from the normal, on the other side of it. By the law of reflection, the angle of "
             f"reflection from {surface} equals the angle of incidence.")


COLOR_THINGS = ["apple", "T-shirt", "car", "flower", "baseball cap", "backpack"]
COLORS = ["red", "green", "blue"]


@variant("concept_light", 1, "Color")
@variant("concept_light", 2, "Color")
def _color(ctx: Ctx) -> Problem:
    thing, color = pick(ctx, COLOR_THINGS), pick(ctx, COLORS)
    if ctx.rng.random() < 0.3:
        return W(f"Explain why a {color} {thing} looks {color} in sunlight.",
                 f"Sunlight contains all colors. The {thing} reflects mostly {color} light into your eyes and absorbs "
                 f"the other colors, so you see it as {color}.")
    light = pick(ctx, COLORS)
    q = f"A {color} {thing} is lit only by {light} light in a dark room. What color does it look? {REASON}"
    if light == color:
        return W(q, f"It looks {color}. The {thing} reflects {color} light, and {color} light is exactly what is shining "
                    f"on it, so it sends that light to your eyes.")
    return W(q, f"It looks black (very dark). A {color} {thing} reflects mainly {color} light and absorbs other colors; "
                f"with only {light} light shining on it, it absorbs almost all of it and reflects almost nothing.")


REFRACTIONS = [
    ("A straw standing in a glass of water looks bent at the water's surface. Explain why.",
     "Light from the part of the straw under water bends as it leaves the water and enters the air. Your eyes trace "
     "the light back in a straight line, so the underwater part seems to be in a different place."),
    ("A swimming pool looks shallower than it really is. Explain why.",
     "Light from the bottom bends away from the normal as it leaves the water. Your eyes assume the light traveled in "
     "a straight line, so the bottom appears higher than it is."),
    ("To spear a fish, you must aim below where the fish appears to be. Explain why.",
     "Light from the fish bends at the water's surface on its way to your eyes, so the fish appears higher, and in a "
     "slightly different place, than it really is."),
    ("A beam of light passes at an angle from air into a block of glass. Does it bend toward the normal or away from "
     "it? Explain why.",
     "Toward the normal. Light slows down when it enters glass, and light bends toward the normal when it slows "
     "down."),
    ("A beam of light passes at an angle from water into air. Does it bend toward the normal or away from it? Explain "
     "why.",
     "Away from the normal. Light speeds up as it leaves the water, and light bends away from the normal when it "
     "speeds up."),
    ("A coin at the bottom of an empty cup is just hidden behind the rim. When water is poured in, the coin comes "
     "into view. Explain why.",
     "With water in the cup, light from the coin bends as it leaves the water, tilting over the rim toward your "
     "eyes, so light that was blocked before now reaches you."),
    ("A prism splits white light into a band of colors. Explain why.",
     "Each color of light slows down by a slightly different amount in glass, so each bends by a different amount. "
     "Violet bends the most and red the least, so the colors spread apart."),
    ("A rainbow appears when sunlight shines on raindrops. Explain how the raindrops make the colors.",
     "Sunlight bends as it enters each drop, reflects off the back, and bends again as it leaves. Each color bends by "
     "a different amount, so the colors leave at slightly different angles and spread into a rainbow."),
    ("On a hot day, a road far ahead can look wet (a mirage). Explain why.",
     "Air just above the hot road is hotter and less dense than the air above it, so light from the sky bends "
     "upward as it passes through. You see the sky's light coming from the road, which looks like a reflection in "
     "water."),
    ("Light bends much more when it enters a diamond than when it enters water. What does that tell you about "
     "light's speed in diamond?",
     "Light must slow down much more in diamond than in water. The bigger the change in speed, the more the light "
     "bends."),
    ("Stars twinkle when seen from the ground, but not from space. Explain why.",
     "The atmosphere has moving pockets of air at different temperatures, which bend starlight by slightly "
     "different amounts. The star's light wobbles in direction and brightness, so it twinkles; above the "
     "atmosphere there is nothing to bend it."),
    ("Your legs look shorter when you stand in a swimming pool. Explain why.",
     "Light from your legs bends as it leaves the water, so your eyes see your feet higher than they really are, and "
     "the underwater part of your legs looks shorter."),
]


@variant("concept_light", 2, "Refraction")
def _refraction(ctx: Ctx) -> Problem:
    return W(*pick(ctx, REFRACTIONS))


DELAYS = [("During a thunderstorm, you see a flash of lightning a few seconds before you hear the thunder.",
           "the thunder"),
          ("At a baseball game, from the far end of the stadium, you see the batter hit the ball a moment before you "
           "hear the crack of the bat.", "the crack of the bat"),
          ("At a fireworks show, you see a firework burst before you hear the bang.", "the bang"),
          ("Far down the track, a race starter fires a pistol. You see the puff of smoke before you hear the shot.",
           "the shot")]
SUNLIGHT = [("The Sun's light takes about 8 minutes to reach the Earth.", "the Sun suddenly went dark",
             "about 8 minutes"),
            ("Light from the Moon takes a little over 1 second to reach the Earth.", "the Moon suddenly vanished",
             "a little over 1 second"),
            ("Light from the nearest star beyond the Sun takes about 4 years to reach the Earth.",
             "that star suddenly burned out", "about 4 years")]


@variant("concept_light", 3, "Light and sound")
def _light_sound(ctx: Ctx) -> Problem:
    kind = ctx.rng.randrange(3)
    if kind == 0:
        scene, sound = pick(ctx, DELAYS)
        return W(f"{scene} Explain why.",
                 f"Light travels about a million times faster than sound (about 300,000 km each second, against about "
                 f"a third of a kilometer each second for sound), so the light arrives almost at once while {sound} "
                 f"takes longer to cover the same distance.")
    if kind == 1:
        n = ctx.rng.choice([3, 6, 9, 12, 15])
        km = n // 3
        return W(f"You count {n} seconds between a lightning flash and its thunder. Sound travels about 1 kilometer "
                 f"every 3 seconds. About how far away was the lightning? {REASON}",
                 f"About {km} kilometer{'s' if km > 1 else ''}. The light arrives almost instantly, so the {n} seconds "
                 f"is the time the sound took, and at about 1 km every 3 seconds that is about {km} km.")
    fact, event, delay = pick(ctx, SUNLIGHT)
    return W(f"{fact} If {event}, how soon would we notice? {REASON}",
             f"Only after {delay}. The last light that left before the change is still on its way, and we keep seeing "
             f"it until it arrives.")


LENSES = [
    ("A magnifying glass can focus sunlight onto a small bright spot. What kind of lens is it, and how does it do "
     "this?",
     "A converging (convex) lens, thicker in the middle than at the edges. It bends the parallel rays of sunlight "
     "toward each other so they meet at a point, the focal point."),
    ("A nearsighted person sees faraway objects blurred. What kind of lens corrects this, and why?",
     "A diverging (concave) lens. The nearsighted eye focuses light from far away in front of the retina; the "
     "diverging lens spreads the rays out a little first, so the eye brings them to a focus on the retina."),
    ("A farsighted person has trouble reading up close. What kind of lens corrects this, and why?",
     "A converging (convex) lens. The farsighted eye can't bend light from nearby objects enough to focus it on the "
     "retina; the converging lens adds the extra bending."),
    ("A camera lens forms an upside-down image of a scene on its sensor. What kind of lens is it?",
     "A converging (convex) lens. It bends the light from each point of the scene to meet at a point on the sensor, "
     "and the rays cross on the way, so the image is upside down (a real image)."),
    ("A peephole in a door shows a wide, small, upright view of the hallway. What kind of lens does it use?",
     "A diverging (concave) lens. It spreads light out, making small upright images that take in a wide field of "
     "view."),
    ("When you hold a magnifying glass close to a page, the print looks bigger and upright. Explain why.",
     "With the page closer to the converging lens than its focal point, the lens bends the light so it seems to come "
     "from a larger, upright image behind the page, a virtual image."),
    ("A projector makes a large image of a small picture on a distant screen. What kind of lens does it use?",
     "A converging (convex) lens. It bends the light from the small picture so it comes together again far away on "
     "the screen, where it forms a large real image."),
    ("Your eye's lens changes shape to focus. How does its shape change for close objects and for faraway ones?",
     "For close objects the lens becomes thicker and more curved, so it bends light more; for faraway objects it "
     "becomes thinner and flatter, so it bends light less. Either way the image lands on the retina."),
    ("Glasses for nearsighted people make the wearer's eyes look smaller to other people. Explain why.",
     "The glasses use diverging lenses, which make images smaller. Someone looking at the wearer's eyes sees them "
     "through those lenses, so the eyes look smaller."),
    ("A drop of water on a leaf can act as a tiny magnifier. Explain how.",
     "The drop is curved like a converging lens, thicker in the middle, so it bends light toward a focus and makes "
     "the leaf's surface under it look bigger."),
    ("A pencil seen through a round glass of water looks wider than it is. Explain why.",
     "The round glass of water acts like a converging lens, bending the light from the pencil so that it forms a "
     "magnified image."),
]


@variant("concept_light", 3, "Lenses")
def _lens(ctx: Ctx) -> Problem:
    return W(*pick(ctx, LENSES))


what_if("concept_light", [
    Law("brightness", "The brightness", "bright",
        [V("P", "the power of the bulb", "the bulb's power", F(1)),
         V("r", "the distance from the bulb", "the distance", F(-2))],
        [("You read by the light of a single bare bulb.", "the brightness of the light on your page"),
         ("A streetlight lights up the sidewalk below it.", "the brightness of the light on the sidewalk"),
         ("A single lamp lights a dark room.", "the brightness of the light on the far wall")]),
    Law("light_delay", "The travel time of light", "long",
        [V("d", "the distance the light travels", "the distance", F(1))],
        [("Light travels from a distant star to Earth.", "the time the light takes"),
         ("A laser pulse travels to a mirror on the Moon and back.", "the time the pulse takes")]),
])
