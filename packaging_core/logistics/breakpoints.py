def detect_cliff(current_weight_kg: float, thresholds: list[float], tolerance_ratio: float = 0.05) -> list[float]:
    return [
        threshold
        for threshold in thresholds
        if abs(current_weight_kg - threshold) / threshold <= tolerance_ratio
    ]
