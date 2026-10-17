# Worksheet Generator

A dockerized web app for building math and physics worksheets with answer keys.
Served at **https://worksheets.tastymath.com** through Traefik.

- **Pick topics** from a catalog of 30 built-in topics (arithmetic → calculus,
  kinematics → optics), or type any **custom topic** and have your Ollama model
  write the problems.
- **Every problem has an answer.** Built-in topics compute the answer in code
  (sympy for algebra and calculus), so those answers are always correct. AI answers
  are checked automatically (see below).
- **GUI:** build a worksheet from sections (topic × count × difficulty), preview
  it on a live paper page, regenerate, edit or delete single problems, and
  print or save as PDF with a separate answer key page. Saved worksheets go to the
  Library. Ollama, paper size, columns, work space and sig figs are configured on the Setup page.
- **Reproducible:** the same seed and the same built-in sections always give the same worksheet.
- **No repeats:** a worksheet never contains the same problem twice, sections rotate
  through every problem type in their topic, and answers rarely repeat within a section.
- **Physics options:** g = 9.8 or 10 m/s² (stated in the problem when it's 10), and a
  **whole-number** mode for conceptual physics with simple givens and answers. Set the
  defaults on the Setup page; each physics section can override them.

## Why not use AI for everything?

LLMs are good at writing varied word problems but unreliable at arithmetic. In
testing, a 12B model wrote the right formula for a Carnot problem and then stated
533 K when the answer was 320 K. So:

| Source | Use it for | Answer correctness |
|---|---|---|
| **Built-in** (default) | Computational practice in the 30 catalog topics | Computed exactly. Always right |
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

Topics live in `app/generators/math_gen.py` and `physics_gen.py`:

```python
topic("my_topic", "physics", "Mechanics", "Hooke's law", "Spring force and stretch.")

@variant("my_topic", 1)          # difficulty 1 = easy, 2 = medium, 3 = hard
def _hooke(ctx: Ctx) -> Problem:
    k, x = step(ctx.rng, 50, 500, 10), step(ctx.rng, 0.01, 0.3, 0.01)
    return Problem(f"A spring with $k = {num(k)}{U('N/m')}$ is stretched ${num(x)}{U('m')}$. Find the force.",
                   f"$F = {sig(k * x, ctx.sig)}{U('N')}$", "$F = kx$")
```

The topic appears in the GUI catalog automatically. Physics variants should pass
their givens and answers to `facts` (see the `P(...)` helper in `physics_gen.py`).

## Quality checks

`tests/test_quality.py` holds every built-in problem to these standards:

- **Correct, checked independently.** Math answers are substituted back into the
  displayed equation, or the question text is re-parsed and evaluated. Physics answers
  must satisfy a *different* relation than the generator used: conservation of momentum
  and energy, Kirchhoff's rules, alternate kinematics equations. Each physics problem type
  must have a check, so a new type can't skip one.
- **Displayed consistently:** every given value appears in the question and every
  computed answer appears in the answer text.
- **Realistic:** runners don't go 19 m/s, ladders lean steeply, TV screens have real
  proportions, wave speeds and densities match real materials, and currents stay in range.
- **Varied:** 30-problem sections never repeat, sections cover every problem type,
  and answers rarely repeat.
- **Well-formed:** clean wording, g is stated exactly when it matters, whole-number mode
  delivers simple values, and every formula renders in KaTeX (`tests/test_katex.py`).

To see the numbers behind this, run the audit (pool size, wording variety, repeats,
whole-number rate per topic and level):

```bash
.venv/bin/python -m scripts.audit            # all topics
.venv/bin/python -m scripts.audit kinematics # one topic
```
