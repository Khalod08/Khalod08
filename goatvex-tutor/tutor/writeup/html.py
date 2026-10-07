"""KaTeX HTML pages: solution write-ups, practice sheets, mock tests, progress reports.

Every formula on a page is ``latex_of`` a verified object (or LaTeX produced by
the verified pipeline, e.g. ``practice_tex``). Prose comes from the solver's
own step labels and justifications, which were built from verified data.

Pages are self-contained HTML files that load KaTeX from a CDN, so they work
when opened straight from disk (``file://``) and print cleanly.
"""

from __future__ import annotations

import html
import os
import webbrowser
from pathlib import Path

import sympy as sp

from tutor import registry
from tutor.steps import ALGEBRA, DERIVATIVE_RULE, EQUATION, INTEGRAL_RULE, LIMIT_STEP, ROW_OP
from tutor.text.latex import latex_of

EQUAL_KINDS = {ALGEBRA, DERIVATIVE_RULE, INTEGRAL_RULE, LIMIT_STEP, ROW_OP}  # shown as "before = after"

KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist"

CSS = """
:root { --bg:#fbfaf7; --fg:#1f2328; --muted:#5b6470; --card:#ffffff; --line:#e4e1da;
        --accent:#2a7f86; --gold:#b8860b; --good:#2e7d32; --warn:#c0563b; --soft:#eef6f6; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --bg:#16181d; --fg:#e8e6e3; --muted:#a3a9b3; --card:#1f232a; --line:#2f343d;
        --accent:#5cc3c9; --gold:#e3b341; --good:#6cc070; --warn:#ef8a6e; --soft:#1d2b2d; }
}
:root[data-theme="dark"] { --bg:#16181d; --fg:#e8e6e3; --muted:#a3a9b3; --card:#1f232a; --line:#2f343d;
        --accent:#5cc3c9; --gold:#e3b341; --good:#6cc070; --warn:#ef8a6e; --soft:#1d2b2d; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font: 17px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 860px; margin: 0 auto; padding: 24px 16px 64px; }
header .crumbs { color:var(--muted); font-size:14px; }
h1 { font-size: 28px; margin: 4px 0 12px; }
h2 { font-size: 20px; margin: 32px 0 8px; color: var(--accent); }
.card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px 18px; margin:12px 0; }
.problem { border-left: 4px solid var(--gold); }
.idea { background: var(--soft); }
.step .num { display:inline-block; min-width:28px; height:28px; line-height:28px; text-align:center; border-radius:14px;
             background:var(--accent); color:var(--bg); font-weight:600; font-size:14px; margin-right:8px; }
.step .op { font-weight:600; }
.step .why { color: var(--muted); margin-top: 6px; }
.math { overflow-x:auto; overflow-y:hidden; padding: 6px 0; }
.answer { border: 2px solid var(--good); }
.answer .label { color: var(--good); font-weight: 700; }
.notes li { margin: 4px 0; }
.verified { color: var(--good); font-weight: 600; }
.unverified { color: var(--warn); font-weight: 600; }
details summary { cursor: pointer; color: var(--accent); font-weight: 600; }
.toolbar { display:flex; gap:8px; flex-wrap:wrap; margin: 8px 0 0; }
button { font: inherit; padding: 6px 12px; border-radius: 8px; border:1px solid var(--line); background:var(--card);
         color:var(--fg); cursor:pointer; }
button:hover { border-color: var(--accent); }
.hidden-step { display: none; }
table { border-collapse: collapse; width: 100%; font-size: 15px; }
th, td { border-bottom: 1px solid var(--line); padding: 6px 8px; text-align: left; vertical-align: top; }
th { color: var(--muted); font-weight: 600; }
.bar { height: 8px; border-radius: 4px; background: var(--line); overflow: hidden; }
.bar > span { display:block; height:100%; background: var(--accent); }
.muted { color: var(--muted); }
.cite { font-size: 14px; color: var(--muted); }
video { width: 100%; border-radius: 12px; margin-top: 8px; }
@media print { .toolbar, button { display:none; } .hidden-step { display:block !important; } details { display:block; } }
"""

