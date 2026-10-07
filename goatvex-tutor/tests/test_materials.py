"""Phase 5: ingest PDFs into a topic index, detect the professor's notation, cite locations."""

from __future__ import annotations

import json

import pytest

SLIDES = [
    "Lecture 3: Row reduction\nWe use elementary row operations.\nR2 ← R2 − 3R1\nR3 ← R3 + 2R1\n"
    "The reduced row echelon form (RREF) is unique.",
    "Free variables\nLet x3 = t1 and x4 = t2.\nThen x1 = 2 − t1, x2 = t2.\nRow reduce: R1 ← (1/2)R1",
    "Transpose\nThe transpose A^T of A satisfies (AB)^T = B^T A^T. det(A^T) = det A",
]
BOOK = ["2.4 Matrix Inverses\nAn inverse matrix A^{-1} satisfies AA^{-1} = I.\nmatrix inverse examples",
        "3.1 The Cofactor Expansion\nThe determinant by cofactor expansion along a row.",
        "3.3 Diagonalization and Eigenvalues\nAn eigenvalue λ of A with eigenvector x."]


def _pdf(path, pages, landscape):
    import pymupdf

    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page(width=792 if landscape else 612, height=612 if landscape else 792)
        # insert_htmlbox ships its own Unicode fonts (←, −, λ), so this works on any OS
        html = "".join(f"<p>{line}</p>" for line in text.split("\n"))
        page.insert_htmlbox(pymupdf.Rect(40, 40, page.rect.width - 40, page.rect.height - 40), html)
    doc.save(path)


@pytest.fixture
def materials(tmp_path):
    course = tmp_path / "MATH1104"
    course.mkdir()
    _pdf(course / "Lecture03_row_reduction.pdf", SLIDES, landscape=True)
    _pdf(course / "Nicholson_textbook_excerpt.pdf", BOOK, landscape=False)
    (course / "course_plan.json").write_text(json.dumps({"weeks": [{"week": 3, "topics": ["Matrix inverses"]}]}))
    return tmp_path


def test_ingest_builds_index_without_copying_text(materials, monkeypatch):
    from tutor.materials import ingest, notation

    monkeypatch.setattr(notation, "PROJECT_ROOT", materials.parent)  # don't touch the real notation cache
    idx = ingest.ingest("MATH1104", base=materials)
    files = {f["label"]: f for f in idx["files"]}
    assert files["Lecture 3"]["slides"] and files["Lecture 3"]["kind"] == "lecture"
    assert files["Nicholson"]["kind"] == "textbook"
    rref = idx["types"]["rref"]
    assert rref[0]["where"].startswith("Lecture 3, slide")
    assert idx["types"]["matrix_inverse"][0]["where"] == "Nicholson, p. 1"
    assert idx["sections"]["3.1"]["title"].startswith("The Cofactor Expansion")
    # the committed index holds locations and short headings, not page text
    raw = (materials / "MATH1104" / "index.json").read_text(encoding="utf-8")
    assert "satisfies" not in raw
    # extracted text is local only
    assert (materials / "MATH1104" / "extracted" / "Lecture03_row_reduction.json").exists()


def test_notation_detection(materials, monkeypatch):
    from tutor.materials import ingest, notation

    monkeypatch.setattr(notation, "PROJECT_ROOT", materials.parent)
    ingest.ingest("MATH1104", base=materials)
    st = json.loads((materials / "MATH1104" / "notation.json").read_text(encoding="utf-8"))
    assert st["rowop_style"] == "left_arrow"
    assert st["transpose"] == "Aᵀ"
    assert st["params"] == ["t₁", "t₂", "t₃"]
    md = (materials / "MATH1104" / "notation.md").read_text(encoding="utf-8")
    assert "R₂ ← R₂ − 3R₁" in md and "Lecture 3" in md


def test_row_ops_follow_the_professors_notation(monkeypatch):
    from tutor.materials import notation
    from tutor.solvers.linear_algebra.rref import param_names
    from tutor.solvers.linear_algebra.row_ops import REPLACE, RowOp

    op = RowOp(REPLACE, 1, 0, -3)
    assert op.text() == "R₂ → R₂ − 3R₁"  # default (conftest)
    monkeypatch.setattr(notation, "settings_for",
                        lambda c: {**notation.DEFAULTS, "rowop_style": "left_arrow", "params": ["t₁", "t₂", "t₃"]})
    assert op.text() == "R₂ ← R₂ − 3R₁"
    assert [str(s) for s in param_names(2)] == ["t₁", "t₂"]
    monkeypatch.setattr(notation, "settings_for", lambda c: {**notation.DEFAULTS, "rowop_style": "result_right"})
    assert op.text() == "R₂ − 3R₁ → R₂"


def test_citations(materials, monkeypatch):
    from tutor.materials import index, ingest, notation
    from tutor.parse.schema import problem_from_dict

    monkeypatch.setattr(notation, "PROJECT_ROOT", materials.parent)
    ingest.ingest("MATH1104", base=materials)
    monkeypatch.setattr(index, "MATERIALS", materials)
    index.load_index.cache_clear()
    p = problem_from_dict(dict(slug="c", course="MATH1104", type="rref", given={"matrix": [["1", "2"], ["3", "4"]]},
                               confirmed_by_student=True, source={"book": "Nicholson", "section": "1.2"}))
    cites = index.citations_for(p)
    assert cites[0] == "Source: Nicholson, 1.2"
    assert cites[1].startswith("In your materials: Lecture 3, slide")
    hits = index.search_text("MATH1104", "cofactor expansion")
    assert hits and hits[0]["where"] == "Nicholson, p. 2"
    index.load_index.cache_clear()
