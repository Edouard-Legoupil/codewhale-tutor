---
name: linear-algebra
description: Linear algebra problem-solving and Socratic tutoring — linear systems, matrix calculus, diagonalisation, symmetric matrices, Euclidean spaces, Gram-Schmidt, least squares, and bilinear/quadratic forms.
invocation: model+user
---

# 📐 Linear Algebra (Algèbre linéaire)

Use this skill for matrix calculus, linear systems, diagonalisation, Euclidean
spaces, and related linear algebra. Guide the student Socratically — never
spell out the full solution; verify each step with `check_math` when a
calculation is claimed.

## The 4-Step Process

1. **Understand** — What is given (matrix, vector, space)? What is asked
   (diagonalise, invert, solve, orthonormalise)?
2. **Devise a plan** — Which tool: Gaussian elimination, determinant, characteristic
   polynomial, Gram-Schmidt, projection formula, normal equations?
3. **Carry out** — One row/column operation at a time; state invariants.
4. **Look back** — Substitute, check dimensions, verify eigenvectors against the
   eigenvalue.

## Key Concepts (MIASHS syllabus)

### Linear systems (Systèmes linéaires)
- Gaussian elimination / row echelon form; pivot, rank, number of solutions.
- **Socratic:** *"How many pivots do you expect? What does a zero row tell you?"*

### Matrix calculus (Calcul matriciel)
- Change of basis, inversion (2×2 and block), determinant, transpose.
- **Pitfalls:** forgetting `det(A·B) = det(A)·det(B)`; sign flips in cofactor expansion;
  assuming `(AB)⁻¹ = A⁻¹B⁻¹` (it's `B⁻¹A⁻¹`).

### Diagonalisation
- Eigenvalues/vectors (`valeurs/vecteurs propres`), characteristic polynomial
  (`polynôme caractéristique`), eigenspaces (`sous-espaces propres`).
- A matrix is diagonalisable iff it has n linearly independent eigenvectors.
- **Socratic:** *"What is the algebraic multiplicity vs. the geometric
  multiplicity? When do they force non-diagonalisability?"*
- **Check:** compute `Matrix([[...], ...]).eigenvals()` and
  `.eigenvects()` with `check_math`.

### Symmetric matrices & Euclidean spaces
- `A` symmetric ⇒ real eigenvalues, orthogonal eigenvectors, diagonalisable by an
  orthogonal matrix.
- Scalar product (`produit scalaire`), norm, orthogonality.

### Gram-Schmidt & projections
- Algorithm and matrix form; orthonormal bases; orthogonal projection onto a subspace.
- **Pitfall:** normalising at each step vs. once at the end; projecting onto the
  wrong subspace.

### Least squares (Moindres carrés)
- Normal equations `AᵀA x = Aᵀb`; geometric meaning (projection onto `Im A`).
- **Socratic:** *"Why is `Aᵀ(b − Ax) = 0` the orthogonality condition?"*

### Bilinear & quadratic forms
- Symmetric bilinear form ↔ quadratic form; sign (definite/semi-definite);
  Sylvester's law of inertia (light touch).

## Common Mistakes

| Mistake | Prevention |
| :--- | :--- |
| Sign errors in cofactor expansion | Expand along the row/column with most zeros |
| Confusing eigenvectors with eigenvalues | Recompute `A·v` and check it equals `λ·v` |
| Not checking dimensions | Write matrix shapes before multiplying |
| Forgetting to normalise | Track `‖v‖` after every Gram-Schmidt step |
| Wrong change-of-basis direction | Always test on a known vector |

## Exam Strategy

1. Scan for the easy marks (determinant, inversion, a 2×2 diagonalisation).
2. Show the characteristic polynomial explicitly — partial credit.
3. Verify every eigenvalue by substitution before moving on.
4. For symmetric matrices, check orthogonality of eigenvectors as a self-check.

## Guided Practice Template

**Student:** "I can't diagonalise this matrix."

**Tutor:**
```text
1️⃣ Write down the characteristic polynomial det(A − λI).
2️⃣ Factor it — what are the eigenvalues and their multiplicities?
3️⃣ For each eigenvalue, solve (A − λI)v = 0 for the eigenspace.
4️⃣ Do the dimensions of the eigenspaces match the multiplicities?

[Verify each step with check_math before proceeding.]
```
