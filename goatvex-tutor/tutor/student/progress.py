"""The student's progress: topics seen, mistakes by type, quiz history, spaced repetition.

Stored in ``student/progress.json`` (plain JSON, easy to read and back up).

Spaced repetition: a simple Leitner system. Each topic sits in a box 0–5.
A correct answer moves it up one box, a mistake drops it to box 0 (or 1 if
it was high). The next review is due after INTERVALS[box] days, so weak topics
come back tomorrow and solid ones only every few weeks.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from tutor.pipeline import PROJECT_ROOT

STUDENT_DIR = PROJECT_ROOT / "student"
PROGRESS_FILE = STUDENT_DIR / "progress.json"
INTERVALS = [1, 2, 4, 8, 16, 32]  # days until the next review, by Leitner box

# Mistake types GoatVex logs (free-form types are allowed too)
MISTAKE_TYPES = {
    "sign error in row reduction", "arithmetic error in a row operation", "wrong row-operation multiplier",
    "not a single elementary row operation", "forgot chain rule inner derivative", "product rule applied wrong",
    "quotient rule order/sign", "power rule error", "sign error", "arithmetic error", "algebra error",
    "forgot to divide by the inner derivative", "forgot + C", "wrong antiderivative", "wrong limits of integration",
    "indeterminate form treated as a value", "L'Hôpital used when not 0/0 or ∞/∞", "cofactor sign error",
    "dot/cross product error", "i² ≠ −1", "conjugate error", "wrong quadrant for the argument",
    "transcription/copying error", "other",
}


def today() -> date:
    return date.today()


def empty() -> dict:
    return {"version": 1, "updated": None, "topics": {}, "mistakes": [], "quizzes": [], "sessions": []}


def load(path: Path | None = None) -> dict:
    path = path or PROGRESS_FILE
    if not path.exists():
        return empty()
    data = json.loads(path.read_text(encoding="utf-8"))
    for k, v in empty().items():
        data.setdefault(k, v)
    return data


def save(data: dict, path: Path | None = None) -> None:
    path = path or PROGRESS_FILE
    data["updated"] = datetime.now().isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _topic(data: dict, topic: str, course: str = "") -> dict:
    t = data["topics"].setdefault(topic, {"course": course, "seen": 0, "correct": 0, "wrong": 0, "box": 0,
                                          "last_seen": None, "next_review": None})
    if course and not t.get("course"):
        t["course"] = course
    return t


def record(data: dict, topic: str, correct: bool | None, course: str = "", mistake: str | None = None,
           problem: str = "", detail: str = "", when: date | None = None) -> dict:
    """Record one interaction with a topic. correct=None means 'studied a worked example'."""
    when = when or today()
    t = _topic(data, topic, course)
    t["seen"] += 1
    t["last_seen"] = when.isoformat()
    if correct is True:
        t["correct"] += 1
        t["box"] = min(t["box"] + 1, len(INTERVALS) - 1)
    elif correct is False:
        t["wrong"] += 1
        t["box"] = 0 if t["box"] <= 2 else 1
    t["next_review"] = (when + timedelta(days=INTERVALS[t["box"]])).isoformat()
    if mistake:
        data["mistakes"].append({"date": when.isoformat(), "topic": topic, "course": course, "type": mistake,
                                 "problem": problem, "detail": detail})
    return t


def record_quiz(data: dict, course: str, name: str, items: list[dict]) -> dict:
    score = sum(1 for it in items if it.get("correct"))
    q = {"date": today().isoformat(), "course": course, "name": name, "score": score, "total": len(items),
         "items": items}
    data["quizzes"].append(q)
    return q


def mistake_counts(data: dict) -> Counter:
    return Counter(m["type"] for m in data["mistakes"])


def due(data: dict, on: date | None = None) -> list[tuple[str, dict]]:
    on = on or today()
    out = [(k, t) for k, t in data["topics"].items() if t.get("next_review") and date.fromisoformat(t["next_review"]) <= on]
    return sorted(out, key=lambda kt: (kt[1]["box"], kt[1]["next_review"]))


@dataclass
class Weakness:
    topic: str
    score: float      # higher = weaker
    wrong: int
    seen: int
    box: int


def weak_topics(data: dict, course: str | None = None, limit: int = 5) -> list[Weakness]:
    """Weakness = error rate (smoothed) + recent mistakes + low Leitner box."""
    recent = Counter(m["topic"] for m in data["mistakes"][-30:])
    out = []
    for k, t in data["topics"].items():
        if course and t.get("course") and t["course"] != course:
            continue
        attempts = t["correct"] + t["wrong"]
        rate = (t["wrong"] + 1) / (attempts + 2)
        score = rate + 0.15 * recent.get(k, 0) + 0.1 * (len(INTERVALS) - 1 - t["box"]) / (len(INTERVALS) - 1)
        out.append(Weakness(k, round(score, 3), t["wrong"], t["seen"], t["box"]))
    return sorted(out, key=lambda w: -w.score)[:limit]


def topic_weights(data: dict, topics: list[str]) -> dict[str, float]:
    """Sampling weights for practice: weak or due topics come up more often; unseen ones still appear."""
    due_set = {k for k, _ in due(data)}
    w = {}
    for tp in topics:
        t = data["topics"].get(tp)
        if t is None:
            w[tp] = 1.0
            continue
        attempts = t["correct"] + t["wrong"]
        rate = (t["wrong"] + 1) / (attempts + 2)
        w[tp] = 0.5 + 2.0 * rate + (1.0 if tp in due_set else 0.0)
    return w
