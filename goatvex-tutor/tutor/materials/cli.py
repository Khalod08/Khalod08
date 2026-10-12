"""python -m tutor materials ingest | find | show"""

from __future__ import annotations

from tutor.study import plan


def run(args) -> int:
    from tutor.materials import index as I
    from tutor.materials.ingest import ingest

    courses = [plan.norm_course(args.course)] if getattr(args, "course", None) else list(plan.COURSES)
    if args.action == "ingest":
        for c in courses:
            idx = ingest(c)
            n_pages = sum(f["pages"] for f in idx["files"])
            print(f"{c}: {len(idx['files'])} PDF(s), {n_pages} pages; {len(idx['types'])} problem types located; "
                  f"{len(idx['sections'])} section headings.")
            for f in idx["files"]:
                print(f"   {f['label']:28} {f['kind']:10} {f['pages']:4} {'slides' if f['slides'] else 'pages'}  ({f['file']})")
            if idx["not_read"]:
                print(f"   Not read (export to PDF first): {', '.join(idx['not_read'])}")
            print(f"   Index: materials/{c}/index.json   Notation: materials/{c}/notation.md")
        return 0
    if args.action == "find":
        from tutor.study.explain import match

        q = " ".join(args.query)
        for c in courses:
            types = [t for t, _ in match(q, c, 2)]
            shown = False
            for t in types:
                for e in I.locations(c, t, 4):
                    if not shown:
                        print(f"{c}:")
                        shown = True
                    print(f"   {e['where']}  — {e.get('heading', '')}  [{t}]")
            for h in I.search_text(c, q, 5):
                if not shown:
                    print(f"{c}:")
                    shown = True
                print(f"   {h['where']}  (text match)")
            if not shown and I.load_index(c) is None:
                print(f"{c}: no materials indexed yet (put PDFs in materials/{c}/ and run `materials ingest`).")
        return 0
    if args.action == "show":
        for c in courses:
            idx = I.load_index(c)
            if not idx:
                print(f"{c}: not indexed yet.")
                continue
            print(f"{c} (indexed {idx['generated']}):")
            for f in idx["files"]:
                print(f"   {f['label']:28} {f['kind']:10} {f['pages']} pages")
        return 0
    return 1
