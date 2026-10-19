def grade_confidence(sample_count: int, max_error_pct: float | None, has_external_cross_check: bool) -> str:
    if sample_count >= 3 and max_error_pct is not None and max_error_pct <= 5:
        return "A"
    if sample_count >= 2:
        return "B" if has_external_cross_check else "C"
    if sample_count == 1:
        return "C"
    return "D"
