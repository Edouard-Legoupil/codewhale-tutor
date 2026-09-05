#!/usr/bin/env python3
"""
Practice engine for the tutor (exercise generation, grading, mock exams,
and bug-hunting drills).

Uses SymPy via the modern FastMCP API. Generators return the question *and* the
answer/hint so the tutor can hold the answer back and grade the student's
attempt (retrieval practice, not re-reading).
"""

import json
import random
from pathlib import Path

import sympy as sp
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("codewhale-practice-engine")

SYLLABI_DIR = Path.home() / ".codewhale" / "syllabi"


def _r(a: int, b: int) -> int:
    return random.randint(a, b)


# --- Exercise generators (concept -> list of {question, answer, hint}) -------
def _gen_derivative(difficulty: int, count: int) -> list:
    x = sp.Symbol("x")
    out = []
    for _ in range(count):
        a = _r(1, 5 if difficulty <= 2 else 9)
        n = _r(2, 3 + difficulty)
        expr = a * x ** n + _r(-5, 5) * x ** 2 + _r(-5, 5)
        out.append({
            "question": f"Differentiate: {sp.sstr(expr)}",
            "answer": sp.sstr(sp.diff(expr, x)),
            "hint": "Apply the power rule term by term.",
        })
    return out


def _gen_integral(difficulty: int, count: int) -> list:
    x = sp.Symbol("x")
    out = []
    for _ in range(count):
        a = _r(1, 5)
        n = _r(1, 2 + difficulty)
        expr = a * x ** n + _r(-3, 3)
        out.append({
            "question": f"Integrate: {sp.sstr(expr)}",
            "answer": sp.sstr(sp.integrate(expr, x)),
            "hint": "Add one to the exponent, divide by it, and don't forget the constant of integration.",
        })
    return out


def _gen_eigenvalues(difficulty: int, count: int) -> list:
    out = []
    for _ in range(count):
        if difficulty >= 3:
            M = sp.Matrix([[_r(-3, 3), _r(-3, 3)], [_r(-3, 3), _r(-3, 3)]])
        else:
            M = sp.Matrix([[_r(1, 5), _r(-2, 2)], [0, _r(1, 5)]])  # triangular
        out.append({
            "question": f"Find the eigenvalues of {M.tolist()}",
            "answer": sp.sstr(M.eigenvals()),
            "hint": "Solve det(A − λI) = 0.",
        })
    return out


def _gen_determinant(difficulty: int, count: int) -> list:
    out = []
    for _ in range(count):
        M = sp.Matrix([[_r(-4, 4), _r(-4, 4)], [_r(-4, 4), _r(-4, 4)]])
        out.append({
            "question": f"Compute the determinant of {M.tolist()}",
            "answer": sp.sstr(M.det()),
            "hint": "For a 2×2 matrix, det = ad − bc.",
        })
    return out


def _gen_bayes(difficulty: int, count: int) -> list:
    out = []
    for _ in range(count):
        p_a = sp.Rational(_r(1, 4), 10)
        sens = sp.Rational(_r(5, 9), 10)   # P(+|condition)
        fpr = sp.Rational(_r(1, 4), 10)     # P(+|no condition)
        num = sens * p_a
        den = sens * p_a + fpr * (1 - p_a)
        out.append({
            "question": (
                f"A condition affects {p_a} of the population. A test has sensitivity "
                f"{sens} and false-positive rate {fpr}. Given a positive test, what is "
                f"P(condition | positive)?"
            ),
            "answer": sp.sstr(sp.simplify(num / den)),
            "hint": "Bayes' theorem with the total-probability denominator.",
        })
    return out


def _gen_expectation(difficulty: int, count: int) -> list:
    out = []
    for _ in range(count):
        n = _r(5, 15)
        p = sp.Rational(_r(1, 8), 10)
        out.append({
            "question": f"For X ~ Binomial(n={n}, p={p}), compute E[X] and Var(X).",
            "answer": f"E[X] = {sp.sstr(n * p)}; Var(X) = {sp.sstr(n * p * (1 - p))}",
            "hint": "Binomial: E = np, Var = np(1−p).",
        })
    return out


