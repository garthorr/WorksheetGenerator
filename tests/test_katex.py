"""Every generated question, answer and solution must render in KaTeX (the GUI's math renderer).

Needs Node and `npm ci` in tests/katex; skipped otherwise.
"""

import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from app.generators import TOPICS, generate_set
from app.generators.core import supports_mc

KATEX_DIR = Path(__file__).parent / "katex"
pytestmark = pytest.mark.skipif(
    not shutil.which("node") or not (KATEX_DIR / "node_modules" / "katex").exists(),
    reason="run `npm ci` in tests/katex to enable the KaTeX check")


def test_all_generated_latex_renders():
    texts = []
    for topic, t in TOPICS.items():
        for level in t.variants:
            for g, nice in ((9.8, False), (10, True)):
                for p in generate_set(topic, level, 12, random.Random(f"k{topic}{level}{nice}"), g=g, nice=nice):
                    texts += [p.question, p.answer, p.solution]
                if supports_mc(topic):  # multiple choice: each choice is shown as $...$
                    for p in generate_set(topic, level, 12, random.Random(f"m{topic}{level}{nice}"), g=g, nice=nice,
                                          mc=True):
                        texts += [p.question, p.answer, *(f"${c}$" for c in p.choices)]
    out = subprocess.run(["node", "check.mjs"], cwd=KATEX_DIR, input=json.dumps(texts),
                         capture_output=True, text=True, check=True)
    failures = json.loads(out.stdout)
    assert not failures, "\n".join(f"{f['error']}\n    in: {texts[f['index']][:160]}" for f in failures[:10])
