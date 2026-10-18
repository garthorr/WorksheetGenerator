# Worksheet Generator

A dockerized web app for building math and physics worksheets with answer keys.
Served at **https://worksheets.tastymath.com** through Traefik.

- **Pick topics by course:** Algebra 1, Geometry, Algebra 2, Precalculus, Conceptual
  Physics and AP Physics 1, with units in teaching order (calculus sits under
  "Beyond Precalculus"). You can also type any **custom topic** and have your Ollama
  model write the problems.
- **Geometry:** angle relationships (parallel lines and transversals, triangle sums,
  exterior angles, polygons), special right triangles, similar triangles and the
  side-splitter theorem, distance and midpoint, transformations, circles (inscribed angles,
  arc length and sector area, intersecting chords, equations of circles), volume and surface
  area, and the laws of sines and cosines.
- **AP Physics 1, every unit:** kinematics through fluids, including torque and static
  equilibrium, rotational kinematics and τ = Iα (pulleys with mass), rotational kinetic
  energy, angular momentum and rolling, and springs and pendulums. Torque and
  oscillations are also in Conceptual Physics.
- **Pick skills:** each topic is made of named skills (e.g. *Factor ax² + bx + c*,
  *Simplest radical form*, *Free fall*) marked E/M/H for difficulty. A section uses
  every skill at its difficulty, or exactly the skills you click.
- **Answer forms for math:** exact answers (in terms of π, simplest radical form),
  decimals, or both, rounded to the nearest whole number, tenth, hundredth or
  thousandth. The question tells students which form to use. Physics answers use
  significant figures.
- **Every problem has an answer and worked steps.** Built-in topics compute the answer in
  code (sympy for algebra and calculus), so those answers are always correct. The answer key
  shows the work the way these courses expect:
  - physics: knowns → equation → substitution → result;
  - algebra: each operation (distributing, collecting terms, elimination for systems);
  - factoring: the factor pair and the zero product property;
  - quadratic formula: the discriminant, then the radical simplified.

  AI answers are checked automatically (see below).
- **Word problems and derivations:** Algebra 1 equation word problems (consecutive
  integers, perimeter, tickets and coins, distance-rate-time, mixtures, catch-up) and AP
  Physics 1 symbolic derivations ("derive an expression for v in terms of g and h").
  Physics problems also rotate the unknown: solve v = v₀ + at for v one time, a or t the
  next. Measured values are shown with at least two significant figures (3.0 kg).
- **GUI:** build a worksheet from sections (topic × count × difficulty), preview
  it on a live paper page, regenerate, edit or delete single problems, and
  print or save as PDF with a separate answer key page. Saved worksheets go to the
  Library. Ollama, paper size, columns, work space and sig figs are configured on the Setup page.
- **Reproducible:** the same seed and the same built-in sections always give the same worksheet.
- **No repeats:** a worksheet never contains the same problem twice, sections rotate
  through every problem type in their topic, and answers rarely repeat within a section.
- **Figures:** problems come with diagrams drawn from their own numbers: triangles drawn to
  their angles, parallel lines and transversals, similar triangles, circles, sectors and
  chords, solids, shapes on the coordinate plane, launches, inclines, free-body diagrams,
  collisions, circuits, lens and refraction diagrams, motion graphs, seesaws and beams,
  pulleys, springs and pendulums. Figures label the givens and
  mark the unknown with x, θ or ?; they never show the answer. Some skills are read off a
  figure (slope from a graph, velocity-time and position-time graphs, free-body diagrams), so
  those keep their figure even when figures are turned off on the Setup page or for a section.
