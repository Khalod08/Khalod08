"""Look things up in materials/<course>/index.json: citations for a problem, search by concept."""

from __future__ import annotations

import json
import re
from functools import lru_cache

from tutor.pipeline import PROJECT_ROOT

MATERIALS = PROJECT_ROOT / "materials"


@lru_cache(maxsize=None)
def load_index(course: str) -> dict | None:
    path = MATERIALS / course / "index.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def locations(course: str, ptype: str, limit: int = 3) -> list[dict]:
    idx = load_index(course)
    if not idx:
        return []
    return idx.get("types", {}).get(ptype, [])[:limit]


def _fmt(e: dict) -> str:
    head = f" (“{e['heading']}”)" if e.get("heading") else ""
    return f"{e['where']}{head}"


def citations_for(problem, limit: int = 2) -> list[str]:
    """'In your materials: Lecture 7, slide 12 (“Row reduction”)' for a problem's type."""
    out = []
    src = problem.source or {}
    if src.get("book") or src.get("file"):
        where = ", ".join(str(src[k]) for k in ("book", "file", "section", "page", "exercise") if src.get(k))
        out.append(f"Source: {where}")
    locs = locations(problem.course, problem.type, limit)
    if locs:
        out.append("In your materials: " + "; ".join(_fmt(e) for e in locs))
    return out


def section_location(course: str, section: str) -> dict | None:
    idx = load_index(course)
    return (idx or {}).get("sections", {}).get(section)


def search_text(course: str, query: str, limit: int = 8) -> list[dict]:
    """Full-text search of the LOCAL extracted pages (never committed). Ranks pages by query word hits."""
    folder = MATERIALS / course / "extracted"
    idx = load_index(course) or {}
    meta = {f["file"]: f for f in idx.get("files", [])}
    words = [w for w in re.findall(r"[a-z0-9']+", query.lower()) if len(w) > 2]
    phrase = query.lower().strip()
    hits = []
    for path in sorted(folder.glob("*.json")) if folder.exists() else []:
        doc = json.loads(path.read_text(encoding="utf-8"))
        m = meta.get(doc["file"], {})
        unit = "slide" if m.get("slides") else "p."
        for i, text in enumerate(doc["pages"], 1):
            low = text.lower()
            score = 5 * low.count(phrase) + sum(low.count(w) for w in words)
            if score and all(w in low for w in words[:3]):
                hits.append({"file": doc["file"], "page": i, "where": f"{m.get('label', doc['file'])}, {unit} {i}",
                             "score": score})
    return sorted(hits, key=lambda h: -h["score"])[:limit]
