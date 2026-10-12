"""Narration lines whose math can only come from verified data.

A narration *template* is plain prose with ``{placeholders}``::

    "Now we {op}, which creates a zero below the pivot."

Each placeholder is filled with a :class:`Spoken` value built from a verified
SymPy object (``V(...)``) or row operation (``OP(...)``), which carries both
the words for the voice and the Unicode for the caption. The lint rejects any
template that contains a digit, a number word, a math word or a math symbol
outside a placeholder, so the narration cannot introduce math of its own.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass, field

from tutor.narration.spoken import number_words, say, say_row_op, say_vector
from tutor.text.unicode_math import to_text, vec_text


@dataclass(frozen=True)
class Spoken:
    say: str    # what the voice says
    show: str   # what the caption shows (readable Unicode)


def V(obj) -> Spoken:
    """A verified SymPy value (number, expression, equation)."""
    return Spoken(say(obj), to_text(obj))


def N(obj) -> Spoken:
    """A verified number, spoken as words (fractions as 'two thirds')."""
    return Spoken(number_words(obj), to_text(obj))


def OP(rowop) -> Spoken:
    return Spoken(say_row_op(rowop), rowop.text())


def VEC(v) -> Spoken:
    return Spoken(say_vector(v), vec_text(v))


def WORDS(text: str) -> Spoken:
    """Plain words chosen by code (e.g. 'augmented matrix'), not math. Linted like a template."""
    problems = lint_template(text)
    if problems:
        raise ValueError(f"WORDS() may not contain math: {problems}")
    return Spoken(text, text)


# ---------------------------------------------------------------- lint
NUMBER_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
    "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty",
    "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million",
    "half", "halves", "third", "thirds", "quarter", "quarters", "fifth", "fifths", "sixth", "sixths",
    "seventh", "sevenths", "eighth", "eighths", "ninth", "ninths", "tenth", "tenths", "twice", "double",
    "triple", "negative", "pi",
}
MATH_WORDS = {
    "plus", "minus", "times", "squared", "cubed", "equals", "sqrt", "sine", "cosine", "tangent", "secant",
    "cosecant", "cotangent", "infinity", "power",
}
MATH_SYMBOLS = set("=+−-×÷*/^²³⁴⁵⁶⁷⁸⁹⁰¹√∫∑∞≤≥≠<>πθλ₀₁₂₃₄₅₆₇₈₉")
# Fixed concept names that contain a number word but are not computed values.
ALLOWED_PHRASES = ["leading one", "leading ones", "one at a time", "one by one", "one entry", "one row",
                   "one more", "each one", "no one", "one side", "this one", "that one", "one step",
                   "one-to-one", "one variable", "one equation", "one solution", "one point", "one line",
                   "zero row", "zero rows", "tangent line", "tangent lines", "a zero", "zeros", "zero below", "zero above", "the zero"]


def lint_template(template: str) -> list[str]:
    """Problems with a narration template (empty list = clean)."""
    text = re.sub(r"\{[^{}]*\}", " ", template)  # placeholders are allowed to hold math
    text = re.sub(r"(?<=[A-Za-z])-(?=[A-Za-z])", " ", text)  # hyphenated words (write-up) are not minus signs
    low = text.lower()
    for phrase in ALLOWED_PHRASES:
        low = low.replace(phrase, " ")
    problems = []
    if re.search(r"\d", low):
        problems.append(f"contains a digit: {template!r}")
    sym = sorted({ch for ch in low if ch in MATH_SYMBOLS})
    if sym:
        problems.append(f"contains math symbol(s) {''.join(sym)}: {template!r}")
    words = set(re.findall(r"[a-z]+", low))
    bad = sorted((words & NUMBER_WORDS) | (words & MATH_WORDS))
    if bad:
        problems.append(f"contains number/math word(s) {bad} outside a placeholder: {template!r}")
    return problems


@dataclass
class Line:
    template: str
    values: dict[str, Spoken] = field(default_factory=dict)

    def problems(self) -> list[str]:
        out = lint_template(self.template)
        names = {f[1] for f in string.Formatter().parse(self.template) if f[1]}
        for n in sorted(names - set(self.values)):
            out.append(f"placeholder {{{n}}} has no verified value")
        for n, v in self.values.items():
            if not isinstance(v, Spoken):
                out.append(f"value for {{{n}}} is not a Spoken built from verified data")
        return out

    def spoken(self) -> str:
        return self.template.format(**{k: v.say for k, v in self.values.items()})

    def caption(self) -> str:
        return self.template.format(**{k: v.show for k, v in self.values.items()})


def lint_script(lines: list[Line]) -> list[str]:
    out = []
    for ln in lines:
        out += ln.problems()
    return out
