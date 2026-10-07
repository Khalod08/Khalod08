---
name: check
description: Check the student's own work line by line against the verified solution, find the first wrong line, name the mistake type (sign error, chain rule, product/quotient rule, row-operation slip…), and log it to progress. Use when the student shares their attempt or answer.
---

# /check — find the first wrong line

1. Transcribe and confirm the **problem** as in `/solve` (steps 2–3).
2. Transcribe the student's **work** into `problems/<slug>.attempt.txt`, one step per line,
   exactly as they wrote it (mistakes included!). Don't fix anything.
   - matrices: one matrix per line, rows separated by `;` (e.g. `1 2 3; 0 1 4`)
   - algebra: `f'(x) = 2x cos(x^2)` (chains like `= … = …` are fine)
   - substitution or parts choices (`u = x^2`, `dv = e^x dx`) are skipped automatically
   Show the transcription and ask "Is this what you wrote?" before checking.
3. Run `python -m tutor check problems/<slug>.json problems/<slug>.attempt.txt --record`.
4. Report kindly, in readable Unicode:
   - what was right (✓ lines). Name the good moves.
   - the **first wrong line**, the mistake type, and the explanation from the output
   - for ungraded work, the "Compare with the verified solution, step k" line. For graded work,
     don't show the correct line. Ask a guiding question instead.
5. Mistakes are normal and useful. Suggest one specific thing to watch next time, and
   offer a short `/practice` on that topic.
6. `--record` logs the mistake type in `student/progress.json` (spaced repetition picks it up).
