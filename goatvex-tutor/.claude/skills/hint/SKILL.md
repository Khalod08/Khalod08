---
name: hint
description: Give a hint for a math problem, one level at a time, from the verified solution (strategy, then the first move, then its result, and so on). Default for graded assignments. Use when the student asks for a hint or is stuck.
---

# /hint — hint ladder

1. Transcribe and confirm the problem exactly as in `/solve` (steps 2–3). If it's graded
   work, set `"context": {"graded": true}` in problem.json: the ladder then never reveals
   the final answer or the last steps.
2. Start at level 1: `python -m tutor hint problems/<slug>.json --level 1`.
3. Give the student **only that hint**, in readable Unicode, then encourage them to try the
   next step on paper. Go one level up only when they ask, or when they've tried and are
   still stuck. Don't skip levels.
4. When they show a step, check it with `/check` rather than eyeballing it.
5. Hints come only from the verified steps the command prints. Never add your own
   computation. If the solver can't verify the problem, say so and stick to conceptual
   hints, labelled as not verified.
