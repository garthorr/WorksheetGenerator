"""Tiny arithmetic evaluator used to check AI-generated answers.

Only numbers, named variables, + - * / ** %, and a whitelist of math
functions are allowed — no attribute access, indexing or arbitrary calls.
"""

from __future__ import annotations

import ast
import math
import operator

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod}
_UN = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
    "exp": math.exp, "ln": math.log, "log": math.log, "log10": math.log10, "log2": math.log2,
    "abs": abs, "radians": math.radians, "degrees": math.degrees, "min": min, "max": max,
}
_CONSTS = {"pi": math.pi, "e": math.e}


def safe_eval(expr: str, variables: dict[str, float] | None = None) -> float:
    if len(expr) > 500:
        raise ValueError("expression too long")
    names = {**_CONSTS, **{k: float(v) for k, v in (variables or {}).items()}}

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)  # floats overflow fast instead of building huge ints
        if isinstance(node, ast.Name):
            if node.id in names:
                return names[node.id]
            raise ValueError(f"unknown name {node.id!r}")
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
            return _BIN[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UN:
            return _UN[type(node.op)](ev(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS \
                and not node.keywords:
            return _FUNCS[node.func.id](*(ev(a) for a in node.args))
        raise ValueError(f"unsupported expression: {ast.dump(node)[:60]}")

    result = ev(ast.parse(expr.replace("^", "**"), mode="eval"))
    if isinstance(result, complex) or not math.isfinite(result):
        raise ValueError("non-real result")
    return float(result)
