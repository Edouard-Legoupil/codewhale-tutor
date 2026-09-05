#!/usr/bin/env python3
"""
Symbolic math engine for the tutor (checking and solving).

Uses SymPy via the modern FastMCP API. Lets the tutor verify a student's
calculation (derivatives, integrals, eigenvalues, probabilities, algebra) and
solve equations, without hand-evaluating.

Only a restricted namespace of symbols and SymPy functions is exposed; no Python
builtins or imports are reachable from the expression parser.
"""

import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication,
    convert_xor,
)
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("codewhale-math-engine")

_TRANSFORMATIONS = standard_transformations + (implicit_multiplication, convert_xor)

_SYMBOL_NAMES = ["x", "y", "z", "t", "n", "k", "a", "b", "c", "lambda", "mu", "sigma", "theta"]


def _local_dict() -> dict:
    loc = {name: sp.Symbol(name) for name in _SYMBOL_NAMES}
    loc.update({
        "Integer": sp.Integer,
        "Float": sp.Float,
        "Symbol": sp.Symbol,
        "diff": sp.diff,
        "integrate": sp.integrate,
        "Derivative": sp.Derivative,
        "Integral": sp.Integral,
        "Matrix": sp.Matrix,
        "solve": sp.solve,
        "sqrt": sp.sqrt,
        "exp": sp.exp,
        "log": sp.log,
        "ln": sp.log,
        "sin": sp.sin,
        "cos": sp.cos,
        "tan": sp.tan,
        "pi": sp.pi,
        "E": sp.E,
        "oo": sp.oo,
        "Rational": sp.Rational,
        "Abs": sp.Abs,
        "factorial": sp.factorial,
        "binomial": sp.binomial,
        "limit": sp.limit,
        "summation": sp.summation,
    })
    return loc


def _parse(expr: str):
    """Parse an expression in a restricted, accent-free namespace."""
    return parse_expr(
        expr,
        local_dict=_local_dict(),
        global_dict={},
        transformations=_TRANSFORMATIONS,
        evaluate=True,
    )


def _approx(value) -> str:
    try:
        num = float(sp.N(value))
        return f"{num:.6g}"
    except Exception:  # noqa: BLE001
        return ""


@mcp.tool()
def check_math(expression: str, expected: str = "") -> str:
    """Simplify/evaluate a math expression and optionally check it against an
    expected result.

    Supports `^` for powers, `diff(f, x)` / `integrate(f, x)` for calculus, and
    `Matrix([[...], ...]).eigenvals()` / `.det()` / `.inv()` for linear algebra.

    Args:
        expression: The student's (or tutor's) expression to evaluate.
        expected: Optional expected value to compare against.
    """
    try:
        result = _parse(expression)
    except Exception as e:  # noqa: BLE001
        return f"❌ Could not parse expression: {e}"

    try:
        simplified = sp.simplify(result)
    except Exception:  # noqa: BLE001
        simplified = result

    out = [f"**Expression:** `{expression}`", f"**Result:** `{simplified}`"]
    approx = _approx(simplified)
    if approx:
        out.append(f"**Approximate:** {approx}")

    if expected:
        try:
            expected_val = sp.simplify(_parse(expected))
        except Exception as e:  # noqa: BLE001
            return f"❌ Could not parse expected value: {e}"

        diff = sp.simplify(simplified - expected_val)
        if diff == 0:
            out.append("✅ **Check:** matches the expected value.")
        else:
            my_num = _approx(simplified)
            exp_num = _approx(expected_val)
            if my_num and exp_num and abs(float(sp.N(simplified)) - float(sp.N(expected_val))) < 1e-6:
                out.append("✅ **Check:** numerically equal to the expected value.")
            else:
                out.append(
                    f"❌ **Check:** not equal. Difference = `{diff}` "
                    f"(yours `{simplified}`, expected `{expected_val}`)."
                )

    return "\n".join(out)


@mcp.tool()
def solve_equation(equation: str, variable: str = "x") -> str:
    """Solve an equation for a variable.

    Write it as `x**2 - 4 = 0`, `x**2 = 4`, or `2x + 1 = 0` (implicit
    multiplication and `^` powers are accepted).

    Args:
        equation: The equation to solve.
        variable: The variable to solve for (default `x`).
    """
    try:
        if "=" in equation:
            lhs_s, rhs_s = equation.split("=", 1)
            relation = sp.Eq(_parse(lhs_s), _parse(rhs_s))
        else:
            relation = sp.Eq(_parse(equation), 0)
        solutions = sp.solve(relation, sp.Symbol(variable))
    except Exception as e:  # noqa: BLE001
        return f"❌ Could not solve: {e}"

    return f"**Equation:** `{equation}`\n**Solutions for {variable}:** `{solutions}`"


@mcp.tool()
def sanity_check(value: str, kind: str = "general") -> str:
    """Check whether a numeric result is plausible for its quantity type.

    Args:
        value: The numeric/expression result to check.
        kind: One of probability, variance, density, correlation, count, general.
    """
    try:
        v = sp.sympify(value)
        num = float(sp.N(v))
    except Exception:  # noqa: BLE001
        return f"❌ Could not parse value: {value}"

    issues = []
    kind = kind.lower()
    if kind in ("probability", "prob"):
        if num < 0 or num > 1:
            issues.append("a probability must be in [0, 1]")
    elif kind == "variance":
        if num < 0:
            issues.append("a variance cannot be negative")
    elif kind == "density":
        if num < 0:
            issues.append("a density cannot be negative")
    elif kind == "correlation":
        if num < -1 or num > 1:
            issues.append("a correlation must be in [-1, 1]")
    elif kind == "count":
        if num < 0 or num != int(num):
            issues.append("a count must be a non-negative integer")

    if issues:
        return f"⚠️ **Sanity check failed** ({kind}): " + "; ".join(issues) + f" (got {num:.6g})."
    return f"✅ **Sanity check passed** ({kind}): {num:.6g}."


if __name__ == "__main__":
    mcp.run()
