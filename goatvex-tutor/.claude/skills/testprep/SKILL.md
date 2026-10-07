---
name: testprep
description: Timed mock test for an upcoming MATH 1104 or MATH 1004 test (or final), built from the course plan topics covered before the test date, graded with a weak-spot report and write-ups/videos for missed questions. Use for "prepare me for test 2", "mock exam", "practice final".
---

# /testprep <course> <test>

1. `python -m tutor testprep upcoming` shows the dates. Build the test:
   `python -m tutor testprep new <MATH1104|MATH1004> <test1..test4|final> --open`.
   - Cumulative: all weeks before the test date, with recent weeks weighted double.
   - MATH 1104: no calculator, hand-doable numbers. MATH 1004 final: multiple choice
     (distractors are proven wrong by the verifier).
   - 50 minutes (180 for the final). The page shows a timer.
2. Tell the student which weeks/topics it covers (from the output) and to work on paper.
   Don't show answers or hints during the test. Do read the questions aloud in Unicode
   if they ask.
3. When they're done, collect their answers (typed, or transcribe a photo, then confirm the
   transcription), then:
   `python -m tutor testprep grade <session> "<a1>" "<a2>" … --open`
   (or `--file answers.txt`, one per line; blank = skipped).
4. Go over the report kindly: the score, then each missed question with its mistake type and
   the textbook section to review. Each missed question already has a verified write-up;
   offer its video (`python -m tutor.video.render <folder>/problem.json`, QA the frames,
   then `--final`).
5. Suggest a `/practice` plan for the weakest topics before the real test date.
