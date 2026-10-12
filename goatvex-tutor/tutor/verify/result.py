"""Check results and their aggregation."""

from __future__ import annotations

from dataclasses import dataclass

PASS = "PASS"
FAIL = "FAIL"
# Neither proven nor disproven (e.g. simplify gave up but numbers agree).
# INCONCLUSIVE blocks rendering exactly like FAIL — we only ship what is proven.
INCONCLUSIVE = "INCONCLUSIVE"


@dataclass
class CheckResult:
    step_id: str   # "s3", or "final" / "answer" for whole-solution checks
    check: str     # short name, e.g. "row op re-applied"
    status: str    # PASS | FAIL | INCONCLUSIVE
    detail: str    # readable Unicode explanation (no LaTeX)

    @property
    def ok(self) -> bool:
        return self.status == PASS


def overall(results: list[CheckResult]) -> str:
    if not results:
        return INCONCLUSIVE
    if any(r.status == FAIL for r in results):
        return FAIL
    if any(r.status == INCONCLUSIVE for r in results):
        return INCONCLUSIVE
    return PASS
