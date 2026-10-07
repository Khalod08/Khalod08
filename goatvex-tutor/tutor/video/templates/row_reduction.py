"""Row reduction / linear systems video (MATH 1104).

Structure: (1) the problem → (2) picture it (lines in the plane / planes in
space) → (3) every row operation, the changed row highlighted → (4) check by
substitution → (5) recap → (6) a practice problem, answer hidden.

All math on screen is ``sympy.latex()`` of verified objects.
"""

from __future__ import annotations

import sympy as sp
from manim import (DEGREES, DOWN, LEFT, RIGHT, UP, Create, Dot, FadeIn, FadeOut, Indicate, Line as MLine,
                   MathTex, Matrix, NumberPlane, ReplacementTransform, Surface, SurroundingRectangle, ThreeDAxes,
                   VGroup, Write, Text)

from tutor.narration.scripts import row_reduction as script_mod
from tutor.video import style as S
from tutor.video.base import GoatVex3DScene


def latex_matrix_entries(m: sp.Matrix) -> list[list[str]]:
    return [[sp.latex(m[i, j]) for j in range(m.cols)] for i in range(m.rows)]


class MatrixView:
    """A Manim Matrix of verified entries, with an optional augmentation bar."""

    def __init__(self, m: sp.Matrix, bar_at: int | None):
        self.m = m
        self.bar_at = bar_at
        has_frac = any(e.is_Rational and not e.is_Integer for e in m)
        self.mob = Matrix(latex_matrix_entries(m), element_to_mobject=lambda s: MathTex(s, color=S.TEXT),
                          h_buff=1.45 if has_frac else 1.35, v_buff=1.5 if has_frac else 0.85, bracket_h_buff=0.2)
        self.mob.scale(S.MATRIX_SIZE / 34)
        self.bar = None
        if bar_at is not None:
            self.bar = self._make_bar()
        self.group = VGroup(self.mob, *([self.bar] if self.bar else []))
        self.group.qa_name = "matrix"
        self.group.qa_parts = list(self.mob.get_entries())  # entries must never overlap each other

    def _make_bar(self):
        cols = self.mob.get_columns()
        x = (cols[self.bar_at - 1].get_right()[0] + cols[self.bar_at].get_left()[0]) / 2
        top, bottom = self.mob.get_top()[1] - 0.1, self.mob.get_bottom()[1] + 0.1
        return MLine([x, top, 0], [x, bottom, 0], color=S.MUTED, stroke_width=2)

    def place_like(self, other: "MatrixView"):
        self.group.move_to(other.group.get_center())
        if self.bar is not None:
            new_bar = self._make_bar()
            self.bar.become(new_bar)
        return self

    def entries(self, i):
        return self.mob.get_rows()[i]

    def color_pivots(self, pivots):
        for r, c in pivots:
            if r < self.m.rows and c < self.m.cols and self.m[r, c] == 1:
                self.mob.get_rows()[r][c].set_color(S.PIVOT)


