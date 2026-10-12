"""LaTeX for verified objects (videos and HTML write-ups).

Everything shown as math comes from ``sympy.latex`` of a verified object.
Hand-built (unevaluated) lines keep the order the solver built them in.
"""

from __future__ import annotations

import sympy as sp

from tutor.text.unicode_math import _built_by_hand

GREEK = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon", "θ": "theta", "λ": "lambda",
         "μ": "mu", "π": "pi", "ρ": "rho", "σ": "sigma", "τ": "tau", "φ": "phi", "ω": "omega", "Δ": "Delta"}
SUBSCRIPT = dict(zip("₀₁₂₃₄₅₆₇₈₉", "0123456789"))
CHARS = {"−": "-", "′": "'", "·": r"\cdot ", "≤": r"\le ", "≥": r"\ge ", "→": r"\to ", "∞": r"\infty ",
         "⁻¹": "^{-1}", "ᵀ": "^{T}", "²": "^{2}", "³": "^{3}", "√": r"\surd "}


def symbol_tex(name: str) -> str:
    """LaTeX for a Symbol name that contains Unicode (λ₁ → \\lambda_{1}, f⁻¹(x) → f^{-1}(x))."""
    out = name
    for k, v in CHARS.items():
        out = out.replace(k, v)
    for k, v in GREEK.items():
        out = out.replace(k, f"\\{v} ")
    m = "".join(SUBSCRIPT.get(c, "") for c in out)
    if m:
        out = "".join(c for c in out if c not in SUBSCRIPT) + "_{" + m + "}"
    out = out.replace(" _", "_").replace(" (", "(").strip()
    return out


def tex(obj, **kwargs) -> str:
    """sympy.latex, with Unicode symbol names turned into LaTeX commands (pdflatex can't typeset λ)."""
    try:
        atoms = obj.atoms(sp.Symbol) if hasattr(obj, "atoms") else set()
    except Exception:  # noqa: BLE001
        atoms = set()
    names = {a: symbol_tex(a.name) for a in atoms if not a.name.isascii()}
    if names:
        kwargs["symbol_names"] = {**kwargs.get("symbol_names", {}), **names}
    return sp.latex(obj, **kwargs)


def latex_of(e, augmented_at: int | None = None) -> str:
    if isinstance(e, sp.MatrixBase):
        if augmented_at is not None and 0 < augmented_at < e.cols:
            spec = "c" * augmented_at + "|" + "c" * (e.cols - augmented_at)
            rows = r" \\ ".join(" & ".join(tex(e[i, j]) for j in range(e.cols)) for i in range(e.rows))
            return r"\left[\begin{array}{" + spec + "}" + rows + r"\end{array}\right]"
        return tex(e)
    if isinstance(e, (list, tuple)):
        if e and all(isinstance(q, sp.Equality) for q in e):
            return r"\begin{aligned}" + r"\\".join(latex_of(q).replace("=", "&=", 1) for q in e) + r"\end{aligned}"
        return r",\quad ".join(latex_of(q) for q in e)
    if isinstance(e, dict):
        return r",\quad ".join(f"{latex_of(k)}: {latex_of(v)}" for k, v in e.items())
    if isinstance(e, str):
        return r"\text{" + e.replace("_", " ") + "}"
    e = sp.sympify(e)
    hand = any(_built_by_hand(n) for n in sp.preorder_traversal(e) if isinstance(n, (sp.Add, sp.Mul)))
    return tex(e, order="none") if hand else tex(e)