- **Physics options:** g = 9.8 or 10 m/s² (stated in the problem when it's 10), and a
  **whole-number** mode for conceptual physics with simple givens and answers. Set the
  defaults on the Setup page; each physics section can override them. Sections added
  from the Conceptual Physics view start with g = 10 and whole numbers.

## Why not use AI for everything?

LLMs are good at writing varied word problems but unreliable at arithmetic. In
testing, a 12B model wrote the right formula for a Carnot problem and then stated
533 K when the answer was 320 K. So:

| Source | Use it for | Answer correctness |
|---|---|---|
| **Built-in** (default) | Computational practice in the 44 catalog topics | Computed exactly. Always right |
| **AI (Ollama)** | Custom topics, themed word problems, more variety | Checked by formula. Problems that fail are flagged or retried |

The AI must return its given values and an arithmetic formula for the answer.
The server evaluates that formula itself, with a sandboxed evaluator, and
requires three things to agree: the computed value, the model's stated value, and
the number in the answer text. In **strict mode** (the default, set on the Setup page),
problems that fail are discarded and re-requested, up to two extra rounds. Any problem
that still couldn't be verified is labeled in the preview: **AI ✓** (passed),
**AI ⚠** (failed the check) or **AI ?** (not checkable, e.g. a symbolic answer).
Hover a label for details. Labels never print.

## Deploy (Traefik)

```bash
cp .env.example .env     # set APP_PASSWORD, TRAEFIK_CERTRESOLVER, Ollama model
docker compose up -d --build
```

- Joins the external `traefik` network with router `worksheets` on entrypoint `websecure`.
- `TRAEFIK_CERTRESOLVER` must match your Traefik config. Your other stacks use
  both `le` and `letsencrypt`, depending on the host.
- Add a DNS record for `worksheets.tastymath.com` pointing at the Traefik host.
- Data (settings + saved worksheets) lives in the `worksheet_data` volume.

### Ollama

The container reaches the host's Ollama at `http://host.docker.internal:11434`
(mapped via `extra_hosts`). Ollama has to listen on more than loopback:
`OLLAMA_HOST=0.0.0.0`. The URL and model can be changed any time on the
**Setup** page, which also lists the models you have pulled.

Model choice matters for AI sections. Math-strong models such as `qwen2.5:14b`
pass the check far more often than small general models, and fewer retries
also means faster generation.

### Security

The site is public and AI sections spend your Ollama compute, so set
`APP_PASSWORD`. With no password the app runs open and logs a warning.

## Local development

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
(cd tests/katex && npm ci)   # optional: enables the KaTeX rendering test (needs Node)
DATA_DIR=./data OLLAMA_BASE_URL=http://localhost:11434 .venv/bin/uvicorn app.main:app --reload --port 8765
.venv/bin/pytest -q
```

Or run in Docker without Traefik: `docker compose -f docker-compose.local.yml up --build`
and open http://localhost:8080.

## Adding a topic

Topics live in `app/generators/`: `math_gen.py` (algebra through calculus), `math_words.py`
(word problems), `geometry_gen.py`, `physics_gen.py`, `rotation_gen.py` (torque, rotation,
oscillations) and `derivations.py`:

```python
topic("magnetism", "physics", "Magnetism", "Magnetic force", "Force on a current-carrying wire.",
      courses=["conceptual"])

@variant("magnetism", 1, "Force on a wire")   # level 1 = easy, 2 = medium, 3 = hard; the label is the skill
def _wire_force(ctx: Ctx) -> Problem:
    I, L, B = step(ctx.rng, 1, 10, 0.5), step(ctx.rng, 0.1, 1, 0.1), step(ctx.rng, 0.1, 2, 0.1)
    return P(f"A ${num(L)}{U('m')}$ wire carries ${num(I)}{U('A')}$ across a ${num(B)}{U('T')}$ magnetic field. "
             "Find the force on it.", f"$F = {ctx.fmt(I * L * B)}{U('N')}$", "$F = ILB$",
             {"I": I, "L": L, "B": B}, {"F": I * L * B})
```

The topic appears in the catalog automatically. A new unit (here "Magnetism") also
needs a place in `COURSE_UNITS` in `core.py`, which sets each course's teaching order;
the tests remind you. Physics variants pass their givens and answers through `P(...)`
so the tests can check them, and need a physics-law check in `LAWS` in
`tests/test_quality.py`. Figures come from `app/generators/drawings.py` (built on the small SVG kit in `figures.py`);
pass `figure=` to `Problem`/`P`, and add `figure_required=True` to the facts when the problem
can't be done without it. Math answers with exact forms should use `ctx.form_note()`
and `ctx.exact_or_decimal()`, and plain decimals should use `ctx.round_note()` and
`ctx.rnd()`.

## Quality checks

`tests/test_quality.py` holds every built-in problem to these standards:

- **Correct, checked independently.** Math answers are substituted back into the
  displayed equation, or the question text is re-parsed and evaluated. Physics answers
  must satisfy a *different* relation than the generator used: conservation of momentum
  and energy, Kirchhoff's rules, alternate kinematics equations, torques about a different
  pivot. Geometry answers are checked another way too: transformations as complex-number
  maps, right angles by dot products, arcs and sectors in radians, triangles by the law of
  sines. Each problem type must have a check, so a new type can't skip one.
- **Displayed consistently:** every given value appears in the question and every
  computed answer appears in the answer text.
- **Realistic:** runners don't go 19 m/s, ladders lean steeply, TV screens have real
  proportions, wave speeds and densities match real materials, and currents stay in range.
- **Varied:** 30-problem sections never repeat, sections cover every problem type,
  and answers rarely repeat.
- **Worked steps reach the answer:** every number in an answer appears in its steps, and
  physics steps use every given. Derivation answers are checked by solving the listed
  physics relations with sympy at random values for every symbol, and word-problem
  solutions must satisfy their equations.
- **Every answer form and skill works:** math answers are checked in exact, decimal and
  combined forms at several rounding places, every skill generates on its own, and
  every topic belongs to a course.
- **Well-formed:** clean wording, g is stated exactly when it matters, whole-number mode
  delivers simple values, and every formula renders in KaTeX (`tests/test_katex.py`).

`tests/test_figures.py` checks that every figure is valid SVG, only shows numbers that are in
the question (or that the problem is read from), never shows the answer, and marks the unknown.

To review every kind of figure at once, render the gallery and open it in a browser:

```bash
.venv/bin/python -m scripts.gallery gallery.html
```

To see the numbers behind this, run the audit (pool size, wording variety, repeats,
whole-number rate per topic and level):

```bash
.venv/bin/python -m scripts.audit            # all topics
.venv/bin/python -m scripts.audit kinematics # one topic
```
