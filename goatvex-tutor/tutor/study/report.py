"""/progress: what the student has done, what's due, weak spots, mistake patterns, upcoming tests."""

from __future__ import annotations

from datetime import date

from tutor.student import progress
from tutor.study import plan
from tutor.writeup import html as W


def _title(topic: str) -> str:
    return topic.replace("-", " ")


def summary(data: dict | None = None, today: date | None = None) -> str:
    data = data or progress.load()
    today = today or date.today()
    out = []
    tests = sorted((t for c in plan.COURSES for t in plan.tests(c) if t.date >= today), key=lambda t: t.date)
    if tests:
        out.append("Upcoming:")
        for t in tests[:4]:
            out.append(f"  {t.course} {t.name}: {t.date:%a %b %d} (in {(t.date - today).days} days)")
    topics = data["topics"]
    if not topics:
        out.append("\nNo practice recorded yet. Try /practice to start building your record.")
        return "\n".join(out)
    att = sum(t["correct"] + t["wrong"] for t in topics.values())
    cor = sum(t["correct"] for t in topics.values())
    out.append(f"\nPractice so far: {cor} of {att} answers correct across {len(topics)} topics.")
    due = progress.due(data, today)
    if due:
        out.append("Due for review today: " + ", ".join(_title(k) for k, _ in due))
    weak = [w for w in progress.weak_topics(data, limit=3) if w.wrong]
    if weak:
        out.append("Weak spots: " + ", ".join(f"{_title(w.topic)} ({w.wrong} wrong)" for w in weak))
    mc = progress.mistake_counts(data).most_common(3)
    if mc:
        out.append("Most common mistakes: " + ", ".join(f"{m} ×{n}" for m, n in mc))
    if data["quizzes"]:
        q = data["quizzes"][-1]
        out.append(f"Last quiz: {q['name']} on {q['date']}: {q['score']}/{q['total']}")
    return "\n".join(out)


def page(data: dict | None = None, today: date | None = None) -> str:
    data = data or progress.load()
    today = today or date.today()
    body = []
    tests = sorted((t for c in plan.COURSES for t in plan.tests(c) if t.date >= today), key=lambda t: t.date)
    if tests:
        body.append("<h2>Upcoming tests</h2><table><tr><th>Course</th><th>Test</th><th>Date</th><th>Days</th>"
                    "<th>Covers</th></tr>" + "".join(
                        f"<tr><td>{t.course}</td><td>{W.esc(t.name)}</td><td>{t.date:%a %b %d}</td>"
                        f"<td>{(t.date - today).days}</td><td>{W.esc('; '.join(plan.topics_for(t.course, t.date)[-6:]))}"
                        "</td></tr>" for t in tests[:6]) + "</table>")
    due = {k for k, _ in progress.due(data, today)}
    rows = []
    for k, t in sorted(data["topics"].items(), key=lambda kv: -((kv[1]["wrong"] + 1) / (kv[1]["correct"] + kv[1]["wrong"] + 2))):
        att = t["correct"] + t["wrong"]
        pct = round(100 * t["correct"] / att) if att else 0
        rows.append(f"<tr><td>{W.esc(_title(k))}</td><td>{W.esc(t.get('course', ''))}</td><td>{t['correct']}/{att}</td>"
                    f"<td><div class='bar'><span style='width:{pct}%'></span></div></td><td>{t['box']}</td>"
                    f"<td>{W.esc(t.get('next_review') or '')}{' (due)' if k in due else ''}</td></tr>")
    body.append("<h2>Topics</h2>" + ("<table><tr><th>Topic</th><th>Course</th><th>Correct</th><th></th>"
                                    "<th>Box</th><th>Next review</th></tr>" + "".join(rows) + "</table>"
                                    if rows else "<p>No practice recorded yet.</p>"))
    mc = progress.mistake_counts(data).most_common()
    if mc:
        body.append("<h2>Mistake patterns</h2><table><tr><th>Mistake</th><th>Times</th></tr>" +
                    "".join(f"<tr><td>{W.esc(m)}</td><td>{n}</td></tr>" for m, n in mc) + "</table>")
    if data["quizzes"]:
        body.append("<h2>Quizzes and mock tests</h2><table><tr><th>Date</th><th>Name</th><th>Score</th></tr>" +
                    "".join(f"<tr><td>{q['date']}</td><td>{W.esc(q['name'])}</td><td>{q['score']}/{q['total']}</td></tr>"
                            for q in reversed(data["quizzes"])) + "</table>")
    body.append('<p class="muted">Box = spaced-repetition level (0 = review tomorrow, 5 = every month). '
                'A right answer moves a topic up a box; a mistake moves it back down.</p>')
    return W.page("Your progress", "\n".join(body), crumbs="GoatVex")
