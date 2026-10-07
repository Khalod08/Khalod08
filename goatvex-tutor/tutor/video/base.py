"""GoatVexScene: the base every video template extends.

Responsibilities
* load the job (problem + verified-solution digest) and re-solve; refuse to
  render anything that is not fully verified or whose digest changed;
* narrate Lines (linted; voice via Edge TTS) with burned-in captions that use
  the exact same chunks and times as the .srt subtitles;
* keep math inside the content zone and away from the caption band, and log
  every layout problem (off-screen, overlap, caption collision) for visual QA;
* record a timeline of segments so QA can pull key frames.
"""

from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from pathlib import Path

import numpy as np
from manim import (DOWN, LEFT, ORIGIN, RIGHT, UP, Create, FadeIn, FadeOut, Rectangle, Text, VGroup, Write, config)
from manim_voiceover import VoiceoverScene

from tutor.narration.script import Line
from tutor.video import style as S
from tutor.video.voice import get_speech_service


class NarrationLintError(RuntimeError):
    pass


class RenderRefused(RuntimeError):
    pass


def load_job():
    path = os.environ.get("GOATVEX_JOB")
    if not path:
        raise RenderRefused("GOATVEX_JOB is not set: render through `python -m tutor.video.render`")
    return json.loads(Path(path).read_text(encoding="utf-8")), Path(path)


def verified_solution(job):
    """Re-solve the confirmed problem and insist it is the exact solution that was verified."""
    from tutor.parse.schema import load_problem
    from tutor.pipeline import solve_problem

    problem = load_problem(job["problem"])
    result = solve_problem(problem)
    if not result.verified:
        raise RenderRefused(f"verification status is {result.status}: refusing to render")
    if result.solution.digest() != job["digest"]:
        raise RenderRefused("the solution changed since it was verified (digest mismatch): refusing to render")
    return result


# ------------------------------------------------------------------ captions
def split_template(template: str) -> list[str]:
    """Split a template into caption-sized pieces at sentence/clause ends (never inside {placeholders})."""
    pieces, buf, depth = [], "", 0
    for i, ch in enumerate(template):
        buf += ch
        depth += ch == "{"
        depth -= ch == "}"
        nxt = template[i + 1] if i + 1 < len(template) else " "
        if depth == 0 and ch in ".;:!?" and nxt == " ":
            pieces.append(buf.strip())
            buf = ""
    if buf.strip():
        pieces.append(buf.strip())
    return pieces


def caption_chunks(line: Line, max_chars: int = 64) -> list[tuple[str, str]]:
    """(spoken, caption) pairs, one per on-screen caption."""
    out = []
    for piece in split_template(line.template):
        sub = Line(piece, line.values)
        spoken, cap = sub.spoken(), sub.caption()
        if len(cap) <= max_chars:
            out.append((spoken, cap))
            continue
        # long piece: split both at commas (same template position) or, failing that, by words
        parts = [p.strip() for p in re.split(r"(?<=,)\s", piece) if p.strip()]
        if len(parts) > 1 and all("{" not in p or p.count("{") == p.count("}") for p in parts):
            for p_ in parts:
                s2 = Line(p_, line.values)
                out.append((s2.spoken(), s2.caption()))
        else:
            words = cap.split()
            half = len(words) // 2
            out.append((spoken, " ".join(words[:half])))
            out.append(("", " ".join(words[half:])))
    return out


class CaptionTrack(VGroup):
    """Shows caption k during [start_k, end_k) of the voiceover (driven by an updater)."""

    def __init__(self, timed: list[tuple[float, float, str]]):
        super().__init__()
        self.elapsed = 0.0
        self.timed = timed
        for start, end, text in timed:
            t = Text(text, font=S.font(), font_size=S.CAPTION_SIZE, color=S.TEXT)
            if t.width > S.FRAME_W - 2 * S.MARGIN - 0.4:
                t.scale_to_fit_width(S.FRAME_W - 2 * S.MARGIN - 0.4)
            bg = Rectangle(width=t.width + 0.5, height=t.height + 0.3, fill_color=S.CAPTION_BG,
                           fill_opacity=S.CAPTION_BG_OPACITY, stroke_width=0)
            g = VGroup(bg, t).move_to([0, S.CAPTION_Y, 0])
            g.set_opacity(0)
            self.add(g)
        self.add_updater(CaptionTrack._tick)

    def _tick(self, dt):
        self.elapsed += dt
        for (start, end, _), g in zip(self.timed, self.submobjects):
            on = start <= self.elapsed < end
            g[0].set_fill(opacity=S.CAPTION_BG_OPACITY if on else 0)
            g[1].set_opacity(1 if on else 0)


