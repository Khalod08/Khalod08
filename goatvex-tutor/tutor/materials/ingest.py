"""Ingest the student's course materials (PDFs) into a topic → file + page index.

    python -m tutor materials ingest [--course MATH1104]

For every PDF in materials/<course>/ (lecture notes, slides, the textbook,
past tests, assignments):

* the text of every page is extracted with PyMuPDF into
  materials/<course>/extracted/<file>.json. That text is the instructor's
  intellectual property, so it stays local (git-ignored).
* each page is matched against every problem type (title + keywords) and every
  course-plan topic, and section headings ("2.4 Matrix Inverses") are noted.
* materials/<course>/index.json gets only locations and our own labels
  (file, page, "Lecture 7, slide 12", a short heading), never copied text, so it
  can be committed and used to cite: "this is in Lecture 7, slide 12".
* the professor's notation is detected (tutor/materials/notation.py) and
  written to materials/<course>/notation.md + notation.json.

PowerPoint files can't be read directly: export them to PDF first.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from tutor import registry
from tutor.pipeline import PROJECT_ROOT

MATERIALS = PROJECT_ROOT / "materials"
KINDS = [("outline", r"outline|syllabus"), ("test", r"test|midterm|exam|quiz|final"),
         ("assignment", r"assignment|webwork|homework|\bhw\b|problem.?set"),
         ("textbook", r"textbook|nicholson|poole|mingarelli|abc|calculus|linear.?algebra.?with"),
         ("lecture", r"lecture|\blec\b|\bl\d+\b|week|slides?|notes|class")]
HEADING = re.compile(r"^\s*((?:\d{1,2}|[A-Z])\.\d{1,2}(?:\.\d{1,2})?)\s+([A-Z][^\n]{2,70})$", re.M)
MAX_PER_TOPIC = 8


def _kind(name: str) -> str:
    low = name.lower()
    for kind, pat in KINDS:
        if re.search(pat, low):
            return kind
    return "notes"


def _label(path: Path, kind: str) -> str:
    stem = path.stem.replace("_", " ").replace("-", " ")
    m = re.search(r"(?:lecture|lec|\bl)\s*0*(\d{1,2})\b", stem, re.I)
    if m:
        return f"Lecture {int(m.group(1))}"
    m = re.search(r"(?:test|midterm|quiz)\s*0*(\d)", stem, re.I)
    if m:
        return f"{'Test' if 'test' in stem.lower() else 'Quiz'} {m.group(1)} ({path.stem})"
    m = re.search(r"week\s*0*(\d{1,2})", stem, re.I)
    if m:
        return f"Week {int(m.group(1))} notes"
    if kind == "textbook":
        for book in ("Nicholson", "Poole", "Mingarelli"):
            if book.lower() in stem.lower():
                return book
        return "Textbook"
    return " ".join(stem.split())


def _phrases_for_types(course: str) -> dict[str, list[str]]:
    out = {}
    for name in registry.names():
        pt = registry.get(name)
        if pt.course != course:
            continue
        out[name] = sorted({k.lower() for k in pt.keywords} | {pt.title.lower().split(" (")[0]}, key=len, reverse=True)
    return out


def _count(text: str, phrase: str) -> int:
    return len(re.findall(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", text))


def extract(pdf: Path) -> tuple[list[str], bool]:
    import pymupdf

    with pymupdf.open(pdf) as doc:
        pages = [p.get_text() for p in doc]
        slides = sum(1 for p in doc if p.rect.width > p.rect.height) > len(pages) / 2
    return pages, slides


def ingest(course: str, base: Path | None = None) -> dict:
    folder = (base or MATERIALS) / course
    pdfs = sorted(p for p in folder.rglob("*.pdf") if "extracted" not in p.parts)
    out_text = folder / "extracted"
    out_text.mkdir(parents=True, exist_ok=True)
    phrases = _phrases_for_types(course)
    plan_file = folder / "course_plan.json"
    plan_topics = []
    if plan_file.exists():
        plan = json.loads(plan_file.read_text(encoding="utf-8"))
        plan_topics = sorted({t for w in plan.get("weeks", []) for t in w.get("topics", [])
                              if t.lower() not in ("review", "fall break")})
    files, topics, sections, plan_hits = [], {}, {}, {}
    skipped = [p.name for p in folder.rglob("*.ppt*")]
    for pdf in pdfs:
        rel = pdf.relative_to(folder).as_posix()
        pages, slides = extract(pdf)
        kind = _kind(pdf.name)
        if slides and kind == "notes":
            kind = "lecture"
        label = _label(pdf, kind)
        unit = "slide" if slides else "p."
        (out_text / (pdf.stem + ".json")).write_text(json.dumps({"file": rel, "pages": pages}, ensure_ascii=False),
                                                     encoding="utf-8")
        files.append({"file": rel, "kind": kind, "label": label, "pages": len(pages), "slides": slides})
        for i, text in enumerate(pages, 1):
            low = text.lower()
            heads = [(m.group(1), " ".join(m.group(2).split())[:60]) for m in HEADING.finditer(text)]
            for num, title in heads:
                sections.setdefault(num, {"file": rel, "page": i, "title": title, "where": f"{label}, {unit} {i}"})
            title = heads[0][1] if heads else next((ln.strip()[:60] for ln in text.splitlines() if len(ln.strip()) > 3),
                                                   "")
            for t, phr in (phrases.items() if kind != "outline" else ()):  # an outline isn't a place to learn from
                score = sum(_count(low, ph) * (1 + len(ph.split())) for ph in phr)
                if score:
                    topics.setdefault(t, []).append({"file": rel, "page": i, "where": f"{label}, {unit} {i}",
                                                     "kind": kind, "heading": title, "score": score})
            for tp in plan_topics:
                if tp.lower() in low:
                    plan_hits.setdefault(tp, []).append({"file": rel, "page": i, "where": f"{label}, {unit} {i}"})
    rank = {"lecture": 0, "notes": 1, "textbook": 2, "assignment": 3, "test": 4, "outline": 9}
    for t in topics:
        topics[t] = sorted(topics[t], key=lambda e: (rank.get(e["kind"], 5), -e["score"]))[:MAX_PER_TOPIC]
    for tp in plan_hits:
        plan_hits[tp] = plan_hits[tp][:MAX_PER_TOPIC]
    index = {"course": course, "generated": datetime.now().isoformat(timespec="seconds"),
             "note": "Locations only (file, page, our labels). The materials themselves stay local.",
             "files": files, "types": topics, "plan_topics": plan_hits, "sections": dict(sorted(sections.items())),
             "not_read": skipped}
    (folder / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    from tutor.materials.notation import detect, write_notation

    notes = detect([json.loads(p.read_text(encoding="utf-8")) for p in sorted(out_text.glob("*.json"))],
                   {f["file"]: f for f in files})
    write_notation(course, notes, folder)
    from tutor.materials.index import load_index

    load_index.cache_clear()
    return index
