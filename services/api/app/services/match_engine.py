class MatchEngine:
    async def score(
        self,
        candidate_skills: list[str],
        required_skills: list[str],
    ) -> float:
        if not required_skills:
            return 0.0

        matched = set(candidate_skills).intersection(required_skills)
        return len(matched) / len(required_skills)
