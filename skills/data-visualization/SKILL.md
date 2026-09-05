---
name: data-visualization
description: Data sources, indicators, and visualization guidance — choosing the right chart, pandas/matplotlib usage, and interpreting plots critically.
invocation: model+user
---

# 📊 Data Visualization (Sources des données & indicateurs)

Use this skill for finding data sources, computing indicators, and producing or
interpreting visualizations. Emphasise *why* a chart is chosen and *what* it
actually shows — not just how to draw it.

## Framework: From question to chart

1. **Question** — What are you trying to show (comparison, trend, distribution,
   relationship, composition)?
2. **Data** — What is the source, unit, granularity, and known bias?
3. **Chart choice** — Match the chart to the question.
4. **Interpret** — State the finding and its limitations.

## Choosing the right chart

| Goal | Chart |
| :--- | :--- |
| Compare categories | Bar chart |
| Trend over time | Line chart |
| Distribution | Histogram / box plot |
| Relationship (2 numeric) | Scatter plot |
| Composition (parts of a whole) | Stacked bar / pie (rarely) |

- **Socratic:** *"Why is a pie chart usually worse than a bar chart for comparing
  many categories?"*

## Indicators & data sources (Indicateurs)

- Know the definition of each indicator (e.g. GDP, inflation/CPI, unemployment,
  inequality indices) and its unit.
- **Pitfalls:** comparing indicators with different bases; mixing nominal and
  real values; ignoring population size (per-capita vs. total).

## pandas / matplotlib essentials

- `pd.read_csv`, `.groupby`, `.describe`, `plt.plot/bar/scatter/hist`.
- **Pitfalls:** plotting raw counts vs. rates; misleading axes (truncated y-axis);
  unlabelled axes; colour scales that hide the message.

## Interpreting plots critically

- Is the scale honest? Are the axes labelled? Is the sample representative?
- Correlation vs. causation: a scatter trend does not imply a mechanism.
- **Socratic:** *"What alternative explanation could produce this same pattern?"*

## Common Mistakes

| Mistake | Prevention |
| :--- | :--- |
| Wrong chart for the question | State the goal before choosing |
| Truncated y-axis | Always start at zero for bars |
| Unlabelled axes/units | Label axis + unit every time |
| Correlation → causation | Look for confounders and mechanisms |
| Ignoring missing data | Report and handle NaN explicitly |

## Exam Strategy

1. Describe the chart first (what, where, when) before interpreting.
2. Quote specific numbers to support any claim.
3. Acknowledge limitations and alternative readings.

## Guided Practice Template

**Student:** "I have a dataset but don't know how to visualise it."

**Tutor:**
```text
1️⃣ What question are you trying to answer with this data?
2️⃣ What are the variable types (categorical / numeric / time)?
3️⃣ Which chart type matches that question and those types?
4️⃣ What would a misleading version of this chart look like, and how would you
   avoid it?
```
