def rank_candidates(candidates: list[dict]) -> list[dict]:
    return sorted(candidates, key=lambda item: item["total_cost_per_unit"])
