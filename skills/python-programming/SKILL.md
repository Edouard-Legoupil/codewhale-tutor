---
name: python-programming
description: Python programming tutoring — functions, dictionaries, file I/O, REST APIs, and object-oriented programming (classes, attributes, methods).
invocation: model+user
---

# 🐍 Python Programming (Structures de données & POO)

Use this skill for Python: functions, dictionaries, reading/writing files,
fetching data from REST APIs, and object-oriented programming. Prefer *asking
the student to predict behaviour* over simply showing code.

## Guiding Principles

1. **Predict before running** — "What do you think this prints? Why?"
2. **State the data flow** — inputs → processing → outputs.
3. **Test on small cases** — trace with a tiny example by hand.

## Functions

- Parameters vs. arguments; return values; scope; default/mutable-argument trap.
- **Socratic:** *"Why does modifying a list passed to a function surprise you?
  What's the difference between mutating and rebinding?"*

## Dictionaries

- Keys must be hashable; lookup is O(1); `dict.get`, `items()`, `defaultdict`, `Counter`.
- **Pitfalls:** mutating a dict while iterating; assuming insertion order is
  guaranteed everywhere (it is for `dict`, not for every mapping).

## File I/O (Lecture / écriture dans des fichiers)

- `with open(...) as f`; text vs. binary; `csv` module; encoding.
- **Socratic:** *"Why use `with`? What happens if you forget to close a file?"*
- **Pitfall:** leaving newline characters; reading a huge file into memory at once.

## REST APIs (Récupération de données)

- `requests.get`, status codes, JSON decoding, query parameters, headers, rate limits.
- **Pitfall:** not checking `response.status_code` or `raise_for_status()`.
- **Socratic:** *"How would you handle a 429 (rate limit) or a timeout?"*

## Object-oriented programming (POO)

- Class vs. instance; `__init__`, attributes, methods, `self`.
- **Socratic:** *"What is the difference between a class attribute and an
  instance attribute? When would each be appropriate?"*
- **Pitfall:** forgetting `self`; mutating a class-level mutable default.

## Common Mistakes

| Mistake | Prevention |
| :--- | :--- |
| Mutable default argument | Default to `None`, then initialise inside |
| Mutating while iterating | Iterate over a copy or collect changes |
| Ignoring HTTP errors | Always check status / `raise_for_status()` |
| Confusing class vs. instance state | Trace `self.x` vs `Class.x` |
| Not closing files | Use `with` |

## Exam Strategy

1. Trace the code by hand on paper first — partial credit for the right trace.
2. Identify the data type of every variable.
3. Watch for the classic traps (mutable defaults, aliasing, off-by-one).

## Guided Practice Template

**Student:** "My code doesn't work and I don't know why."

**Tutor:**
```text
1️⃣ What is the expected output vs. the actual output (paste the traceback)?
2️⃣ What are the types/values of the variables at the point of failure?
3️⃣ Can you reproduce it with a minimal 5-line example?
4️⃣ What does the error message literally say?

[Guide the student to state a hypothesis, then test it — don't hand them the fix.]
```
