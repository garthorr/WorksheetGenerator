"""Quality audit for the built-in generators.

    python -m scripts.audit              # every topic
    python -m scripts.audit kinematics   # just some topics

Columns:
  pool    distinct problems among 300 independent draws (how big the problem pool is)
  words   distinct sentence templates (numbers stripped) among those draws
  types   problem types at this level (sections rotate through all of them)
  rep-q   10-problem sections containing a repeated problem
  rep-a   10-problem sections containing a repeated answer
  whole   physics problems with simple values in whole-number mode (g = 10)
"""

import random
import re
import sys

from app.generators import TOPICS, generate_set
from app.generators.core import is_nice_problem


def audit(topic: str, level: int, n: int = 300, sections: int = 20) -> dict:
    rng = random.Random(level)
    pool = [generate_set(topic, level, 1, rng)[0] for _ in range(n)]
    secs = [generate_set(topic, level, 10, random.Random(f"s{i}")) for i in range(sections)]
    row = {
        "pool": len({p.key for p in pool}) / n,
        "words": len({re.sub(r"-?\d+(\.\d+)?", "#", p.question) for p in pool}),
        "types": len(TOPICS[topic].variants[level]),
        "rep-q": sum(len({p.key for p in s}) < len(s) for s in secs) / sections,
        "rep-a": sum(len({p.answer for p in s}) < len(s) for s in secs) / sections,
        "whole": None,
    }
    if TOPICS[topic].subject == "physics":
        nice = [is_nice_problem(p) for i in range(sections)
                for p in generate_set(topic, level, 10, random.Random(f"w{i}"), g=10, nice=True)]
        row["whole"] = sum(nice) / len(nice)
    return row


def main(topics: list[str]) -> None:
    pct = lambda v: "" if v is None else f"{v * 100:5.0f}%"  # noqa: E731
    print(f"{'topic':16} lvl  {'pool':>6} {'words':>5} {'types':>5} {'rep-q':>6} {'rep-a':>6} {'whole':>6}")
    for topic in topics or TOPICS:
        for level in sorted(TOPICS[topic].variants):
            r = audit(topic, level)
            print(f"{topic:16} {level:>3}  {pct(r['pool'])} {r['words']:>5} {r['types']:>5} "
                  f"{pct(r['rep-q'])} {pct(r['rep-a'])} {pct(r['whole']):>6}")


if __name__ == "__main__":
    main(sys.argv[1:])
