"""Render a verified solution video.

    python -m tutor.video.render <problem.json>            # fast preview (480p15) + QA frames
    python -m tutor.video.render <problem.json> --final    # 1080p60, only after the preview passed QA

Outputs go to videos/<course>/<topic>/<slug>/:
  preview.mp4 / solution.mp4, solution.srt, timeline.json, qa_layout.json,
  frames/NN-<segment>.png (key frames for visual QA), practice.json (hidden answer).

Nothing is rendered unless the solution is fully verified, and the scene itself
re-verifies and checks the solution digest before drawing a single frame.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

import sympy as sp

from tutor import registry
from tutor.parse.schema import Problem, load_problem, problem_from_dict
from tutor.pipeline import PROJECT_ROOT, output_dir, run, solve_problem

TEMPLATES = PROJECT_ROOT / "tutor" / "video" / "templates"


def practice_problem(problem: Problem) -> dict | None:
    """A similar problem (different numbers, same method) with its verified answer."""
    pt = registry.get(problem.type)
    if pt.generate is None:
        return None
    seed = int(hashlib.sha256(problem.slug.encode()).hexdigest()[:8], 16)
    difficulty = 2
    if problem.type in ("rref", "matrix_inverse", "determinant", "cramers_rule") and "matrix" in problem.given:
        difficulty = 1 if problem.matrix.rows <= 2 else 2  # same size as the worked example
    for attempt in range(10):
        given, statement = pt.generate(random.Random(seed + attempt), difficulty)
        p = problem_from_dict(dict(slug=f"{problem.slug}-practice", course=pt.course, type=problem.type, given=given,
                                   statement=statement, confirmed_by_student=True))
        res = solve_problem(p)
        if res.verified:
            return {"given": given, "statement": statement, "latex": practice_tex(p),
                    "answer_text": _answer_text(res.solution), "type": problem.type}
    return None


def practice_tex(p: Problem) -> str:
    if p.type == "rref" and p.given.get("augmented"):
        m = p.matrix
        n = m.cols - 1
        names = sp.symbols("x y z")[:n] if n <= 3 else sp.symbols(f"x1:{n + 1}")
        eqs = [sp.latex(sp.Eq(sum(m[i, j] * names[j] for j in range(n)), m[i, n])) for i in range(m.rows)]
        return r"\begin{aligned}" + r"\\".join(e.replace("=", "&=", 1) for e in eqs) + r"\end{aligned}"
    if p.type in ("rref", "matrix_inverse", "determinant"):
        return "A = " + sp.latex(p.matrix)
    if p.type in ("derivative", "log_differentiation"):
        return r"\frac{d}{dx}\left(" + sp.latex(p.function) + r"\right)"
    if p.type == "indefinite_integral":
        return r"\int " + sp.latex(p.expr("integrand")) + r"\,dx"
    if p.type == "definite_integral":
        return (r"\int_{" + sp.latex(sp.sympify(p.given["a"])) + "}^{" + sp.latex(sp.sympify(p.given["b"])) + "} "
                + sp.latex(p.expr("integrand")) + r"\,dx")
    if p.type == "limit":
        return sp.latex(sp.Limit(p.expr("function"), sp.Symbol("x", real=True),
                                 sp.sympify(p.given["point"], locals={"oo": sp.oo}),
                                 p.given.get("direction", "+-")))
    if p.type == "complex" and p.given["task"] == "simplify":
        from tutor.parse.schema import parse_math
        return sp.latex(parse_math(p.given["expression"], imaginary=True, evaluate=False))
    return None  # the template shows the plain-text statement instead


def _answer_text(sol) -> str:
    from tutor.text.unicode_math import to_text

    return to_text(sol.answer)


def render(problem_path: Path, final: bool = False, voice: str | None = None) -> Path:
    problem = load_problem(problem_path)
    result = run(problem)  # solve + verify + write report (refuses unconfirmed problems)
    if not result.verified:
        raise SystemExit(f"Not rendering: verification status is {result.status}. See "
                         f"{result.out_dir / 'verification_report.md'}")
    pt = registry.get(problem.type)
    template = pt.template if pt.template and (TEMPLATES / f"{pt.template}.py").exists() else "derivation"
    out = result.out_dir
    if final:
        qa = out / "qa_layout.json"
        if not qa.exists() or json.loads(qa.read_text()):
            raise SystemExit("Final render needs a clean preview first: run without --final and fix the QA issues.")
    practice = practice_problem(problem)
    if practice:
        (out / "practice.json").write_text(json.dumps(practice, indent=2, ensure_ascii=False), encoding="utf-8")
    job = {"problem": str((out / "problem.json").resolve()), "digest": result.solution.digest(),
           "out_dir": str(out.resolve()), "practice": practice}
    job_path = out / "render_job.json"
    job_path.write_text(json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8")

    media = out / "media"
    quality = "-qh" if final else "-ql"
    env = dict(os.environ, GOATVEX_JOB=str(job_path.resolve()), PYTHONPATH=str(PROJECT_ROOT))
    if voice:
        env["GOATVEX_VOICE"] = voice
    cmd = [sys.executable, "-m", "manim", "render", quality, "--media_dir", str(media), "-o", "solution",
           str(TEMPLATES / f"{template}.py"), "Video"]
    print("Rendering:", " ".join(cmd))
    proc = subprocess.run(cmd, env=env, cwd=PROJECT_ROOT)
    if proc.returncode != 0:
        raise SystemExit("Manim render failed (see output above).")
    qdir = "1080p60" if final else "480p15"
    mp4 = next(p_ for p_ in media.rglob("solution.mp4") if p_.parent.name == qdir)
    name = "solution.mp4" if final else "preview.mp4"
    shutil.copy(mp4, out / name)
    srt = next((p_ for p_ in media.rglob("solution.srt") if p_.parent.name == qdir), None)
    if srt:
        shutil.copy(srt, out / "solution.srt")
    frames = extract_frames(out / name, out / "timeline.json", out / "frames")
    issues = json.loads((out / "qa_layout.json").read_text())
    print(f"\nVideo: {out / name}")
    print(f"Key frames for visual QA: {len(frames)} in {out / 'frames'}")
    if issues:
        print(f"Layout QA found {len(issues)} issue(s) — fix before the final render:")
        for it in issues[:20]:
            print(f"  t={it['t']:.1f}s [{it['segment']}] {it['issue']}: {it['what']}")
    else:
        print("Layout QA: no overlaps, nothing off-screen, nothing in the caption band.")
    return out / name


def extract_frames(video: Path, timeline: Path, folder: Path) -> list[Path]:
    """One frame near the end of every narrated segment (where the full step is on screen)."""
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.png"):
        old.unlink()
    segs = json.loads(timeline.read_text(encoding="utf-8"))
    out = []
    for k, seg in enumerate(segs):
        # the last frame of the segment: every animation in it has finished, nothing has faded yet
        t = max(seg["start"], seg["end"] - 0.04)
        path = folder / f"{k:02d}-{seg['segment']}.png"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                        str(path)], check=False)
        if path.exists():
            out.append(path)
    return out


def main(argv=None) -> int:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="python -m tutor.video.render")
    ap.add_argument("problem", type=Path)
    ap.add_argument("--final", action="store_true", help="1080p60 (after a clean preview)")
    ap.add_argument("--voice", choices=["edge", "silent"], default=None,
                    help="silent = offline preview audio (timing only)")
    args = ap.parse_args(argv)
    render(args.problem, final=args.final, voice="silent" if args.voice == "silent" else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
