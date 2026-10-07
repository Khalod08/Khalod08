# Setting up GoatVex on Windows

This installs everything GoatVex needs. You can use it again to reinstall on
another PC. It takes about 15–30 minutes, mostly waiting for downloads
(MiKTeX is the big one).

## What gets installed, and why

| Piece | Why GoatVex needs it |
|---|---|
| **Python 3.12** (or 3.11; not 3.13+, which removed a module the voiceover library needs) | Runs the math engine (SymPy) and Manim. |
| **FFmpeg** | Encodes the videos and mixes in the voice. |
| **MiKTeX** (LaTeX) | Typesets the equations in the videos (Manim's `MathTex`). |
| **A virtual environment** (`.venv`) | Keeps GoatVex's Python packages separate so nothing else on your PC breaks. |
| `sympy`, `mpmath`, `numpy` | The computer algebra system and numeric cross-checks. This is where every number comes from. |
| `manim`, `manim-voiceover` | 3Blue1Brown-style animation, synced to narration. |
| `edge-tts` | Free Microsoft Edge voices (we use `en-CA-LiamNeural`). Needs internet. |
| `pymupdf` | Reads your textbook and lecture PDFs (Phase 5). |
| `pytest` | Runs the known-answer tests that keep the solver honest. |

## Option A: the setup script (recommended)

1. Put the `goatvex-tutor` folder somewhere simple, e.g. `C:\Users\<you>\goatvex-tutor`.
2. Open **PowerShell** in that folder (in File Explorer, click the address bar, type `powershell`, press Enter).
3. Run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
   ```

The script checks each piece, tells you what it is, and **asks before installing
anything**. At the end it runs the checks and the tests, then renders a
5-second test video with an equation and a voice line.

## Option B: step by step, by hand

```powershell
# 1. Tools (skip any you already have)
winget install -e --id Python.Python.3.12
winget install -e --id Gyan.FFmpeg
winget install -e --id MiKTeX.MiKTeX
# Close PowerShell and open a new one so the new PATH is picked up.

# 2. Let MiKTeX download missing LaTeX packages by itself (no pop-ups mid-render)
initexmf --set-config-value "[MPM]AutoInstall=1"

# 3. Virtual environment + packages (run inside the goatvex-tutor folder)
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Check everything
python scripts\check_env.py --voice
python -m pytest
manim -ql setup_check\hello_goatvex.py HelloGoatVex
```

The test video lands in `media\videos\hello_goatvex\480p15\HelloGoatVex.mp4`.
You should hear "Hi, I'm GoatVex. The derivative of x squared is two x." while
d/dx x² = 2x is written on screen.

## Every time you open a new terminal

```powershell
cd C:\Users\<you>\goatvex-tutor
.venv\Scripts\Activate.ps1
```

Then start Claude Code **from inside the `goatvex-tutor` folder** so it
loads GoatVex's `CLAUDE.md` and the slash commands (`/solve`, `/hint`, `/check`,
`/explain`, `/practice`, `/testprep`, `/progress`).

## Adding your course materials

1. Copy your PDFs (lecture notes, slides, the textbook, past tests) into
   `materials\MATH1104\` or `materials\MATH1004\`. PowerPoint files: open them and
   *Save As → PDF* first.
2. Run `python -m tutor materials ingest`.

GoatVex then knows where each topic is in your materials ("this is in Lecture 7,
slide 12") and uses your professor's notation (see `materials\<course>\notation.md`).
The PDFs and their extracted text never leave your PC and are never committed to git.

## Troubleshooting

- **"running scripts is disabled on this system"** when activating: run
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again.
- **`latex` or `ffmpeg` not found** right after installing: close and reopen
  PowerShell. Windows only updates PATH for new terminals.
- **The first render is slow or MiKTeX shows a package pop-up**: MiKTeX is
  downloading LaTeX packages the first time they're used. Allow it; later
  renders are fast.
- **"SoX could not be found!" warning**: harmless. SoX is only used to change
  voice speed, which GoatVex doesn't do. Ignore it.
- **Edge TTS fails**: it needs internet. For an offline preview with silent
  audio (timing only), set `$env:GOATVEX_VOICE = "silent"` before rendering.
  Final videos always use the real voice.
- **Unicode math looks garbled in the terminal**: use Windows Terminal (the
  default on Windows 11). GoatVex switches its output to UTF-8 automatically.
