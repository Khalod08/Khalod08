"""Check that everything GoatVex needs is installed. Safe to run any time.

    python scripts/check_env.py            # checks tools + packages
    python scripts/check_env.py --voice    # also synthesizes one sentence with Edge TTS
"""

from __future__ import annotations

import argparse
import importlib
import io
import shutil
import subprocess
import sys
from pathlib import Path

OK, BAD, WARN = "✅", "❌", "⚠️ "

PACKAGES = {
    "sympy": "sympy",
    "mpmath": "mpmath",
    "numpy": "numpy",
    "manim": "manim",
    "manim_voiceover": "manim-voiceover",
    "edge_tts": "edge-tts",
    "pymupdf": "pymupdf",
    "pytest": "pytest",
}

TOOLS = {
    "ffmpeg": "FFmpeg (encodes the videos). Windows: winget install Gyan.FFmpeg",
    "latex": "LaTeX (typesets MathTex). Windows: winget install MiKTeX.MiKTeX",
    "dvisvgm": "dvisvgm (turns LaTeX into shapes; ships with MiKTeX)",
}


def main() -> int:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", action="store_true", help="also test Edge TTS (needs internet)")
    args = ap.parse_args()
    problems = 0

    v = sys.version_info
    good = (3, 11) <= v < (3, 13)
    print(f"{OK if good else BAD} Python {v.major}.{v.minor}.{v.micro} (need 3.11 or 3.12; 3.13+ removed audioop, "
          "which the voiceover library needs)")
    problems += not good
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    print(f"{OK if in_venv else WARN} virtual environment {'active' if in_venv else 'NOT active (activate .venv first)'}")

    for module, pip_name in PACKAGES.items():
        try:
            mod = importlib.import_module(module)
            ver = getattr(mod, "__version__", getattr(mod, "VersionBind", ""))
            print(f"{OK} {pip_name} {ver}")
        except Exception as exc:  # ImportError, or a broken native dependency
            print(f"{BAD} {pip_name} missing or broken ({type(exc).__name__}) → pip install -r requirements.txt")
            problems += 1

    for tool, why in TOOLS.items():
        path = shutil.which(tool)
        if path:
            print(f"{OK} {tool} found at {path}")
        else:
            print(f"{BAD} {tool} not found on PATH — {why}. Open a NEW terminal after installing.")
            problems += 1

    if shutil.which("latex"):
        tex = Path(__file__).resolve().parent / "_texcheck.tex"
        tex.write_text(r"\documentclass[preview]{standalone}\usepackage{amsmath}\begin{document}$x^2$\end{document}")
        try:
            r = subprocess.run(["latex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
                               cwd=tex.parent, capture_output=True, text=True, timeout=300)
            ok = r.returncode == 0
            print(f"{OK if ok else BAD} LaTeX can compile an amsmath document"
                  + ("" if ok else " — in MiKTeX Console enable 'Always install missing packages'"))
            problems += not ok
        except subprocess.TimeoutExpired:
            print(f"{WARN} LaTeX test timed out (MiKTeX may be downloading packages; run again)")
        finally:
            for ext in (".tex", ".aux", ".log", ".dvi"):
                tex.with_suffix(ext).unlink(missing_ok=True)

    if args.voice:
        try:
            import asyncio

            import edge_tts

            async def speak():
                comm = edge_tts.Communicate("GoatVex voice check.", "en-CA-LiamNeural")
                n = 0
                async for chunk in comm.stream():
                    n += chunk["type"] == "audio"
                return n

            chunks = asyncio.run(speak())
            print(f"{OK if chunks else BAD} Edge TTS voice en-CA-LiamNeural ({chunks} audio chunks)")
            problems += not chunks
        except Exception as exc:
            print(f"{BAD} Edge TTS failed: {type(exc).__name__}: {exc} (needs internet)")
            problems += 1

    print("\nAll good!" if problems == 0 else f"\n{problems} problem(s) found — see the ❌ lines above.")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
