"""The course plans (materials/<course>/course_plan.json): weeks, tests, which problem types each week teaches."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

from tutor.pipeline import PROJECT_ROOT

COURSES = ("MATH1104", "MATH1004")


@lru_cache(maxsize=None)
def load(course: str) -> dict:
    return json.loads((PROJECT_ROOT / "materials" / course / "course_plan.json").read_text(encoding="utf-8"))


def norm_course(text: str) -> str:
    t = text.upper().replace(" ", "")
    for c in COURSES:
        if t in (c, c[-4:]):
            return c
    raise ValueError(f"unknown course {text!r}; use MATH1104 or MATH1004")


@dataclass
class Test:
    course: str
    name: str
    date: date
    number: int | None  # 1–4, or None for the final


def tests(course: str) -> list[Test]:
    d = load(course)
    out = [Test(course, t["name"], date.fromisoformat(t["date"]), i + 1) for i, t in enumerate(d["tests"])]
    if "final" in d:
        out.append(Test(course, d["final"]["name"], date.fromisoformat(d["final"]["date"]), None))
    return out


def find_test(course: str, which: str) -> Test:
    w = which.lower().replace(" ", "").replace("test", "")
    for t in tests(course):
        if (t.number is None and w in ("final", "finalexam", "exam")) or (t.number is not None and w == str(t.number)):
            return t
    raise ValueError(f"no test {which!r} for {course}; use test1–test4 or final")


def next_test(course: str, today: date | None = None) -> Test | None:
    today = today or date.today()
    upcoming = [t for t in tests(course) if t.date >= today]
    return upcoming[0] if upcoming else None


def weeks(course: str) -> list[dict]:
    return [w for w in load(course)["weeks"] if str(w["week"]) != "break"]


def weeks_before(course: str, when: date) -> list[dict]:
    """Weeks whose first lecture is before ``when`` (what a test on that date can cover)."""
    return [w for w in weeks(course) if date.fromisoformat(w["start"]) < when]


def covered_specs(course: str, when: date, recent_since: date | None = None) -> dict[str, float]:
    """{type spec: weight} for everything taught before ``when``; weeks after ``recent_since`` count double
    (tests are cumulative but focus on the recent material)."""
    out: dict[str, float] = {}
    for w in weeks_before(course, when):
        recent = recent_since is not None and date.fromisoformat(w["start"]) >= recent_since
        for spec in w.get("goatvex_types", []):
            out[spec] = max(out.get(spec, 0.0), 2.0 if recent else 1.0)
    return out


def topics_for(course: str, when: date) -> list[str]:
    return [t for w in weeks_before(course, when) for t in w.get("topics", [])]


def sections_for(course: str, when: date) -> list[str]:
    book = "nicholson" if course == "MATH1104" else "mingarelli"
    return [s for w in weeks_before(course, when) for s in (w.get(book) or [])]
