---
name: progress
description: Show the student's progress — upcoming tests, topics practiced, accuracy, spaced-repetition reviews due, weak spots and mistake patterns — as a short chat summary and an HTML report. Use for "how am I doing", "what should I study".
---

# /progress

1. Run `python -m tutor progress --open`.
2. In chat, summarise in a few calm, encouraging lines: the next test and days left, what's
   due for review today, the top weak spots and most common mistake types.
3. Recommend a concrete next step: `/practice review`, a `/practice` on the weakest topic,
   or `/testprep` if a test is within ~10 days.
4. If you learned something durable about how the student learns or what they
   mix up, add one line under "Notes GoatVex has learned" in `student/profile.md`.
