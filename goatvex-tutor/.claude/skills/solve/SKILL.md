---
name: solve
description: Full verified solution of a math problem (MATH 1104 or MATH 1004) — transcribe, confirm with the student, solve with SymPy, verify every step, KaTeX write-up and a narrated Manim video. Use when the student asks to solve or explain how to do a specific problem.
---

# /solve — verified worked solution + video

Follow the accuracy contract in CLAUDE.md exactly. Never compute the math yourself.

1. **Graded?** If the student says it's a graded assignment, or you're not sure, ask. For
   graded work, don't solve it. Offer `/hint` or a parallel problem instead: make a new
   problem.json with changed numbers of the same type (`python -m tutor practice new --type <type>`
   also works).
2. **Transcribe** the problem (text, photo, screenshot or PDF page) into
   `problems/<slug>.json` (schema: `tutor/parse/problem.schema.json`; `python -m tutor types`
   lists the types and the keys each one needs). Use exact strings ("1/3", not 0.333).
   Set `course`, `topic`, and `source` (e.g. {"book": "Nicholson", "section": "2.4", "exercise": "7"}).
3. **Confirm.** Run `python -m tutor show problems/<slug>.json` and show its output, then ask:
   **"Is this exactly the problem?"** Wait for a clear yes. If a photo is blurry, ask instead
   of guessing. Then run `python -m tutor confirm problems/<slug>.json`.
4. **Solve + verify:** `python -m tutor solve problems/<slug>.json --open --log`
   (`--log` records the studied example in `student/progress.json`).
   - Status FAIL/INCONCLUSIVE, or `UnsupportedProblem`: say so plainly. Don't solve it by
     hand and present it as verified. You may discuss the idea in words, labelled
     "not machine-verified".
   - PASS: the write-up `solution.html` opens in the browser.
5. **In chat:** give a short summary in readable Unicode (x², √x, ∫, λ, A⁻¹, R₂ → R₂ − 3R₁):
   the method, the key steps, and the answer, all quoted from the solver output. Never raw
   LaTeX, never math in code blocks.
6. **Video:** `python -m tutor.video.render videos/<course>/<topic>/<slug>/problem.json` (preview).
   Look at every key frame in `frames/` with the Read tool. Check for overlaps, math cut off,
   captions covering equations, and wrong highlights. Fix the template or layout and
   re-render until it's clean. Then run the same command with `--final` (1080p60). If Edge
   TTS can't be reached, render with `--voice silent` and tell the student the voice will be
   added when online.
7. Point to the practice problem at the end of the write-up/video (answer hidden) and offer
   to check their answer: `/practice` or just type it.
