# GoatVex

A personal, **verified** math tutor for Carleton's MATH 1104 (Linear Algebra I)
and MATH 1004 (Calculus), running inside Claude Code.

GoatVex's rule: the AI never invents math. Every step comes from a computer
algebra system (SymPy) and is machine-checked before you see it, hear it, or
watch it. See `CLAUDE.md` for the full accuracy contract.

## What it does

- **/solve**: worked solutions where every step is checked, a KaTeX write-up page, and a
  3Blue1Brown-style video with voice (Edge TTS, `en-CA-LiamNeural`) and captions.
- **/hint**: one hint at a time. This is the default for graded assignments.
- **/check**: finds the first wrong line in your own work and names the mistake.
- **/explain**: the idea first, visually, then a verified example and a video.
- **/practice**: problems with hidden answers that come back on a spaced-repetition
  schedule and focus on your weak spots.
- **/testprep**: timed mock tests built from the course plan, with a weak-spot report.
- **/progress**: upcoming tests, reviews due, mistake patterns.
- 31 problem types covering every topic in both course plans.
- Uses your professor's notation, detected from your course PDFs.

## Getting started

- **Install:** see [SETUP.md](SETUP.md) (Windows).
- **Course materials:** put lecture notes, slides and textbook PDFs in `materials/MATH1104/` and
  `materials/MATH1004/`, then run `python -m tutor materials ingest`. They stay on your PC.
- **Try it:** `python -m tutor show tests/benchmark/MATH1104/rref-sys-unique-3x3.json`, then
  `python -m tutor solve tests/benchmark/MATH1104/rref-sys-unique-3x3.json --open`.
- **Example output:** `videos/*/*/*/` (verification reports, captions, write-ups).
- **Tests:** `python -m pytest` runs the 165 known-answer benchmarks, the "plant a mistake and make
  sure it's caught" tests, the narration lint, and tests for every study mode.
