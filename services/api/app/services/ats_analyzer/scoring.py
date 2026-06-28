from app.services.ats_analyzer.format_checker import FormatIssue
from app.services.ats_analyzer.keyword_matcher import KeywordMatch


def compute_ats_score(
    matches: list[KeywordMatch],
    format_issues: list[FormatIssue],
) -> int:
    if not matches:
        return max(0, 100 - sum(issue.penalty for issue in format_issues))

    literal_hits = sum(1 for match in matches if match.status == "literal")
    semantic_hits = sum(1 for match in matches if match.status == "semantic")
    keyword_score = ((literal_hits * 1.0 + semantic_hits * 0.5) / len(matches)) * 100
    penalties = sum(issue.penalty for issue in format_issues)
    return round(max(0, keyword_score - penalties))
