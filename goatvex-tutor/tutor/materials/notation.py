"""Detect the professor's notation in the course materials, and apply it.

Detection counts patterns in the extracted text (lecture notes and slides
count three times as much as the textbook, since the professor's own
notation is what the student sees in class and on tests). The result is:

* materials/<course>/notation.md: readable, with counts and where each
  convention was seen (committed: it's our own summary)
* materials/<course>/notation.json: settings GoatVex applies automatically:
  - rowop_style: "right_arrow" (R₂ → R₂ − 3R₁), "left_arrow" (R₂ ← R₂ − 3R₁) or
    "result_right" (R₂ − 3R₁ → R₂). Used in captions, write-ups and step labels.
  - params: names for free parameters, e.g. ["s", "t"] or ["t₁", "t₂"]
  - plus conventions GoatVex follows when writing in chat (transpose, det,
    derivative notation, inverse trig, log), listed in notation.md.

Missing files or no evidence → the defaults below, which match the textbooks.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from tutor.pipeline import PROJECT_ROOT

DEFAULTS = {"rowop_style": "right_arrow", "row_letter": "R", "params": None, "transpose": "Aᵀ",
            "determinant": "det(A)", "derivative": "f′(x)", "inverse_trig": "arcsin", "natural_log": "ln",
            "rref_term": "reduced row echelon form (RREF)"}

R = r"[Rr]\s*_?\{?\s*\d\s*\}?"
ARROW_R = r"(?:→|->|⟶|\\to|\\rightarrow)"
ARROW_L = r"(?:←|<-|⟵|\\leftarrow)"
OP = r"[-−+]\s*\(?[\d/]*\)?\s*"
PATTERNS = {
    ("rowop_style", "right_arrow"): rf"{R}\s*{ARROW_R}\s*(?:\(?[\d/−-]*\)?\s*)?{R}",
    ("rowop_style", "left_arrow"): rf"{R}\s*{ARROW_L}\s*(?:\(?[\d/−-]*\)?\s*)?{R}",
    ("rowop_style", "result_right"): rf"{R}\s*{OP}{R}\s*{ARROW_R}\s*{R}",
    ("row_letter", "R"): r"\bR\s*_?\{?\d\}?\s*(?:→|->|←|↔|<->|\+|−|-)",
    ("row_letter", "r"): r"\br\s*_?\{?\d\}?\s*(?:→|->|←|↔|<->|\+|−|-)",
    ("transpose", "Aᵀ"): r"\b[A-Z]\s*(?:\^\s*\{?T\}?|ᵀ)",
    ("transpose", "Aᵗ"): r"\b[A-Z]\s*(?:\^\s*\{?t\}?|ᵗ)",
    ("transpose", "A′"): r"\b[A-Z](?:'|′)(?=\s|[,.)=])",
    ("determinant", "det(A)"): r"\bdet\s*\(?\s*[A-Z]",
    ("determinant", "|A|"): r"\|\s*[A-Z]\s*\|",
    ("derivative", "f′(x)"): r"\b[fgy]\s*(?:'|′)\s*\(",
    ("derivative", "dy/dx"): r"\bd\s*y\s*/\s*d\s*x\b",
    ("inverse_trig", "arcsin"): r"\barc(?:sin|cos|tan)\b",
    ("inverse_trig", "sin⁻¹"): r"\b(?:sin|cos|tan)\s*(?:\^\s*\{?\s*-\s*1\s*\}?|⁻¹|−1)",
    ("natural_log", "ln"): r"\bln\s*\(?",
    ("natural_log", "log"): r"\blog\s*\(",
    ("rref_term", "reduced row echelon form (RREF)"): r"reduced row[- ]echelon|\bRREF\b",
    ("rref_term", "reduced echelon form"): r"reduced echelon form",
}
PARAMS = re.compile(r"\bx\s*_?\{?\s*\d\s*\}?\s*=\s*([str]|t\s*_?\{?\s*\d\s*\}?|[α-ω])\s*(?:[,;.)]|\n|$)")
SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def detect(extracted: list[dict], files: dict[str, dict]) -> dict:
    """{setting: {"value": …, "counts": {option: n}, "seen": [where …]}} from the extracted pages."""
    counts: dict[str, Counter] = {}
    seen: dict[tuple[str, str], list[str]] = {}
    params = Counter()
    for doc in extracted:
        meta = files.get(doc["file"], {})
        if meta.get("kind") == "outline":
            continue
        weight = 1 if meta.get("kind") == "textbook" else 3
        unit = "slide" if meta.get("slides") else "p."
        for i, text in enumerate(doc["pages"], 1):
            for (setting, option), pat in PATTERNS.items():
                n = len(re.findall(pat, text))
                if n:
                    counts.setdefault(setting, Counter())[option] += weight * n
                    where = seen.setdefault((setting, option), [])
                    if len(where) < 4:
                        where.append(f"{meta.get('label', doc['file'])}, {unit} {i}")
            for m in PARAMS.finditer(text):
                params[re.sub(r"\s|_|\{|\}", "", m.group(1))] += weight
    out = {}
    for setting, default in DEFAULTS.items():
        if setting == "params":
            continue
        c = counts.get(setting, Counter())
        # "result_right" also matches the right-arrow pattern; prefer it only when it is the majority form
        if setting == "rowop_style" and c:
            c = Counter(c)
            c["right_arrow"] = max(0, c["right_arrow"] - c["result_right"])
        value = c.most_common(1)[0][0] if c else default
        out[setting] = {"value": value, "counts": dict(c),
                        "seen": {opt: seen.get((setting, opt), []) for opt in c}}
    if params:
        letters = [p for p, _ in params.most_common()]
        if any(re.fullmatch(r"t\d", p) for p in letters[:2]):
            value = ["t₁", "t₂", "t₃"]
        else:
            singles = [p for p in letters if len(p) == 1][:3]
            value = sorted(singles, key=lambda p: "rst".find(p) if p in "rst" else 9)
        out["params"] = {"value": value, "counts": dict(params), "seen": {}}
    else:
        out["params"] = {"value": None, "counts": {}, "seen": {}}
    return out


EXAMPLES = {"right_arrow": "R₂ → R₂ − 3R₁", "left_arrow": "R₂ ← R₂ − 3R₁", "result_right": "R₂ − 3R₁ → R₂"}


def write_notation(course: str, notes: dict, folder: Path) -> None:
    settings = {k: v["value"] for k, v in notes.items()}
    (folder / "notation.json").write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
                                          encoding="utf-8")
    lines = [f"# {course}: the professor's notation", "",
             "Detected automatically from the course materials by `python -m tutor materials ingest`.",
             "GoatVex uses these conventions in chat, write-ups, captions and videos. Lecture notes and slides",
             "count three times as much as the textbook. If something looks wrong, edit `notation.json`",
             "(the settings GoatVex applies) and add a note here.", "",
             "| Convention | GoatVex uses | Evidence (weighted counts) | Seen in |", "|---|---|---|---|"]
    names = {"rowop_style": "Row operations", "row_letter": "Row names", "params": "Free parameters",
             "transpose": "Transpose", "determinant": "Determinant", "derivative": "Derivative",
             "inverse_trig": "Inverse trig", "natural_log": "Natural log", "rref_term": "RREF"}
    for k, v in notes.items():
        val = v["value"]
        shown = EXAMPLES.get(val, val) if k == "rowop_style" else (", ".join(val) if isinstance(val, list) else val)
        if val is None:
            shown = "s, t (default: not detected)"
        ev = ", ".join(f"{opt}: {n}" for opt, n in sorted(v["counts"].items(), key=lambda t: -t[1])) or \
            "none found (default)"
        where = "; ".join(w for opt in v["seen"] for w in v["seen"][opt][:2]) or "—"
        lines.append(f"| {names.get(k, k)} | {shown} | {ev} | {where} |")
    (folder / "notation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if hasattr(settings_for, "cache_clear"):
        settings_for.cache_clear()


@lru_cache(maxsize=None)
def settings_for(course: str) -> dict:
    path = PROJECT_ROOT / "materials" / course / "notation.json"
    out = dict(DEFAULTS)
    if path.exists():
        try:
            out.update({k: v for k, v in json.loads(path.read_text(encoding="utf-8")).items() if v is not None})
        except (OSError, ValueError):
            pass
    return out


def param_letters(k: int, course: str = "MATH1104") -> list[str] | None:
    p = settings_for(course).get("params")
    if not p:
        return None
    if all(re.fullmatch(r"t[₀-₉]", q) for q in p):
        return [f"t{str(i + 1).translate(SUB)}" for i in range(k)]
    return list(p)[:k] if len(p) >= k else None