SCRIPT = """
document.addEventListener("DOMContentLoaded", function () {
  renderMathInElement(document.body, {delimiters: [
    {left: "$$", right: "$$", display: true}, {left: "\\\\(", right: "\\\\)", display: false}], throwOnError: false});
  const steps = Array.from(document.querySelectorAll(".step"));
  const one = document.getElementById("one-at-a-time"), all = document.getElementById("show-all"),
        next = document.getElementById("next-step");
  if (one) one.onclick = () => { steps.forEach((s, i) => s.classList.toggle("hidden-step", i > 0));
                                 next.style.display = "inline-block"; };
  if (all) all.onclick = () => { steps.forEach(s => s.classList.remove("hidden-step")); next.style.display = "none"; };
  if (next) next.onclick = () => { const h = steps.find(s => s.classList.contains("hidden-step"));
                                   if (h) { h.classList.remove("hidden-step"); h.scrollIntoView({behavior: "smooth", block: "center"}); }
                                   if (!steps.some(s => s.classList.contains("hidden-step"))) next.style.display = "none"; };
});
"""


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def display(tex: str) -> str:
    return f'<div class="math">$${esc(tex)}$$</div>'


def page(title: str, body: str, crumbs: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{KATEX}/katex.min.css">
<script defer src="{KATEX}/katex.min.js"></script>
<script defer src="{KATEX}/contrib/auto-render.min.js"></script>
<style>{CSS}</style>
<script>{SCRIPT}</script>
</head>
<body><main>
<header><div class="crumbs">{esc(crumbs)}</div><h1>{esc(title)}</h1></header>
{body}
<p class="muted" style="margin-top:40px">Made by GoatVex. Every formula on this page was computed by SymPy and checked
by the verifier before it was written here.</p>
</main></body></html>
"""


def _augmented_at(sol, obj) -> int | None:
    p = sol.problem
    if not isinstance(obj, sp.MatrixBase):
        return None
    if p.type == "matrix_inverse" and obj.cols == 2 * obj.rows:
        return obj.rows
    if p.type == "rref" and p.given.get("augmented") and obj.cols == p.matrix.cols:
        return obj.cols - 1
    return None


def _math(sol, obj) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return f'<div class="math">{esc(obj.replace("_", " "))}</div>'
    return display(latex_of(obj, _augmented_at(sol, obj)))


def _step_math(sol, st) -> str:
    before, after = st.before, st.after
    if (st.kind == EQUATION and isinstance(before, (sp.Equality, list)) and isinstance(after, (sp.Equality, list))):
        return display(latex_of(before) + r"\quad\Longleftrightarrow\quad " + latex_of(after))
    if (before is None or after is None or isinstance(before, str) or isinstance(after, str)
            or st.kind not in EQUAL_KINDS):
        return _math(sol, after if after is not None else before)
    if st.kind == ROW_OP and isinstance(before, sp.MatrixBase):
        aug = _augmented_at(sol, before)
        return display(latex_of(before, aug) + r"\;\longrightarrow\;" + latex_of(after, aug))
    if isinstance(before, (sp.MatrixBase, list, tuple, dict, sp.Equality)) or isinstance(after, (list, tuple, dict)):
        return _math(sol, after)
    if isinstance(after, sp.Equality):
        return _math(sol, after)
    return display(latex_of(before) + " = " + latex_of(after))


def statement_html(problem, describe_text: str | None = None, tex: str | None = None) -> str:
    from tutor.study.generate import practice_tex

    tex = tex if tex is not None else practice_tex(problem)
    parts = []
    if problem.statement:
        parts.append(f"<p>{esc(problem.statement)}</p>")
    if tex is None and "matrix" in problem.given:
        try:
            tex = "A = " + latex_of(problem.matrix)
        except Exception:  # noqa: BLE001
            tex = None
    if tex:
        parts.append(display(tex))
    elif describe_text:
        lines = [ln for ln in describe_text.splitlines()
                 if not ln.startswith(("Course:", "Confirmed by student", "Statement:"))]
        parts.append("<pre style='white-space:pre-wrap;font:inherit'>" + esc("\n".join(lines)) + "</pre>")
    return "".join(parts)


def sections_html(ptype: str) -> str:
    pt = registry.get(ptype)
    if not pt.sections:
        return ""
    bits = [f"{book} §{', '.join(secs)}" for book, secs in pt.sections.items()]
    return f'<p class="cite">Textbook: {esc("; ".join(bits))}</p>'


def solution_page(result, practice: dict | None = None, video: str | None = None,
                  citations: list[str] | None = None) -> str:
    """The full write-up for a verified solution."""
    from tutor.narration.generic import intuition_line, recap_line

    sol = result.solution
    p = sol.problem
    pt = registry.get(p.type)
    n_pass = sum(c.ok for c in result.checks)
    body = []
    body.append('<section class="card problem"><h2 style="margin-top:0">Problem</h2>'
                + statement_html(p, pt.describe(p)) + sections_html(p.type)
                + "".join(f'<p class="cite">{esc(c)}</p>' for c in (citations or [])) + "</section>")
    if video:
        body.append(f'<video controls src="{esc(video)}"></video>')
    body.append(f'<section class="card idea"><strong>The idea.</strong> {esc(intuition_line(p.type).caption())}</section>')
    body.append('<h2>Step by step</h2><p class="muted">Try each step on paper first, then reveal it.</p>'
                '<div class="toolbar"><button id="one-at-a-time">One step at a time</button>'
                '<button id="next-step" style="display:none">Next step ▸</button>'
                '<button id="show-all">Show all steps</button></div>')
    k = 0
    for st in sol.steps:
        k += 1
        body.append(f'<div class="card step"><span class="num">{k}</span><span class="op">{esc(st.operation)}</span>'
                    f'{_step_math(sol, st)}<div class="why">{esc(st.justification)}</div></div>')
    body.append(f'<section class="card answer"><span class="label">{esc(sol.answer_label)}</span>'
                f'{_math(sol, sol.answer)}</section>')
    if sol.notes:
        body.append('<ul class="notes">' + "".join(f"<li>{esc(n)}</li>" for n in sol.notes) + "</ul>")
    status = ('<span class="verified">✓ Verified</span>' if result.verified else
              f'<span class="unverified">✗ Not verified ({esc(result.status)})</span>')
    body.append(f'<p>{status}: {n_pass} of {len(result.checks)} checks passed (every step re-checked symbolically '
                'and at random numeric points, plus an independent second method for the answer). Details: '
                '<a href="verification_report.md">verification_report.md</a>.</p>')
    body.append(f'<h2>Recap</h2><p>{esc(recap_line(p.type).caption())}</p>')
    if practice:
        body.append(practice_html(practice))
    return page(pt.title, "\n".join(body), crumbs=f"{p.course} · {p.topic.replace('-', ' ')}")


def practice_html(practice: dict, heading: str = "Your turn") -> str:
    tex = practice.get("latex")
    stmt = esc(practice.get("statement", ""))
    shown = display(tex) if tex else ""
    return (f'<h2>{esc(heading)}</h2><div class="card problem"><p>{stmt}</p>{shown}'
            f'<details><summary>Show the answer (try it first!)</summary><p>{esc(practice["answer_text"])}</p>'
            '<p class="muted">Or type your answer to GoatVex and it will be checked.</p></details></div>')


def write(path: Path, content: str, open_browser: bool = False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if open_browser and not os.environ.get("GOATVEX_NO_BROWSER"):
        webbrowser.open(path.resolve().as_uri())
    return path


def write_solution(result, out_dir: Path | None = None, practice: dict | None | bool = True,
                   open_browser: bool = False) -> Path:
    """Write solution.html next to the verification report (verified results only)."""
    if not result.verified:
        raise ValueError("refusing to write a write-up for an unverified solution")
    out = out_dir or result.out_dir
    if practice is True:
        import json

        pj = out / "practice.json"
        if pj.exists():
            practice = json.loads(pj.read_text(encoding="utf-8"))
        else:
            from tutor.study.generate import practice_problem

            practice = practice_problem(result.solution.problem)
            if practice:
                pj.write_text(json.dumps(practice, indent=2, ensure_ascii=False), encoding="utf-8")
    video = next((v for v in ("solution.mp4", "preview.mp4") if (out / v).exists()), None)
    citations = None
    try:
        from tutor.materials.index import citations_for

        citations = citations_for(result.solution.problem)
    except Exception:  # noqa: BLE001  (materials are optional)
        citations = None
    html_text = solution_page(result, practice or None, video, citations)
    return write(out / "solution.html", html_text, open_browser)
