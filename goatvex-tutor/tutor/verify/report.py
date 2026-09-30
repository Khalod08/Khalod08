"""verification_report.md: every check, PASS/FAIL, in readable Unicode."""

from __future__ import annotations

from datetime import datetime

from tutor.steps import Solution
from tutor.text.unicode_math import sub, to_text
from tutor.verify.result import FAIL, INCONCLUSIVE, PASS, CheckResult, overall

ICON = {PASS: "✅ PASS", FAIL: "❌ FAIL", INCONCLUSIVE: "⚠️ INCONCLUSIVE"}


def _cell(text: str) -> str:
    return text.replace("|", "│").replace("\n", "<br>")


def _matrix_table(m, bar: int | None = None, labels: list[str] | None = None) -> str:
    """A matrix as a Markdown table (readable anywhere, no code blocks, no LaTeX)."""
    head = labels or [" "] * m.cols
    cols = list(range(m.cols))

    def row(cells):
        out = []
        for j, c in zip(cols, cells):
            if bar is not None and j == bar:
                out.append("│")
            out.append(c)
        return "| " + " | ".join(out) + " |"

    lines = [row(head), row(["---"] * m.cols).replace("│", "---")]
    for i in range(m.rows):
        lines.append(row([to_text(m[i, j]) for j in cols]))
    return "\n".join(lines)


def _block(obj, bar: int | None = None, labels: list[str] | None = None) -> str:
    if hasattr(obj, "cols") and hasattr(obj, "rows"):
        return _matrix_table(obj, bar if bar is not None and obj.cols > bar else None, labels)
    return f"> {to_text(obj)}"


def _bar(solution: Solution) -> int | None:
    """Column before which to draw the │ of an augmented matrix."""
    p = solution.problem
    if p.type == "matrix_inverse":
        return solution.facts["n"]
    if p.type == "rref" and solution.facts.get("augmented"):
        return solution.facts["input"].cols - 1
    return None


def render_report(solution: Solution, results: list[CheckResult]) -> str:
    p = solution.problem
    status = overall(results)
    counts = {s: sum(r.status == s for r in results) for s in (PASS, FAIL, INCONCLUSIVE)}
    verdict = {
        PASS: "**ALL CHECKS PASSED** — this solution may be rendered.",
        FAIL: "**VERIFICATION FAILED** — no video or write-up will be produced from this solution.",
        INCONCLUSIVE: "**NOT FULLY VERIFIED** — some checks could not be proven, so nothing will be rendered.",
    }[status]

    lines = [
        f"# Verification report — `{p.slug}`",
        "",
        f"- **Course / topic:** {p.course} / {p.topic}",
        f"- **Type:** {p.type}",
        f"- **Generated:** {datetime.now().isoformat(timespec='seconds')}",
        f"- **Solution digest:** `{solution.digest()}`",
        f"- **Result:** {ICON[status]} — {verdict}",
        f"- **Checks:** {counts[PASS]} passed, {counts[FAIL]} failed, {counts[INCONCLUSIVE]} inconclusive",
        "",
        "## Problem (as confirmed)",
        "",
        p.statement or "_(no statement text)_",
        "",
    ]
    bar = _bar(solution)
    labels = None
    if p.type == "rref" and solution.facts.get("augmented"):
        labels = [f"x{sub(j + 1)}" for j in range(p.matrix.cols - 1)] + ["b"]
    if p.type == "rref":
        lines += [_block(p.matrix, bar, labels), ""]
    elif p.type == "matrix_inverse":
        lines += [_block(p.matrix), ""]
    elif p.type == "derivative":
        lines += [f"f({p.variable}) = {to_text(p.function)}", ""]

    lines += ["## Steps", ""]
    for s in solution.steps:
        lines += [f"**{s.id} — {s.operation}.** {s.justification}", "", _block(s.after, bar, labels), ""]

    lines += [f"## Answer: {solution.answer_label}", ""]
    if solution.problem.type == "matrix_inverse" and not solution.facts.get("invertible"):
        lines += ["A is not invertible.", ""]
    else:
        lines += [_block(solution.answer, bar if p.type == "rref" else None, labels), ""]
    for note in solution.notes:
        lines.append(f"- {note}")
    system = solution.facts.get("system")
    if system and system["status"] != "inconsistent":
        parts = ", ".join(f"x{sub(i + 1)} = {to_text(v)}" for i, v in enumerate(system["general"]))
        params = ", ".join(str(p_) for p_ in system["params"])
        lines.append(f"- Solution: {parts}" + (f"  ({params} any real number)" if params else ""))
    lines += ["", "## Checks", "", "| # | Step | Check | Result | Details |", "|---|---|---|---|---|"]
    order = {s.id: i for i, s in enumerate(solution.steps)}
    ordered = sorted(results, key=lambda r: order.get(r.step_id, len(order)))  # stable: keeps check order per step
    for i, r in enumerate(ordered, 1):
        lines.append(f"| {i} | {r.step_id} | {_cell(r.check)} | {ICON[r.status]} | {_cell(r.detail)} |")
    lines.append("")
    failed = [r for r in results if r.status != PASS]
    if failed:
        lines += ["## What could not be verified", ""]
        for r in failed:
            lines.append(f"- **{r.step_id} / {r.check}:** {r.detail}")
        lines.append("")
    return "\n".join(lines)
