from collections.abc import Sequence
from typing import Protocol

from app.services.ats_analyzer.format_checker import FormatIssue


class _KeywordStatus(Protocol):
    @property
    def status(self) -> str: ...


def compute_ats_score(
    matches: Sequence[_KeywordStatus],
    format_issues: list[FormatIssue],
) -> int:
    return score_keyword_coverage(
        matches,
        sum(issue.penalty for issue in format_issues),
    )


def score_keyword_coverage(matches: Sequence[_KeywordStatus], penalty: int) -> int:
    if not matches:
        return max(0, 100 - penalty)

    literal_hits = sum(1 for match in matches if match.status == "literal")
    semantic_hits = sum(1 for match in matches if match.status == "semantic")
    keyword_score = ((literal_hits * 1.0 + semantic_hits * 0.5) / len(matches)) * 100
    return round(max(0, keyword_score - penalty))
