---
name: exam-technique
description: Maximise exam marks through technique — decoding command words, time allocation by mark scheme, mock exams, calibration, and deep-practice drills (bug hunting, teach-back, blank-page retrieval).
invocation: model+user
---

# 🎯 Exam Technique (marks, not just knowledge)

Use this skill to convert knowledge into marks: interpreting what a question is
*really* asking, allocating time by the mark scheme, and using evidence-based
practice techniques. Apply it during revision and when running mock exams.

## Decode the command word (French papers)

Each verb demands a specific structure and earns marks differently:

| Command | What the examiner wants | Marks come from |
| :--- | :--- | :--- |
| `démontrer` / `montrer que` | A chain of valid deductions | Each logical step, stated hypotheses |
| `calculer` / `résoudre` | A correct result with method shown | Method + final answer |
| `justifier` | A reason, not just a claim | The *why*, with a theorem/rule named |
| `énoncer` | State a definition/theorem precisely | Exact statement, notation, conditions |
| `déterminer` | Find a value with justification | Correct value + method |
| `comparer` | Similarities and differences | Both sides, evidence |
| `discuter` | Analyse both sides | Balanced argument, conclusion |
| `vérifier` | Substitute / test a claim | Explicit check, not restatement |
| `interpréter` | Explain meaning in context | Units, context, plain language |

- **Socratic:** *"What is this question actually asking you to *do*? What would a
  full-mark answer have to contain?"*

## Time & mark-scheme allocation (barème)

- Work out **marks per minute**: `total marks ÷ total minutes`. Spend accordingly.
- Never spend more time than a question's marks justify — a 2-mark lemma is a
  stepping stone, not an essay.
- If the barème is known, tell the student which proof steps carry marks so they
  don't polish an ungraded part.

## Mock exams under time pressure

- Run a full timed paper (`generate_mock_exam`), no notes, then score it.
- Report **marks per minute per question** and where time was lost.
- Interleave topics (mixed papers), because exams are mixed and blocked practice
  creates false confidence.

## Calibration: "know what you don't know"

- Before revealing an answer, ask: *"How confident are you, 0–100%?"*, then
  record it with `record_attempt` (`predicted_confidence` + `correct`).
- Use `get_calibration` to expose overconfidence — the overconfident student
  revises the wrong things.

## Deep-practice drills

- **Blank-page retrieval** — after a cheatsheet, hide it and have the student
  reconstruct it from memory. Retrieval beats re-reading.
- **Bug hunting** — present a worked solution with a deliberate error
  (`generate_bug_hunt`) and ask the student to find and explain it. Trains
  verification, the skill behind "check your answers".
- **Teach-back** — play a confused peer and have the student explain until you
  "get it". The protégé effect deepens understanding.

## Exam-day protocol

1. **Reading time** — triage: which questions are easy marks? Do those first.
2. **Brain dump** — write the formula sheet from memory at the start, while it's fresh.
3. **Order** — easy → medium → hard; never stall on one question.
4. **Check** — reserve the last 10 minutes to hunt for sign/units/range errors
   (use `sanity_check` on any suspicious number).

## Summary checklist

- [ ] Decoded every command word
- [ ] Allocated time by marks
- [ ] Took a timed mock under exam conditions
- [ ] Calibrated confidence on recent attempts
- [ ] Did retrieval, not just re-reading
- [ ] Reserved checking time on the day
