"""Transcribe → confirm → solve → verify → report.

This is the only way a solution reaches the student. Later phases (video,
HTML write-up) must call :func:`run` and refuse to render unless
``result.verified`` is True.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import sympy as sp

from tutor.text.latex import tex
from tutor.errors import NotConfirmed
from tutor.parse.schema import Problem, save_problem
from tutor.steps import Solution
from tutor.text.unicode_math import to_text
from tutor.verify import PASS, CheckResult, overall, verify
from tutor.verify.report import render_report

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = PROJECT_ROOT / "videos"


def _solver_for(ptype: str):
    from tutor import registry

    return registry.get(ptype).solve


@dataclass
class PipelineResult:
    solution: Solution
    checks: list[CheckResult]
    status: str
    out_dir: Path | None = None

    @property
    def verified(self) -> bool:
        return self.status == PASS


def solve_problem(problem: Problem, *, require_confirmation: bool = True) -> PipelineResult:
    if require_confirmation and not problem.confirmed_by_student:
        raise NotConfirmed(
            "The student has not confirmed this transcription yet. Show it with "
            "`python -m tutor show <problem.json>` and ask 'Is this exactly the problem?'"
        )
    solution = _solver_for(problem.type)(problem)
    checks = verify(solution)
    return PipelineResult(solution=solution, checks=checks, status=overall(checks))


def output_dir(problem: Problem, base: Path = VIDEOS_DIR) -> Path:
    return base / problem.course / problem.topic / problem.slug


def _jsonable(v):
    if isinstance(v, sp.MatrixBase):
        return {"matrix": [[str(v[i, j]) for j in range(v.cols)] for i in range(v.rows)],
                "latex": tex(v), "text": to_text(v)}
    if isinstance(v, sp.Basic):
        return {"srepr": sp.srepr(v), "latex": tex(v, order="none"), "text": to_text(v)}
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


def solution_json(result: PipelineResult) -> dict:
    s = result.solution
    return {
        "slug": s.problem.slug,
        "status": result.status,
        "digest": s.digest(),
        "answer_label": s.answer_label,
        "answer": _jsonable(s.answer),
        "notes": s.notes,
        "steps": [
            {
                "id": st.id,
                "kind": st.kind,
                "operation": st.operation,
                "justification": st.justification,
                "before": _jsonable(st.before),
                "after": _jsonable(st.after),
                "data": _jsonable({k: v for k, v in st.data.items() if k != "rowop"}),
            }
            for st in s.steps
        ],
    }


def write_outputs(result: PipelineResult, out_dir: Path | None = None) -> Path:
    out = out_dir or output_dir(result.solution.problem)
    out.mkdir(parents=True, exist_ok=True)
    save_problem(result.solution.problem, out / "problem.json")
    (out / "verification_report.md").write_text(render_report(result.solution, result.checks), encoding="utf-8")
    (out / "solution.json").write_text(json.dumps(solution_json(result), indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8")
    result.out_dir = out
    return out


def run(problem: Problem, *, out_dir: Path | None = None, require_confirmation: bool = True) -> PipelineResult:
    """Solve, verify, and write problem.json / solution.json / verification_report.md."""
    result = solve_problem(problem, require_confirmation=require_confirmation)
    write_outputs(result, out_dir)
    return result
