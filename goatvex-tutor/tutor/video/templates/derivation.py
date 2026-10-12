"""Generic step-by-step video for every problem type.

(1) problem → (2) picture (graph, area, rectangles, complex plane, vectors …)
→ (3) every verified step, the changed part highlighted → (4) checks → (5) recap
→ (6) practice problem (answer hidden).

On-screen math: ``sympy.latex()`` of the verified step objects only.
"""

from __future__ import annotations

import math

import numpy as np
import sympy as sp
from manim import (DOWN, LEFT, ORIGIN, RIGHT, UP, Arrow, Axes, Circle, Create, Dot, FadeIn, FadeOut, Indicate,
                   Line as MLine, MathTex, NumberPlane, Polygon, ReplacementTransform, Text,
                   TransformMatchingShapes, VGroup, Write, DashedLine, Angle)

from tutor.narration import generic
from tutor.text.latex import latex_of, tex
from tutor.video import style as S
from tutor.video.base import GoatVexScene
from tutor.video.templates.row_reduction import MatrixView


class Video(GoatVexScene):
    template_name = "derivation"

    def construct(self):
        sol = self.solution
        p = sol.problem
        script = generic.build(sol)
        from tutor import registry

        pt = registry.get(p.type)
        title = self.title(pt.title)
        statement = self.problem_mobject(sol)
        self.fit(statement, top=S.CONTENT_TOP - 0.1)
        statement.qa_name = "problem"
        self.register(statement)
        with self.narrate(script["intro"], "problem"):
            self.play(Write(title), run_time=1.0)
            self.play(FadeIn(statement, shift=0.3 * UP), run_time=1.2)
        self.play(FadeOut(statement), run_time=0.5)
        self.unregister(statement)

        self.picture(script["intuition"], sol)

        current = None
        label = None
        for step, line in script["steps"]:
            current, label = self.show_step(step, line, current, label)
        if label is not None:
            self.play(FadeOut(label), run_time=0.3)
            self.unregister(label)

        with self.narrate(script["result"], "result"):
            box = self.answer_mobject(sol)
            if current is not None:
                self.play(FadeOut(current), run_time=0.4)
                self.unregister(current)
            self.fit(box)
            box.qa_name = "answer"
            self.register(box)
            self.play(Write(box), run_time=1.2)
            self.play(Indicate(box, color=S.RESULT), run_time=0.8)
        self.play(FadeOut(box), run_time=0.4)
        self.unregister(box)

        self.checks(script["check"])
        self.recap(script["recap"])
        self.practice(script["practice"])

    # ------------------------------------------------------------------ pieces
    def problem_mobject(self, sol):
        s0 = sol.steps[0]
        p = sol.problem
        head = self.text(p.statement or "Problem", size=S.BODY_SIZE)
        if head.width > S.FRAME_W - 1.2:
            head.scale_to_fit_width(S.FRAME_W - 1.2)
        obj = s0.after if s0.after is not None else s0.before
        body = self.math(obj)
        return VGroup(head, body).arrange(DOWN, buff=0.5) if body is not None else VGroup(head)

    def math(self, obj, color=S.TEXT, highlight=None):
        """Mobject for a verified object (None if there is nothing to draw)."""
        if obj is None:
            return None
        if isinstance(obj, sp.MatrixBase):
            bar = self.solution.facts.get("n") if self.solution.problem.type == "matrix_inverse" and obj.cols > obj.rows else None
            return MatrixView(obj, bar).group
        if isinstance(obj, str):
            return self.text(obj.replace("_", " "), size=S.BODY_SIZE + 4, color=color)
        tex = latex_of(obj)
        iso = [latex_of(highlight)] if highlight is not None else []
        try:
            m = MathTex(tex, color=color, font_size=S.MATH_SIZE, substrings_to_isolate=[i for i in iso if i in tex])
            if iso and iso[0] in tex:
                m.set_color_by_tex(iso[0], S.CHANGE)
        except Exception:
            m = MathTex(tex, color=color, font_size=S.MATH_SIZE)
        return m

    def show_step(self, step, line, current, label):
        hl = step.data.get("replacement") if step.kind in ("derivative_rule", "integral_rule") else None
        new = self.math(step.after if step.after is not None else step.before, highlight=hl)
        new_label = self.text(step.operation, size=S.BODY_SIZE, color=S.CHANGE)
        if new_label.width > S.FRAME_W - 1.0:
            new_label.scale_to_fit_width(S.FRAME_W - 1.0)
        new_label.move_to([0, S.CONTENT_TOP - 0.3, 0])
        new_label.qa_name = "step label"
        if new is not None:
            self.fit(new, top=S.CONTENT_TOP - 0.75)
            new.qa_name = "step"
        with self.narrate(line, step.id):
            anims = []
            if label is not None:
                anims.append(ReplacementTransform(label, new_label))
                self.unregister(label)
            else:
                anims.append(FadeIn(new_label))
            self.register(new_label)
            if new is not None:
                continues = current is not None and step.data.get("chain", True)
                if continues and not isinstance(current, VGroup):
                    anims.append(TransformMatchingShapes(current, new))
                elif current is not None:
                    anims += [FadeOut(current, shift=0.3 * UP), FadeIn(new, shift=0.3 * UP)]
                else:
                    anims.append(Write(new))
                if current is not None:
                    self.unregister(current)
                self.register(new)
                self.play(*anims, run_time=S.TRANSFORM_TIME)
                current = new
            else:
                self.play(*anims, run_time=0.6)
        self.wait(S.STEP_PAUSE)
        return current, new_label

    def answer_mobject(self, sol):
        head = self.text(sol.answer_label, size=S.BODY_SIZE, color=S.MUTED)
        ans = sol.answer
        if isinstance(ans, sp.Symbol) and str(ans) in ("DNE", "undefined", "not_invertible", "cramer_does_not_apply"):
            body = self.text({"DNE": "the limit does not exist", "undefined": "not defined",
                              "not_invertible": "A is not invertible",
                              "cramer_does_not_apply": "Cramer's rule does not apply"}[str(ans)],
                             size=S.BODY_SIZE + 6, color=S.WARNING)
        else:
            body = self.math(ans, color=S.RESULT)
            if body is None:
                body = self.text(str(ans), color=S.RESULT)
        if sol.problem.type == "indefinite_integral" and "initial" not in sol.facts:
            body = VGroup(body, MathTex(r"+\,C", color=S.RESULT, font_size=S.MATH_SIZE)).arrange(RIGHT, buff=0.15)
        return VGroup(head, body).arrange(DOWN, buff=0.4)

    def checks(self, line):
        finals = [c for c in self.result.checks if c.step_id == "final" and c.ok][:4]
        rows = [VGroup(self.text("✓", color=S.RESULT, size=S.BODY_SIZE + 2),
                       self.text(c.check, size=S.BODY_SIZE - 2)).arrange(RIGHT, buff=0.3) for c in finals]
        if not rows:
            rows = [self.text("✓  every step verified", color=S.RESULT)]
        group = VGroup(*rows).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        self.fit(group)
        group.qa_name = "checks"
        self.register(group)
        with self.narrate(line, "check"):
            for r in rows:
                self.play(FadeIn(r, shift=0.2 * RIGHT), run_time=0.5)
        self.play(FadeOut(group), run_time=0.4)
        self.unregister(group)

    def recap(self, line):
        t = self.text(line.caption(), size=S.BODY_SIZE)
        words = line.caption().split()
        # wrap to ~42 characters per line
        lines, cur = [], ""
        for w in words:
            if len(cur) + len(w) > 42:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        lines.append(cur)
        t = VGroup(*[self.text(l_, size=S.BODY_SIZE + 2) for l_ in lines]).arrange(DOWN, buff=0.2)
        head = self.text("Recap", size=S.TITLE_SIZE - 6, color=S.PIVOT)
        group = VGroup(head, t).arrange(DOWN, buff=0.4)
        self.fit(group)
        group.qa_name = "recap"
        self.register(group)
        with self.narrate(line, "recap"):
            self.play(FadeIn(group), run_time=0.8)
        self.play(FadeOut(group), run_time=0.4)
        self.unregister(group)

    def practice(self, line):
        practice = self.job.get("practice")
        if not practice:
            return
        head = self.text("Your turn", size=S.TITLE_SIZE - 4, color=S.PIVOT)
        body = None
        if practice.get("latex"):
            try:
                body = MathTex(practice["latex"], color=S.TEXT, font_size=S.MATH_SIZE - 4)
            except Exception:
                body = None
        if body is None:
            body = self.text(practice["statement"], size=S.BODY_SIZE)
        group = VGroup(head, body).arrange(DOWN, buff=0.45)
        self.fit(group)
        group.qa_name = "practice"
        self.register(group)
        with self.narrate(line, "practice"):
            self.play(FadeIn(head), Write(body), run_time=1.5)
        self.wait(1.0)

    # ------------------------------------------------------------------ pictures
    def picture(self, line, sol):
        t = sol.problem.type
        draw = {
            "derivative": self.pic_function_and_derivative, "log_differentiation": self.pic_function_and_derivative,
            "tangent_line": self.pic_tangent, "definite_integral": self.pic_area, "riemann_sum": self.pic_riemann,
            "indefinite_integral": self.pic_antiderivative, "limit": self.pic_limit,
            "determinant": self.pic_determinant, "matrix_inverse": self.pic_inverse, "complex": self.pic_complex,
            "geometry": self.pic_vectors,
            "optimization": self.pic_graph, "curve_sketching": self.pic_graph, "higher_derivative": self.pic_graph,
            "function_domain": self.pic_graph, "inverse_derivative": self.pic_graph, "linearization": self.pic_tangent,
            "area_between_curves": self.pic_between, "volume_of_revolution": self.pic_between,
            "improper_integral": self.pic_improper, "inverse_function": self.pic_inverse_function,
            "eigen": self.pic_eigen, "linear_transformation": self.pic_transformation,
        }.get(t)
        mobs = []
        try:
            mobs = draw(sol) if draw else []
        except Exception:
            mobs = []
        group = VGroup(*mobs) if mobs else None
        if group is not None:
            self.fit(group)
            group.qa_name = "picture"
            self.register(group)
        with self.narrate(line, "intuition"):
            if group is not None:
                for m in mobs:
                    self.play(Create(m) if not isinstance(m, (MathTex, Text)) else FadeIn(m), run_time=0.9)
            else:
                self.wait(0.5)
        if group is not None:
            self.play(FadeOut(group), run_time=0.5)
            self.unregister(group)

    def _axes_for(self, fns, x, x_range, y_clip=8.0, extra_y=(), square=False):
        """Axes + graphs. ``extra_y``: values that must be visible (marked points, an axis of revolution).
        ``square``: same scale on both axes (needed where angles matter, e.g. the mirror line y = x)."""
        xs = np.linspace(x_range[0], x_range[1], 400)
        ys = []
        lams = [sp.lambdify(x, f, "numpy") for f in fns]
        for lam in lams:
            with np.errstate(all="ignore"):
                v = np.array(lam(xs), dtype=complex) * np.ones_like(xs)
            v = np.where(np.abs(v.imag) < 1e-9, v.real, np.nan)
            ys.append(v)
        allv = np.concatenate([v[np.isfinite(v)] for v in ys]) if ys else np.array([0.0])
        lo, hi = (np.percentile(allv, 3), np.percentile(allv, 97)) if allv.size else (-1, 1)
        lo, hi = max(lo, -y_clip), min(hi, y_clip)
        for yv in extra_y:
            lo, hi = min(lo, float(yv)), max(hi, float(yv))
        if hi - lo < 1:
            lo, hi = lo - 1, hi + 1
        pad = 0.15 * (hi - lo)
        if square:
            lo, hi, pad = x_range[0], x_range[1], 0.0
        axes = Axes(x_range=[x_range[0], x_range[1], max(1, round((x_range[1] - x_range[0]) / 8))],
                    y_range=[lo - pad, hi + pad, max(0.5, round((hi - lo) / 6, 1))],
                    x_length=5.2 if square else 8.5, y_length=5.2 if square else 4.6,
                    axis_config={"color": S.MUTED, "include_ticks": True})
        graphs = []
        ylo, yhi = lo - pad, hi + pad
        for k, (lam, v) in enumerate(zip(lams, ys)):
            # draw only where the function is real and inside the window: never clamp (a flat line would lie)
            inside = np.isfinite(v) & (v >= ylo) & (v <= yhi)
            runs, start = [], None
            for i, flag in enumerate(inside):
                if flag and start is None:
                    start = i
                if (not flag or i == len(inside) - 1) and start is not None:
                    end = i if flag else i - 1
                    if end - start >= 2:
                        runs.append((xs[start], xs[end]))
                    start = None
            for a_, b_ in runs:
                def fn(t, lam=lam):
                    with np.errstate(all="ignore"):
                        return float(np.real(lam(t)))
                graphs.append(axes.plot(fn, x_range=[a_, b_, (b_ - a_) / 120], color=S.SERIES[k % len(S.SERIES)],
                                        use_smoothing=False))
        return axes, graphs

    def pic_function_and_derivative(self, sol):
        x = sol.facts.get("variable") or sol.facts.get("x")
        f = sol.facts.get("function") or sol.facts.get("f")
        rng = (0.05, 4) if sol.problem.type == "log_differentiation" else (-3, 3)
        axes, graphs = self._axes_for([f, sol.answer], x, rng)
        lab = VGroup(MathTex("f(x) = " + tex(f), color=S.SERIES[0], font_size=30),
                     MathTex("f'(x)", color=S.SERIES[1], font_size=30)).arrange(DOWN, aligned_edge=LEFT)
        lab.next_to(axes, RIGHT, buff=0.2)
        return [axes, *graphs, lab]

    def pic_tangent(self, sol):
        f = sol.facts
        x, fn, a = f["x"], f["f"], float(f["a"])
        axes, graphs = self._axes_for([fn, f["line"].rhs], x, (a - 3, a + 3))
        dot = Dot(axes.c2p(a, float(f["fa"])), color=S.RESULT)
        return [axes, *graphs, dot]

    def pic_area(self, sol):
        f = sol.facts
        x, fn, a, b = f["variable"], f["integrand"], float(f["a"]), float(f["b"])
        span = b - a
        axes, graphs = self._axes_for([fn], x, (a - 0.3 * span, b + 0.3 * span), y_clip=1e9)
        lam = sp.lambdify(x, fn, "numpy")
        g = axes.plot(lambda t: float(lam(t)), x_range=[a, b, (b - a) / 120], color=S.SERIES[0], use_smoothing=False)
        area = axes.get_area(g, x_range=[a, b], color=S.CHANGE, opacity=0.35)
        return [axes, *graphs, area]

    def pic_riemann(self, sol):
        f = sol.facts
        x, fn, a, b, n = f["variable"], f["f"], float(f["a"]), float(f["b"]), f["n"]
        axes, graphs = self._axes_for([fn], x, (a - 0.2 * (b - a), b + 0.2 * (b - a)), y_clip=1e9)
        lam = sp.lambdify(x, fn, "numpy")
        g = axes.plot(lambda t: float(lam(t)), x_range=[a, b, (b - a) / 120], color=S.SERIES[0], use_smoothing=False)
        method = {"left": "left", "right": "right", "midpoint": "center", "trapezoid": "left"}[f["method"]]
        rects = axes.get_riemann_rectangles(g, x_range=[a, b], dx=(b - a) / n, input_sample_type=method,
                                            fill_opacity=0.45, color=[S.CHANGE, S.ACCENT])
        return [axes, *graphs, rects]

    def pic_antiderivative(self, sol):
        f = sol.facts
        x = f["variable"]
        dom = (0.1, 4) if f.get("domain") or sol.answer.has(sp.log) else (-3, 3)
        axes, graphs = self._axes_for([f["integrand"], f["F"]], x, dom)
        lab = VGroup(MathTex("f", color=S.SERIES[0], font_size=32), MathTex("F", color=S.SERIES[1], font_size=32))
        lab.arrange(DOWN).next_to(axes, RIGHT, buff=0.2)
        return [axes, *graphs, lab]

    def pic_limit(self, sol):
        f = sol.facts
        x, fn, a = f["variable"], f["function"], f["point"]
        if a.is_infinite:
            rng = (1, 30) if a > 0 else (-30, -1)
            axes, graphs = self._axes_for([fn], x, rng)
            return [axes, *graphs]
        a = float(a)
        axes, graphs = self._axes_for([fn], x, (a - 2.5, a + 2.5))
        ans = sol.answer
        mobs = [axes, *graphs]
        if ans.is_number and ans.is_finite and ans.is_real:
            hole = Circle(radius=0.08, color=S.RESULT).move_to(axes.c2p(a, float(ans)))
            guide = DashedLine(axes.c2p(a, axes.y_range[0]), axes.c2p(a, axes.y_range[1]), color=S.MUTED)
            mobs += [guide, hole]
        return mobs

    def pic_determinant(self, sol):
        m = sol.facts["input"]
        if m.shape != (2, 2):
            return []
        plane = NumberPlane(x_range=[-6, 6, 1], y_range=[-4, 4, 1], x_length=8, y_length=5.3,
                            background_line_style={"stroke_color": S.MUTED, "stroke_opacity": 0.3})
        c1, c2 = [float(v) for v in m[:, 0]], [float(v) for v in m[:, 1]]
        sq = Polygon(plane.c2p(0, 0), plane.c2p(1, 0), plane.c2p(1, 1), plane.c2p(0, 1), color=S.MUTED,
                     fill_opacity=0.3)
        par = Polygon(plane.c2p(0, 0), plane.c2p(*c1), plane.c2p(c1[0] + c2[0], c1[1] + c2[1]), plane.c2p(*c2),
                      color=S.CHANGE, fill_opacity=0.35)
        return [plane, sq, par]

    def pic_inverse(self, sol):
        m = sol.facts["input"]
        if m.shape != (2, 2) or not sol.facts.get("invertible"):
            return []
        plane = NumberPlane(x_range=[-6, 6, 1], y_range=[-4, 4, 1], x_length=8, y_length=5.3,
                            background_line_style={"stroke_color": S.MUTED, "stroke_opacity": 0.3})
        c1, c2 = [float(v) for v in m[:, 0]], [float(v) for v in m[:, 1]]
        e1 = Arrow(plane.c2p(0, 0), plane.c2p(1, 0), buff=0, color=S.PIVOT)
        e2 = Arrow(plane.c2p(0, 0), plane.c2p(0, 1), buff=0, color=S.PIVOT)
        a1 = Arrow(plane.c2p(0, 0), plane.c2p(*c1), buff=0, color=S.CHANGE)
        a2 = Arrow(plane.c2p(0, 0), plane.c2p(*c2), buff=0, color=S.CHANGE)
        return [plane, e1, e2, a1, a2]

    def pic_complex(self, sol):
        f = sol.facts
        task = f["task"]
        pts = []
        if task in ("polar", "power"):
            pts = [f["z"]]
        elif task == "roots":
            pts = list(sol.answer)
        elif task == "quadratic":
            pts = list(sol.answer)
        else:
            pts = [sol.answer]
        vals = [complex(sp.N(z)) for z in pts]
        R = max(2.0, max(abs(v) for v in vals) * 1.3)
        plane = NumberPlane(x_range=[-R, R, max(1, round(R / 4))], y_range=[-R, R, max(1, round(R / 4))],
                            x_length=5.4, y_length=5.4,
                            background_line_style={"stroke_color": S.MUTED, "stroke_opacity": 0.3})
        mobs = [plane]
        for k, v in enumerate(vals):
            mobs.append(Arrow(plane.c2p(0, 0), plane.c2p(v.real, v.imag), buff=0, color=S.SERIES[k % 4]))
        if task == "roots":
            r = abs(vals[0])
            mobs.append(Circle(radius=plane.c2p(r, 0)[0] - plane.c2p(0, 0)[0], color=S.MUTED).move_to(plane.c2p(0, 0)))
        return mobs

    def _range_for(self, sol, default=(-4.0, 4.0)):
        f = sol.facts
        iv = f.get("interval")
        if isinstance(iv, sp.Interval) and iv.inf.is_finite and iv.sup.is_finite:
            lo, hi = float(iv.inf), float(iv.sup)
            pad = 0.15 * (hi - lo)
            return lo - pad, hi + pad
        if "a" in f and "b" in f and f["a"].is_finite and f["b"].is_finite and f["a"] != f["b"]:
            lo, hi = float(f["a"]), float(f["b"])
            pad = 0.3 * (hi - lo)
            return lo - pad, hi + pad
        if "a" in f and f["a"].is_finite:
            a = float(f["a"])
            return a - 3, a + 3
        return default

    def pic_graph(self, sol):
        """The function's graph; for optimization the absolute max/min points (verified values) are marked."""
        f = sol.facts
        x, fn = f["x"], f["f"]
        marks = [f[k] for k in ("max", "min") if f.get("closed") and k in f]
        if sol.problem.type == "inverse_derivative":
            marks.append(f["b"])
        axes, graphs = self._axes_for([fn], x, self._range_for(sol), extra_y=marks)
        mobs = [axes, *graphs]
        if f.get("closed") and "argmax" in f:
            for xv, yv, col in ((f["argmax"], f["max"], S.PIVOT), (f["argmin"], f["min"], S.CHANGE)):
                mobs.append(Dot(axes.c2p(float(xv), float(yv)), color=col, radius=0.09))
        if sol.problem.type == "inverse_derivative":
            mobs.append(Dot(axes.c2p(float(f["a"]), float(f["b"])), color=S.RESULT, radius=0.09))
        return mobs

    def pic_between(self, sol):
        """The region between the curves (for volumes: the region that gets revolved)."""
        f = sol.facts
        x, a, b = f["x"], float(f["a"]), float(f["b"])
        fns = [f["f"]] + ([f["g"]] if f.get("g") is not None else [])
        axis = str(f.get("axis", "x"))
        horizontal_axis = axis == "x" or axis.startswith("y=")  # revolved about a horizontal line y = c
        extra = [float(f.get("c") or 0)] if sol.problem.type == "volume_of_revolution" and horizontal_axis else []
        axes, graphs = self._axes_for(fns, x, self._range_for(sol), y_clip=1e9, extra_y=extra)
        lams = [sp.lambdify(x, g_, "numpy") for g_ in fns]
        top = axes.plot(lambda t: float(lams[0](t)), x_range=[a, b, (b - a) / 120], color=S.SERIES[0],
                        use_smoothing=False)
        if len(lams) > 1:
            bot = axes.plot(lambda t: float(lams[1](t)), x_range=[a, b, (b - a) / 120], color=S.SERIES[1],
                            use_smoothing=False)
            area = axes.get_area(top, x_range=[a, b], bounded_graph=bot, color=S.CHANGE, opacity=0.35)
        else:
            area = axes.get_area(top, x_range=[a, b], color=S.CHANGE, opacity=0.35)
        mobs = [axes, *graphs, area]
        if sol.problem.type == "volume_of_revolution":
            axis, c = str(f.get("axis", "x")), float(f.get("c") or 0)
            horizontal = axis == "x" or axis.startswith("y=")  # revolve about a horizontal line y = c
            if horizontal and axes.y_range[0] <= c <= axes.y_range[1]:
                mobs.append(DashedLine(axes.c2p(axes.x_range[0], c), axes.c2p(axes.x_range[1], c), color=S.PIVOT))
            elif not horizontal and axes.x_range[0] <= c <= axes.x_range[1]:
                mobs.append(DashedLine(axes.c2p(c, axes.y_range[0]), axes.c2p(c, axes.y_range[1]), color=S.PIVOT))
        return mobs

    def pic_improper(self, sol):
        f = sol.facts
        x, fn = f["x"], f["f"]
        a = float(f["a"]) if f["a"].is_finite else -10.0
        b = float(f["b"]) if f["b"].is_finite else a + 10.0
        axes, graphs = self._axes_for([fn], x, (a, b), y_clip=6.0)
        lam = sp.lambdify(x, fn, "numpy")
        eps = 1e-3 * (b - a)
        lo_y, hi_y = axes.y_range[0], axes.y_range[1]
        g = axes.plot(lambda t: float(min(max(lam(t), lo_y), hi_y)), x_range=[a + eps, b - eps, (b - a) / 200],
                      color=S.SERIES[0], use_smoothing=False)
        area = axes.get_area(g, x_range=[a + eps, b - eps], color=S.CHANGE, opacity=0.35)
        return [axes, *graphs, area]

    def pic_inverse_function(self, sol):
        f = sol.facts
        x = f["x"]
        lo = f["domain"].inf
        rng = (float(lo) - 0.5, float(lo) + 4.5) if lo.is_finite else (-4, 4)
        axes, graphs = self._axes_for([f["f"], f["finv"], x], x, rng, square=True)
        return [axes, *graphs]

    def _plane(self, R):
        return NumberPlane(x_range=[-R, R, 1], y_range=[-R, R, 1], x_length=5.4, y_length=5.4,
                           background_line_style={"stroke_color": S.MUTED, "stroke_opacity": 0.3})

    def pic_eigen(self, sol):
        """Each eigenvector v and A·v = λv on the same line through the origin (2×2, real eigenvalues)."""
        f = sol.facts
        A = f["matrix"]
        if A.shape != (2, 2) or not all(lv.is_real for lv in f["eigenvalues"]):
            return []
        pairs = [(lv, v) for lv in f["eigenvalues"] for v in f["spaces"][lv]]
        unit = [(lv, v / sp.sqrt(v.dot(v))) for lv, v in pairs]
        R = max(3.0, 1.3 * max(abs(float(lv)) for lv, _ in unit))
        plane = self._plane(round(R))
        mobs = [plane]
        for k, (lv, u) in enumerate(unit):
            ux, uy = float(u[0]), float(u[1])
            col = S.SERIES[k % len(S.SERIES)]
            mobs.append(DashedLine(plane.c2p(-R * ux, -R * uy), plane.c2p(R * ux, R * uy), color=col,
                                   stroke_opacity=0.6))
            Av = A * u  # = λu (verified eigenvector), drawn from the matrix product itself
            mobs.append(Arrow(plane.c2p(0, 0), plane.c2p(float(Av[0]), float(Av[1])), buff=0, color=col))
            mobs.append(Arrow(plane.c2p(0, 0), plane.c2p(ux, uy), buff=0, color=S.TEXT, stroke_width=7))  # v on top
        return mobs

    def pic_transformation(self, sol):
        f = sol.facts
        A = f.get("A")
        if not f.get("linear") or A is None or A.shape != (2, 2):
            return []
        c1, c2 = [float(v) for v in A[:, 0]], [float(v) for v in A[:, 1]]
        R = max(3.0, 1.3 * max(abs(v) for v in c1 + c2 + [c1[0] + c2[0], c1[1] + c2[1]]))
        plane = self._plane(round(R))
        sq = Polygon(plane.c2p(0, 0), plane.c2p(1, 0), plane.c2p(1, 1), plane.c2p(0, 1), color=S.MUTED,
                     fill_opacity=0.3)
        par = Polygon(plane.c2p(0, 0), plane.c2p(*c1), plane.c2p(c1[0] + c2[0], c1[1] + c2[1]), plane.c2p(*c2),
                      color=S.CHANGE, fill_opacity=0.3)
        arrows = [Arrow(plane.c2p(0, 0), plane.c2p(*c), buff=0, color=S.SERIES[k]) for k, c in enumerate((c1, c2))]
        return [plane, sq, par, *arrows]

    def pic_vectors(self, sol):
        p = sol.problem
        vecs = [p.vec(k) for k in ("u", "v") if k in p.given]
        if not vecs or vecs[0].rows != 2:
            return []
        R = max(3.0, max(abs(float(c)) for v in vecs for c in v) * 1.3)
        plane = NumberPlane(x_range=[-R, R, 1], y_range=[-R, R, 1], x_length=5.4, y_length=5.4,
                            background_line_style={"stroke_color": S.MUTED, "stroke_opacity": 0.3})
        arrows = [Arrow(plane.c2p(0, 0), plane.c2p(float(v[0]), float(v[1])), buff=0, color=S.SERIES[k])
                  for k, v in enumerate(vecs)]
        return [plane, *arrows]
