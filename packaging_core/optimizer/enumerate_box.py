from dataclasses import dataclass


@dataclass(frozen=True)
class BoxCandidate:
    units_per_box: int
    gross_weight_kg: float
    layout: dict | None = None


def calculate_auto_units_per_box(
    product_length_mm: float,
    product_width_mm: float,
    product_height_mm: float,
    unit_weight_kg: float,
    box_length_mm: float,
    box_width_mm: float,
    box_height_mm: float,
    max_box_weight_kg: float,
    carton_max_load_kg: float,
) -> int:
    by_height = int(box_height_mm // product_height_mm)
    by_weight = int(max_box_weight_kg // unit_weight_kg)
    by_carton_load = int(carton_max_load_kg // unit_weight_kg)
    if product_length_mm > box_length_mm or product_width_mm > box_width_mm:
        return 0
    return max(0, min(by_height, by_weight, by_carton_load))


def enumerate_box_candidates(
    units_per_box_candidates: list[int],
    unit_weight_kg: float,
    max_box_weight_kg: float,
) -> list[BoxCandidate]:
    result = []
    for units_per_box in units_per_box_candidates:
        if units_per_box <= 0:
            continue
        gross_weight_kg = units_per_box * unit_weight_kg
        if gross_weight_kg <= max_box_weight_kg:
            result.append(BoxCandidate(units_per_box=units_per_box, gross_weight_kg=gross_weight_kg))
    return result
