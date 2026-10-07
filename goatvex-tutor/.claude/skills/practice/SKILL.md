---
name: practice
description: Practice problems with hidden verified answers, chosen by weak spots and spaced repetition, graded when the student answers, progress updated. Use for "give me practice", "quiz me", or a review session.
---

# /practice [type | topic] [n]

1. Pick the session:
   - Specific topic: `python -m tutor practice new --type <type[:variant]> --n 3`
     (`python -m tutor types` lists types and variants, e.g. `indefinite_integral:parts`).
   - General: `python -m tutor practice new --course MATH1104 --n 3`. It weights topics taught so
     far by weak spots and due reviews.
   - Spaced repetition: `python -m tutor practice review` (topics due today).
2. Show the questions in readable Unicode, **one at a time**. Never reveal answers, and don't
   peek at or quote the session file's answer fields.
3. When the student answers: `python -m tutor practice answer <session> <k> "<their answer>"`.
   Relay the feedback. If wrong: name the likely mistake, then offer a hint ladder
   (`/hint`) or `/check` on their work, before showing the verified answer if they want it.
4. Celebrate correct answers. After the last question the score is logged in
   `student/progress.json` (Leitner boxes: right answers push a topic's next review further out).
5. For a longer set, print a practice sheet as HTML via `/testprep`-style pages if asked.
6. MATH 1104 has no calculators on tests: encourage doing every step by hand.