class GoatVexScene(VoiceoverScene):
    """Base scene: 2D. Templates needing 3D use GoatVex3DScene."""

    template_name = "base"

    # ------------------------------------------------------------------ setup
    def setup(self):
        super().setup()
        self.camera.background_color = S.BACKGROUND
        self.set_speech_service(get_speech_service(), create_subcaption=False)
        self.job, self.job_path = load_job()
        self.result = verified_solution(self.job)
        self.solution = self.result.solution
        self.timeline: list[dict] = []
        self.qa_issues: list[dict] = []
        self.blocks: list = []        # content mobjects that must not overlap each other
        self.fixed: list = []         # mobjects kept fixed in frame (3D scenes)

    def now(self) -> float:
        return float(self.renderer.time)

    # ------------------------------------------------------------------ narration + captions
    @contextmanager
    def narrate(self, line: Line, segment: str):
        problems = line.problems()
        if problems:
            raise NarrationLintError("; ".join(problems))
        chunks = caption_chunks(line)
        spoken = " ".join(" ".join(c[0] for c in chunks if c[0]).split())
        start_t = self.now()
        with self.voiceover(text=spoken) as tracker:
            timed = self._time_chunks(chunks, spoken, tracker)
            track = CaptionTrack(timed)
            self.add(track)
            self._fix(track)
            for st, en, text in timed:
                self.add_subcaption(text, duration=max(0.1, en - st), offset=st)
            yield tracker
        self.remove(track)
        self.timeline.append({"segment": segment, "start": round(start_t, 3), "end": round(self.now(), 3),
                              "caption": line.caption()})
        self.qa_check(segment)

    def _time_chunks(self, chunks, spoken, tracker):
        """Start time of each caption = time the voice reaches the first word of that chunk."""
        total = tracker.duration
        wbs = tracker.data.get("word_boundaries") or []
        xs = [wb["text_offset"] for wb in wbs]
        ys = [wb["audio_offset"] / 1e7 for wb in wbs]

        def time_at(char):
            if not xs:
                return total * char / max(1, len(spoken))
            return float(np.interp(char, xs, ys))

        timed, pos = [], 0
        starts = []
        for sp_, cap in chunks:
            if sp_:
                idx = spoken.find(sp_.split()[0], pos) if sp_.split() else pos
                idx = pos if idx < 0 else idx
                starts.append(time_at(idx))
                pos = idx + len(sp_)
            else:  # continuation of a long piece: split its time evenly
                starts.append(None)
        # fill continuations
        for k, s_ in enumerate(starts):
            if s_ is None:
                prev = starts[k - 1]
                nxt = next((t for t in starts[k + 1:] if t is not None), total)
                starts[k] = (prev + nxt) / 2
        for k, (_, cap) in enumerate(chunks):
            end = starts[k + 1] if k + 1 < len(chunks) else total
            timed.append((max(0.0, starts[k]), max(starts[k] + 0.3, end), cap))
        return timed

    def _fix(self, mob):
        pass  # 2D scenes: everything is already in the frame

    # ------------------------------------------------------------------ layout helpers
    def title(self, text: str) -> Text:
        t = Text(text, font=S.font(), font_size=S.TITLE_SIZE, color=S.TEXT)
        t.move_to([0, S.TITLE_Y, 0])
        if t.width > S.FRAME_W - 2 * S.MARGIN:
            t.scale_to_fit_width(S.FRAME_W - 2 * S.MARGIN)
        self._fix(t)
        return t

    def text(self, text: str, size=S.BODY_SIZE, color=S.TEXT) -> Text:
        return Text(text, font=S.font(), font_size=size, color=color)

    def fit(self, mob, top=S.CONTENT_TOP, bottom=S.CAPTION_TOP + 0.15, left=S.CONTENT_LEFT, right=S.CONTENT_RIGHT,
            center=True):
        """Scale mob down (never up) so it fits the content zone; optionally center it there."""
        w, h = right - left, top - bottom
        if mob.width > w:
            mob.scale_to_fit_width(w)
        if mob.height > h:
            mob.scale_to_fit_height(h)
        if center:
            mob.move_to([(left + right) / 2, (top + bottom) / 2, 0])
        return mob

    def register(self, *mobs):
        for m in mobs:
            if m not in self.blocks:
                self.blocks.append(m)

    def unregister(self, *mobs):
        for m in mobs:
            if m in self.blocks:
                self.blocks.remove(m)

    # ------------------------------------------------------------------ QA
    def qa_check(self, label: str):
        """Log content that leaves the frame, enters the caption band, or overlaps other content."""
        half_w, half_h = S.FRAME_W / 2, S.FRAME_H / 2
        visible = [m for m in self.blocks if m in self.mobjects or any(m in g.get_family() for g in self.mobjects)]
        for m in visible:
            if m.width == 0 and m.height == 0:
                continue
            l, r = m.get_left()[0], m.get_right()[0]
            t, b = m.get_top()[1], m.get_bottom()[1]
            name = getattr(m, "qa_name", type(m).__name__)
            if l < -half_w + 0.05 or r > half_w - 0.05 or t > half_h - 0.02 or b < -half_h + 0.02:
                self.qa_issues.append({"t": self.now(), "segment": label, "issue": "off-screen", "what": name})
            if b < S.CAPTION_TOP - 0.02:
                self.qa_issues.append({"t": self.now(), "segment": label, "issue": "in caption band", "what": name})
        for m in visible:  # pieces inside one block (e.g. matrix entries) must not overlap each other
            parts = getattr(m, "qa_parts", [])
            for i in range(len(parts)):
                for j in range(i + 1, len(parts)):
                    if _overlap(parts[i], parts[j], pad=0.0):
                        self.qa_issues.append({"t": self.now(), "segment": label, "issue": "overlap inside",
                                               "what": getattr(m, "qa_name", type(m).__name__)})
        for i in range(len(visible)):
            for j in range(i + 1, len(visible)):
                a, c = visible[i], visible[j]
                if _overlap(a, c):
                    self.qa_issues.append({"t": self.now(), "segment": label, "issue": "overlap",
                                           "what": f"{getattr(a, 'qa_name', type(a).__name__)} / "
                                                   f"{getattr(c, 'qa_name', type(c).__name__)}"})

    def tear_down(self):
        super().tear_down()
        out = Path(self.job["out_dir"])
        out.mkdir(parents=True, exist_ok=True)
        (out / "timeline.json").write_text(json.dumps(self.timeline, indent=2, ensure_ascii=False), encoding="utf-8")
        (out / "qa_layout.json").write_text(json.dumps(self.qa_issues, indent=2), encoding="utf-8")


def _overlap(a, b, pad: float = 0.02) -> bool:
    al, ar, at, ab = a.get_left()[0], a.get_right()[0], a.get_top()[1], a.get_bottom()[1]
    bl, br, bt, bb = b.get_left()[0], b.get_right()[0], b.get_top()[1], b.get_bottom()[1]
    return al < br - pad and bl < ar - pad and ab < bt - pad and bb < at - pad


try:
    from manim import ThreeDScene

    class GoatVex3DScene(GoatVexScene, ThreeDScene):
        """For templates with a 3D segment (planes, vectors in space). Captions/titles stay fixed in frame."""

        def _fix(self, mob):
            self.add_fixed_in_frame_mobjects(mob)
except ImportError:  # pragma: no cover
    GoatVex3DScene = GoatVexScene
