from dataclasses import dataclass

from packaging_core.optimizer.enumerate_box import BoxCandidate


DEFAULT_MAX_STACK_LAYERS = 7


@dataclass(frozen=True)
class PalletCandidate:
    boxes_per_layer: int
    layers: int
    boxes_per_pallet: int
    units_per_pallet: int
    total_height_mm: float
    cols: int = 0
    rows: int = 0
    orientation: str = "A"


def enumerate_pallet_candidates(
    box: BoxCandidate,
    box_length_mm: float,
    box_width_mm: float,
    box_height_mm: float,
    pallet_length_mm: float,
    pallet_width_mm: float,
    pallet_height_mm: float,
    max_height_mm: float,
    max_stack_layers: int = DEFAULT_MAX_STACK_LAYERS,
) -> list[PalletCandidate]:
    cols_a = int(pallet_length_mm // box_length_mm)
    rows_a = int(pallet_width_mm // box_width_mm)
    layout_a = cols_a * rows_a
    cols_b = int(pallet_length_mm // box_width_mm)
    rows_b = int(pallet_width_mm // box_length_mm)
    layout_b = cols_b * rows_b

    if layout_a >= layout_b:
        orientation, cols, rows = "A", cols_a, rows_a
    else:
        orientation, cols, rows = "B", cols_b, rows_b
    boxes_per_layer = max(layout_a, layout_b)

    theoretical_layers = int((max_height_mm - pallet_height_mm) // box_height_mm)
    layers = min(theoretical_layers, max_stack_layers)
    if boxes_per_layer <= 0 or layers <= 0:
        return []

    boxes_per_pallet = boxes_per_layer * layers
    return [
        PalletCandidate(
            boxes_per_layer=boxes_per_layer,
            layers=layers,
            boxes_per_pallet=boxes_per_pallet,
            units_per_pallet=boxes_per_pallet * box.units_per_box,
            total_height_mm=pallet_height_mm + layers * box_height_mm,
            cols=cols,
            rows=rows,
            orientation=orientation,
        )
    ]
