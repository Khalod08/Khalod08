# GoatVex

A personal, **verified** math tutor for Carleton's MATH 1104 (Linear Algebra I)
and MATH 1004 (Calculus), running inside Claude Code.

GoatVex's rule: the AI never invents math. Every step comes from a computer
algebra system (SymPy) and is machine-checked before you see it, hear it, or
watch it. See `CLAUDE.md` for the full accuracy contract.

- **Install:** see [SETUP.md](SETUP.md) (Windows).
- **Try it:** `python -m tutor show tests/benchmark/MATH1104/rref-sys-unique-3x3.json`,
  then `python -m tutor solve` on the same file.
- **Example reports:** `videos/*/*/*/verification_report.md`.
- **Tests:** `python -m pytest` (known-answer benchmark + "plant a mistake, make
  sure it's caught" tests).

Build status: Phase 1 of 5 (verification engine) is done. Videos come in Phase 2.