def _gen_variance_sum(difficulty: int, count: int) -> list:
    out = []
    for _ in range(count):
        a = _r(-5, 5)
        b = _r(-5, 5)
        out.append({
            "question": (
                f"X and Y are independent with Var(X)=2 and Var(Y)=3. "
                f"Compute Var({a}X + {b}Y)."
            ),
            "answer": sp.sstr(a ** 2 * 2 + b ** 2 * 3),
            "hint": "Independence means no covariance term: Var(aX+bY) = a²Var(X) + b²Var(Y).",
        })
    return out


def _gen_python(difficulty: int, count: int) -> list:
    tasks = {
        1: "Write a function `count_words(text)` that returns the number of words in a string.",
        2: "Write a function `word_freq(text)` that returns a dict mapping each word to its count.",
        3: "Write a function `read_lines(path)` that reads a file and returns the list of non-empty lines.",
    }
    out = []
    for _ in range(count):
        out.append({
            "question": tasks.get(difficulty, tasks[3]),
            "answer": "(code review — ask the student to trace it on a small example)",
            "hint": "Consider `str.split`, `dict.get`, and `with open(...) as f`.",
        })
    return out


_GENERATORS = {
    "derivative": _gen_derivative,
    "differentiate": _gen_derivative,
    "integral": _gen_integral,
    "integrate": _gen_integral,
    "calculus": _gen_derivative,
    "calculus_analysis": _gen_derivative,
    "eigenvalues": _gen_eigenvalues,
    "eigenvectors": _gen_eigenvalues,
    "diagonalisation": _gen_eigenvalues,
    "determinant": _gen_determinant,
    "matrix": _gen_determinant,
    "linear_algebra": _gen_eigenvalues,
    "bayes": _gen_bayes,
    "conditional_probability": _gen_bayes,
    "probability": _gen_expectation,
    "binomial": _gen_expectation,
    "expectation": _gen_expectation,
    "statistics": _gen_variance_sum,
    "variance": _gen_variance_sum,
    "python": _gen_python,
    "python_programming": _gen_python,
    "programming": _gen_python,
}


def _find_generator(concept: str):
    key = concept.lower().strip()
    if key in _GENERATORS:
        return _GENERATORS[key]
    for k, g in _GENERATORS.items():
        if k in key or key in k:
            return g
    return None


# --- Tools -------------------------------------------------------------------
@mcp.tool()
def generate_exercises(concept: str, difficulty: int = 2, count: int = 3) -> str:
    """Generate practice exercises for a concept (with answers for the tutor).

    Args:
        concept: Concept to practise (e.g. derivative, integral, eigenvalues,
            determinant, bayes, probability, statistics, python).
        difficulty: 1 (easy) to 5 (hard).
        count: Number of exercises (max 5).
    """
    gen = _find_generator(concept)
    if gen is None:
        return (
            "❌ No exercise templates for that concept. Try one of: derivative, "
            "integral, eigenvalues, determinant, bayes, probability, statistics, python."
        )
    try:
        exercises = gen(max(1, min(difficulty, 5)), max(1, min(count, 5)))
    except Exception as e:  # noqa: BLE001
        return f"❌ Could not generate exercises: {e}"

    lines = [f"📝 **{len(exercises)} exercise(s) for {concept} (difficulty {difficulty}):**"]
    for i, ex in enumerate(exercises, 1):
        lines.append(f"\n**{i}.** {ex['question']}\n   - Answer: {ex['answer']}\n   - Hint: {ex['hint']}")
    return "\n".join(lines)


@mcp.tool()
def grade_answer(answer: str, expected: str) -> str:
    """Grade a student's answer against the expected result (symbolic or text).

    Args:
        answer: The student's answer.
        expected: The correct answer.
    """
    try:
        a = sp.sympify(answer)
        e = sp.sympify(expected)
        if sp.simplify(a - e) == 0:
            return "✅ Correct."
        try:
            if abs(float(sp.N(a)) - float(sp.N(e))) < 1e-6:
                return "✅ Correct (numerically equal)."
        except Exception:  # noqa: BLE001
            pass
        return f"❌ Incorrect. Expected `{expected}`, got `{sp.sstr(a)}`."
    except Exception:  # noqa: BLE001
        if answer.strip().lower() == expected.strip().lower():
            return "✅ Correct."
        return f"❌ Incorrect. Expected: `{expected}`."


