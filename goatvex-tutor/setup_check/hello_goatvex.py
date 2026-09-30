"""5-second install check: LaTeX (MathTex) + FFmpeg + Edge TTS voiceover.

Run from the goatvex-tutor folder:

    manim -ql setup_check/hello_goatvex.py HelloGoatVex

The equation is produced by SymPy (``sympy.latex``), never typed by hand —
the same rule every GoatVex video follows.
"""

import sys
from pathlib import Path

import sympy as sp
from manim import DOWN, UP, FadeIn, MathTex, Text, Write
from manim_voiceover import VoiceoverScene

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tutor.video.voice import get_speech_service  # noqa: E402

x = sp.Symbol("x")
EQUATION = sp.latex(sp.Eq(sp.Derivative(x**2, x), sp.diff(x**2, x)))  # d/dx x² = 2x


class HelloGoatVex(VoiceoverScene):
    def construct(self):
        self.camera.background_color = "#0f1117"
        self.set_speech_service(get_speech_service())
        title = Text("GoatVex", font_size=56).to_edge(UP)
        eq = MathTex(EQUATION, font_size=72).shift(DOWN * 0.3)
        with self.voiceover(text="Hi, I'm GoatVex. The derivative of x squared is two x.") as tracker:
            self.play(FadeIn(title), run_time=0.8)
            self.play(Write(eq), run_time=max(1.0, tracker.duration - 1.0))
        self.wait(0.5)