class Video(GoatVex3DScene):
    template_name = "row_reduction"

    def construct(self):
        sol = self.solution
        f = sol.facts
        script = script_mod.build(sol)
        self.script = script
        aug = f["augmented"]
        m0 = f["input"]
        bar_at = m0.cols - 1 if aug else None
        self.bar_at = bar_at

        # (1) the problem ---------------------------------------------------
        title = self.title("Solving a linear system" if aug else "Row reduction")
        view = MatrixView(m0, bar_at)
        self.fit(view.group, top=S.CONTENT_TOP - 0.2)
        self.register(view.group)
        with self.narrate(script["intro"], "problem"):
            self.play(Write(title), run_time=1.0)
            self.play(FadeIn(view.group, shift=0.3 * UP), run_time=1.2)
        self.title_mob = title

        # (2) intuition -------------------------------------------------------
        self.play(FadeOut(view.group), run_time=0.5)
        self.unregister(view.group)
        self.intuition(script["intuition"], m0, f)
        self.play(FadeIn(view.group), run_time=0.6)
        self.register(view.group)

        # (3) every row operation ---------------------------------------------
        self.play(view.group.animate.scale(0.92).move_to([0, -0.15, 0]), run_time=0.6)
        current = view
        for step, line in script["steps"]:
            current = self.row_op_step(current, step, line)

        # result
        current.color_pivots([(r - 1, c - 1) for r, c in f["pivots"]])
        with self.narrate(script["result"], "result"):
            self.play(*[Indicate(current.mob.get_rows()[r - 1][c - 1], color=S.PIVOT) for r, c in f["pivots"]],
                      run_time=1.2)
            answer_tex = self.answer_tex(f)
            if answer_tex is not None:
                answer_tex.next_to(current.group, DOWN, buff=0.35)
                if answer_tex.get_bottom()[1] < S.CAPTION_TOP + 0.15:
                    VGroup(current.group, answer_tex).arrange(DOWN, buff=0.35)
                    self.fit(VGroup(current.group, answer_tex))
                self.register(answer_tex)
                self.play(Write(answer_tex), run_time=1.5)

        # (4) check -------------------------------------------------------------
        self.play(*[FadeOut(mo) for mo in self.blocks], run_time=0.6)
        self.blocks.clear()
        self.check_segment(script["check"], f)

        # (5) recap + (6) practice ---------------------------------------------
        self.recap(script["recap"])
        self.practice(script["practice"])

    # ------------------------------------------------------------------ segments
    def intuition(self, line, m0, f):
        aug = f["augmented"]
        nvars = m0.cols - 1 if aug else m0.cols
        if not aug or nvars not in (2, 3):
            with self.narrate(line, "intuition"):
                self.wait(0.5)
            return
        if nvars == 2:
            self.lines_picture(line, m0, f)
        else:
            self.planes_picture(line, m0, f)

    def lines_picture(self, line, m0, f):
        system = f["system"]
        pts = [system["particular"]] if system["status"] == "unique" else []
        cx = float(pts[0][0]) if pts else 0.0
        cy = float(pts[0][1]) if pts else 0.0
        span = 5
        plane = NumberPlane(x_range=[cx - span, cx + span, 1], y_range=[cy - span * 0.6, cy + span * 0.6, 1],
                            x_length=8.5, y_length=5.2,
                            background_line_style={"stroke_color": S.MUTED, "stroke_opacity": 0.35})
        plane.move_to([0, 0.05, 0])
        plane.qa_name = "plane"
        x = sp.Symbol("x")
        y = sp.Symbol("y")
        eqs = []
        for i in range(m0.rows):
            a, b, c = m0[i, 0], m0[i, 1], m0[i, 2]
            if a == 0 and b == 0:
                continue
            eqs.append((a, b, c, S.SERIES[i % len(S.SERIES)]))
        labels = [MathTex(sp.latex(sp.Eq(a * x + b * y, c)), color=col, font_size=38) for a, b, c, col in eqs]
        legend = VGroup(*labels).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        legend.next_to(plane, RIGHT, buff=0.25)
        self.fit(VGroup(plane, legend))  # position FIRST, then draw lines in the final coordinates
        x_lo, x_hi = cx - span, cx + span
        y_lo, y_hi = cy - span * 0.6, cy + span * 0.6
        graphs = []
        for a, b, c, col in eqs:
            if b != 0:
                # clip to the visible window: x where y stays inside [y_lo, y_hi]
                xs = sorted([float((c - b * y_lo) / a), float((c - b * y_hi) / a)]) if a != 0 else [x_lo, x_hi]
                t0, t1 = max(x_lo, xs[0]), min(x_hi, xs[1])
                p0 = plane.c2p(t0, float((c - a * t0) / b))
                p1 = plane.c2p(t1, float((c - a * t1) / b))
                graphs.append(MLine(p0, p1, color=col, stroke_width=4))
            else:
                x0 = float(c / a)
                graphs.append(MLine(plane.c2p(x0, y_lo), plane.c2p(x0, y_hi), color=col, stroke_width=4))
        legend.qa_name = "legend"
        plot = VGroup(plane, *graphs)
        plot.qa_name = "plot"
        self.register(plot, legend)
        with self.narrate(line, "intuition") as tracker:
            self.play(Create(plane), run_time=1.0)
            for g, lab in zip(graphs, labels):
                self.play(Create(g), FadeIn(lab), run_time=1.0)
            if pts:
                dot = Dot(plane.c2p(float(pts[0][0]), float(pts[0][1])), color=S.RESULT, radius=0.09)
                self.play(FadeIn(dot, scale=2), run_time=0.6)
                self.play(Indicate(dot, color=S.RESULT), run_time=0.8)
        self.play(*[FadeOut(mo) for mo in [plane, legend, *graphs] + ([dot] if pts else [])], run_time=0.6)
        self.unregister(plot, legend)

    def planes_picture(self, line, m0, f):
        system = f["system"]
        c = [float(v) for v in system["particular"]] if system["status"] == "unique" else [0.0, 0.0, 0.0]
        R = 4  # half-width of the window around the solution
        axes = ThreeDAxes(x_range=[c[0] - R, c[0] + R, 1], y_range=[c[1] - R, c[1] + R, 1],
                          z_range=[c[2] - R, c[2] + R, 1], x_length=4.2, y_length=4.2, z_length=3.2)
        axes.shift(0.35 * UP)
        surfaces = []
        for i in range(m0.rows):
            a, b, cc, d = (float(m0[i, j]) for j in range(4))
            color = S.SERIES[i % len(S.SERIES)]
            coeffs = [abs(a), abs(b), abs(cc)]
            if max(coeffs) == 0:
                continue
            k = coeffs.index(max(coeffs))

            def point(u, v, a=a, b=b, cc=cc, d=d, k=k):
                # solve the plane for its dominant variable; (u, v) are the other two coordinates
                if k == 2:
                    return axes.c2p(u, v, (d - a * u - b * v) / cc)
                if k == 1:
                    return axes.c2p(u, (d - a * u - cc * v) / b, v)
                return axes.c2p((d - b * u - cc * v) / a, u, v)

            ur = [c[0] - 2.5, c[0] + 2.5] if k != 0 else [c[1] - 2.5, c[1] + 2.5]
            vr = [c[1] - 2.5, c[1] + 2.5] if k == 2 else [c[2] - 2.5, c[2] + 2.5]
            surf = Surface(point, u_range=ur, v_range=vr, resolution=(8, 8), fill_opacity=0.45,
                           checkerboard_colors=[color, color], stroke_color=color, stroke_width=0.5)
            surfaces.append(surf)
        dot = None
        if system["status"] == "unique":
            dot = Dot(axes.c2p(*c), color=S.RESULT, radius=0.1)
        with self.narrate(line, "intuition"):
            self.move_camera(phi=62 * DEGREES, theta=-50 * DEGREES, zoom=0.95, frame_center=axes.c2p(*c),
                             run_time=1.0)
            self.play(Create(axes), run_time=1.0)
            for srf in surfaces:
                self.play(Create(srf), run_time=1.2)
            if dot is not None:
                self.play(FadeIn(dot, scale=2), run_time=0.6)
            self.begin_ambient_camera_rotation(rate=0.15)
            self.wait(1.5)
            self.stop_ambient_camera_rotation()
        self.play(*[FadeOut(mo) for mo in [axes, *surfaces] + ([dot] if dot else [])], run_time=0.6)
        self.move_camera(phi=0, theta=-90 * DEGREES, zoom=1.0, frame_center=[0, 0, 0], run_time=0.8)

    def row_op_step(self, view: MatrixView, step, line) -> MatrixView:
        op = step.data["rowop"]
        new = MatrixView(step.after, self.bar_at)
        new.place_like(view)
        self.fit(new.group, top=S.CONTENT_TOP - 0.9, center=False)  # leave room for the row-op label above
        if new.group.get_bottom()[1] < S.CAPTION_TOP + 0.15 or new.group.get_top()[1] > S.CONTENT_TOP - 0.9:
            new.group.move_to([0, (S.CONTENT_TOP - 0.9 + S.CAPTION_TOP + 0.15) / 2, 0])
        label = MathTex(op.latex(), color=S.CHANGE, font_size=S.OP_LABEL_SIZE)
        label.next_to(view.group, UP, buff=0.3)
        if label.get_top()[1] > S.CONTENT_TOP:
            label.move_to([0, S.CONTENT_TOP - label.height / 2, 0])
        label.qa_name = "row-op label"
        self.register(label)
        rows_old = view.mob.get_rows()
        rows_new = new.mob.get_rows()
        target = SurroundingRectangle(rows_old[op.i], color=S.CHANGE, buff=0.12)
        extras = [target]
        if op.j is not None and op.kind != "swap":
            extras.append(SurroundingRectangle(rows_old[op.j], color=S.PIVOT, buff=0.12))
        if op.kind == "swap":
            extras.append(SurroundingRectangle(rows_old[op.j], color=S.CHANGE, buff=0.12))
        with self.narrate(line, step.id):
            self.play(Write(label), *[Create(e) for e in extras], run_time=0.9)
            anims = []
            n = len(rows_old)
            mapping = list(range(n))
            if op.kind == "swap":
                mapping[op.i], mapping[op.j] = op.j, op.i
            for r in range(n):
                for c in range(len(rows_old[r])):
                    anims.append(ReplacementTransform(rows_old[r][c], rows_new[mapping[r]][c]))
            anims.append(ReplacementTransform(view.mob.get_brackets(), new.mob.get_brackets()))
            if view.bar is not None:
                anims.append(ReplacementTransform(view.bar, new.bar))
            self.play(*anims, *[FadeOut(e) for e in extras], run_time=S.TRANSFORM_TIME)
            changed = [op.i] if op.kind != "swap" else [op.i, op.j]
            self.play(*[Indicate(rows_new[r], color=S.CHANGE, scale_factor=1.05) for r in changed], run_time=0.8)
        # make the scene hold exactly the new matrix (no leftover pieces of the old one)
        pieces = [e for row in rows_new for e in row] + [new.mob.get_brackets()] + ([new.bar] if new.bar else [])
        self.remove(view.mob, *pieces)
        self.add(new.group)
        self.unregister(view.group)
        self.register(new.group)
        self.play(FadeOut(label), run_time=0.3)
        self.unregister(label)
        self.wait(S.STEP_PAUSE)
        return new

    def answer_tex(self, f):
        system = f.get("system")
        if not f["augmented"] or system is None:
            return None
        n = f["input"].cols - 1
        names = sp.symbols("x y z")[:n] if n <= 3 else sp.symbols(f"x1:{n + 1}")
        if system["status"] == "inconsistent":
            t = self.text("no solution", size=S.BODY_SIZE + 4, color=S.WARNING)
            t.qa_name = "answer"
            return t
        vals = system["particular"] if system["status"] == "unique" else system["general"]
        eqs = ",\\quad ".join(sp.latex(sp.Eq(v, val)) for v, val in zip(names, vals))
        tex = MathTex(eqs, color=S.RESULT, font_size=S.MATH_SIZE)
        tex.qa_name = "answer"
        return tex

    def check_segment(self, line, f):
        system = f.get("system")
        m0 = f["input"]
        rows = []
        if f["augmented"] and system and system["status"] in ("unique", "infinite"):
            xp = system["particular"]
            n = m0.cols - 1
            for i in range(m0.rows):
                # textbook form a(x₀) + b(y₀) = c; every number is sympy.latex of a verified value
                terms = []
                for j in range(n):
                    a = m0[i, j]
                    if a == 0:
                        continue
                    piece = rf"{sp.latex(abs(a))}\left({sp.latex(xp[j])}\right)"
                    terms.append(("-" if a < 0 else "+", piece))
                body = "".join(f" {sg} {pc}" for sg, pc in terms).strip()
                body = body[2:] if body.startswith("+ ") else body
                tex = MathTex(body + " = " + sp.latex(m0[i, n]), color=S.TEXT, font_size=S.MATH_SIZE - 6)
                tick = self.text("✓", size=S.BODY_SIZE + 6, color=S.RESULT)
                rows.append(VGroup(tex, tick).arrange(RIGHT, buff=0.3))
        else:
            rows.append(self.text("Independent check: SymPy's own rref() gives the same matrix ✓", size=S.BODY_SIZE))
        group = VGroup(*rows).arrange(DOWN, buff=0.35)
        self.fit(group)
        group.qa_name = "check"
        self.register(group)
        with self.narrate(line, "check"):
            for r in rows:
                self.play(Write(r), run_time=0.9)
        self.play(FadeOut(group), run_time=0.5)
        self.unregister(group)

    def recap(self, line):
        bullets = VGroup(*[self.text(t, size=S.BODY_SIZE) for t in (
            "1.  Get a leading 1 (swap / scale)",
            "2.  Make zeros below it",
            "3.  Move to the next column",
            "4.  Make zeros above every leading 1")]).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        self.fit(bullets)
        bullets.qa_name = "recap"
        self.register(bullets)
        with self.narrate(line, "recap"):
            for b in bullets:
                self.play(FadeIn(b, shift=0.2 * RIGHT), run_time=0.5)
        self.play(FadeOut(bullets), run_time=0.5)
        self.unregister(bullets)

    def practice(self, line):
        practice = self.job.get("practice")
        if not practice:
            return
        head = self.text("Your turn", size=S.TITLE_SIZE - 4, color=S.PIVOT)
        body = MathTex(practice["latex"], color=S.TEXT, font_size=S.MATH_SIZE - 4)
        group = VGroup(head, body).arrange(DOWN, buff=0.45)
        self.fit(group)
        group.qa_name = "practice"
        self.register(group)
        with self.narrate(line, "practice"):
            self.play(FadeIn(head), Write(body), run_time=1.5)
        self.wait(1.0)
