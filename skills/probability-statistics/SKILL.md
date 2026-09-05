---
name: probability-statistics
description: Probability and statistics tutoring — discrete and continuous random variables, expectation/variance, common distributions, conditional probability and Bayes, pairs of variables, and statistical estimation.
invocation: model+user
---

# 🎲 Probability & Statistics (Probabilités / Statistique)

Use this skill for random variables, distributions, conditional probability,
Bayes' rule, and statistical estimation. Emphasise *modelling* before computing:
what is the experiment, what is the variable, what distribution applies?

## Core Framework

1. **Model** — Name the random variable and its distribution; justify the choice.
2. **Compute** — Expectation, variance, probability of an event.
3. **Interpret** — Units, plausibility, and what the number means.

## Discrete random variables (Variables aléatoires discrètes)

- Expectation `E[X]` (definition, linearity, transfer theorem), variance
  `Var(X) = E[X²] − E[X]²`, standard deviation, moments.
- Markov and Bienaymé-Tchebychev inequalities.
- **Socratic:** *"Why does linearity of expectation hold even for dependent
  variables?"*

### Common laws (Lois usuelles)
| Law | Support | E | Var |
| :--- | :--- | :--- | :--- |
| Bernoulli(p) | {0,1} | p | p(1−p) |
| Binomial(n,p) | 0..n | np | np(1−p) |
| Poisson(λ) | ℕ | λ | λ |
| Geometric(p) | ℕ⁺ | 1/p | (1−p)/p² |
| Uniform(1..n) | 1..n | (n+1)/2 | (n²−1)/12 |

- **Socratic:** *"When is a binomial the right model? When does Poisson
  approximate it?"*

### Conditional probability & Bayes
- `P(A|B)`, total probability (`probabilités totales`), Bayes' formula, independence.
- **Pitfalls:** confusing `P(A|B)` with `P(B|A)`; forgetting to normalise in Bayes.

### Pairs of discrete variables (Couples de VA)
- Joint, marginal, and conditional laws; independence; covariance;
  `Var(X+Y) = Var(X) + Var(Y) + 2Cov(X,Y)`.

## Continuous random variables (Variables aléatoires continues)

- Density, cumulative distribution function (`fonction de répartition`), quantiles.
- Uniform, exponential, normal laws; expectation and variance; method of test
  functions (`méthode des fonctions tests`).
- Pairs with density: marginal density, covariance, density of a transformed
  pair, density of a sum, independence.
- **Simulation:** inverse CDF method and Box-Müller for normal variables.
- **Pitfalls:** forgetting the Jacobian when transforming densities; mixing up
  `f(x)` and `F(x)`.

## Statistical estimation (Statistique inférentielle)

- Estimator (`estimateur`), bias, variance, and mean squared error
  (`risque quadratique moyen`, MSE = bias² + variance).
- Comparing estimators across models.
- **Socratic:** *"An estimator can be unbiased but terrible. Why? How does MSE
  capture that trade-off?"*

## Common Mistakes

| Mistake | Prevention |
| :--- | :--- |
| Mixing P(A|B) and P(B|A) | Write Bayes' formula explicitly |
| Forgetting normalisation in a density | Check ∫f = 1 |
| Variance of a sum for dependent variables | Include the covariance term |
| Confusing density and CDF | Differentiate/integrate and re-check |
| Wrong distribution choice | State the assumptions out loud first |

## Exam Strategy

1. State the model and distribution before any calculation (marks).
2. Write expectations/variance formulas explicitly.
3. For conditional problems, draw the tree or table.
4. Check results are in range (probabilities in [0,1], variances ≥ 0).

## Guided Practice Template

**Student:** "I can't start this probability question."

**Tutor:**
```text
1️⃣ What is the random experiment?
2️⃣ What is the random variable, and what law does it follow (and why)?
3️⃣ What exactly is being asked — an expectation, a probability, a density?
4️⃣ Which formula connects your model to the answer?

[Use check_math to verify sums, integrals, and simplifications.]
```
