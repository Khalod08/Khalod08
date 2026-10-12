---
name: explain
description: Explain a concept (e.g. "chain rule", "eigenvectors", "integration by parts") with visual intuition first, then a verified worked example, a write-up page and an explainer video. Use when the student asks what something means or why a method works.
---

# /explain <concept>

1. Find the matching verified problem type:
   `python -m tutor explain "<concept>" [--course MATH1104|MATH1004]`. It ranks types and
   shows textbook sections. If materials are indexed, also run
   `python -m tutor materials find "<concept>"` and cite where it is in their notes/textbook.
2. **Explain the idea in chat first, visually and calmly**: what it means geometrically,
   why it works, when to use it. This part is your explanation. Keep it conceptual: no
   specific computed numbers that didn't come from the solver. Use Unicode math only.
3. Build a **verified worked example** with easy numbers:
   `python -m tutor explain "<concept>" --make --open` (or `--type <type[:variant]>`). It writes
   problem.json + solution.html under `videos/<course>/<topic>/explain-…/`.
4. Walk through the example using the solver's steps (quote them; don't recompute).
5. Offer the video: `python -m tutor.video.render <that problem.json>`, then QA the key frames
   (see `/solve` step 6) before `--final`.
6. End with a practice problem: `python -m tutor practice new --type <type> --n 1`.
7. If no type matches: explain conceptually, clearly labelled "not machine-verified", and
   say GoatVex can't generate a checked example for it yet.