@mcp.tool()
def generate_mock_exam(syllabus_id: str, num_questions: int = 6) -> str:
    """Build a timed mock exam from the concepts in a syllabus.

    Args:
        syllabus_id: Syllabus ID.
        num_questions: Total questions (max 12).
    """
    syllabus_file = SYLLABI_DIR / f"{syllabus_id}.json"
    if not syllabus_file.exists():
        return f"❌ Syllabus {syllabus_id} not found"

    with open(syllabus_file, "r", encoding="utf-8") as f:
        syllabus = json.load(f)

    concepts = syllabus.get("concepts", [])
    if not concepts:
        return "❌ Syllabus has no concepts — run process_syllabus first."

    questions = []
    n = max(1, min(num_questions, 12))
    for i in range(n):
        concept = concepts[i % len(concepts)]
        name = concept.get("name", "")
        gen = _find_generator(name)
        if gen is None:
            gen = _gen_derivative
        qs = gen(2, 1)
        questions.append((name, qs[0]))

    lines = [f"⏱️ **Mock exam for {syllabus_id}** — {len(questions)} questions, ~{len(questions) * 10} minutes", ""]
    for i, (name, q) in enumerate(questions, 1):
        lines.append(f"**{i}. [{name}]** {q['question']}")
    lines.append("\n**Marking key** (for the tutor):")
    for i, (name, q) in enumerate(questions, 1):
        lines.append(f"  {i}. {q['answer']}")
    return "\n".join(lines)


@mcp.tool()
def generate_bug_hunt(concept: str) -> str:
    """Generate a worked solution with a deliberate error for the student to find.

    Args:
        concept: Concept (derivative, integral, determinant, bayes, variance).
    """
    x = sp.Symbol("x")
    bugs = {
        "derivative": {
            "problem": "Differentiate f(x) = 3x².",
            "buggy": "f'(x) = 6x²",
            "fix": "f'(x) = 6x (multiply by the exponent, then reduce it by one).",
        },
        "integral": {
            "problem": "Integrate f(x) = 2x.",
            "buggy": "∫ 2x dx = 2x²",
            "fix": "∫ 2x dx = x² + C (divide by the new exponent).",
        },
        "determinant": {
            "problem": "Compute det([[1, 2], [3, 4]]).",
            "buggy": "det = 1·4 + 2·3 = 10",
            "fix": "det = 1·4 − 2·3 = −2 (the formula is ad − bc).",
        },
        "bayes": {
            "problem": "P(A)=0.1, P(+|A)=0.9, P(+|¬A)=0.2. Find P(A|+).",
            "buggy": "P(A|+) = 0.9 (using only the sensitivity)",
            "fix": "P(A|+) = (0.9·0.1)/(0.9·0.1 + 0.2·0.9) ≈ 0.33 (normalise by total probability).",
        },
        "variance": {
            "problem": "X and Y independent, Var(X)=Var(Y)=1. Compute Var(X + Y).",
            "buggy": "Var(X + Y) = 1 + 1 + 2·1 = 4",
            "fix": "Independence ⇒ no covariance term: Var(X+Y) = 1 + 1 = 2.",
        },
    }
    key = concept.lower().strip()
    b = bugs.get(key)
    if b is None:
        for k, v in bugs.items():
            if k in key or key in k:
                b = v
                break
    if b is None:
        return "❌ No bug-hunt template for that concept. Try: derivative, integral, determinant, bayes, variance."

    return (
        f"🐛 **Spot the error** ({concept})\n\n"
        f"**Problem:** {b['problem']}\n\n"
        f"**Student's worked solution:**\n{b['buggy']}\n\n"
        f"*(Ask the student to find and explain the mistake. Then reveal the fix.)*\n\n"
        f"**Fix:** {b['fix']}"
    )


if __name__ == "__main__":
    mcp.run()
