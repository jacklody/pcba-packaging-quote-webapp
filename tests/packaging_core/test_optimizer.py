from packaging_core.optimizer.enumerate_box import calculate_auto_units_per_box, enumerate_box_candidates
from packaging_core.optimizer.enumerate_pallet import enumerate_pallet_candidates
from packaging_core.optimizer.objective import rank_candidates


def test_box_enumeration_filters_overweight_boxes():
    candidates = enumerate_box_candidates([1, 2, 4, 6], unit_weight_kg=9.8, max_box_weight_kg=25)

    assert [c.units_per_box for c in candidates] == [1, 2]


def test_auto_units_per_box_respects_volume_weight_and_carton_load():
    assert calculate_auto_units_per_box(
        product_length_mm=620,
        product_width_mm=360,
        product_height_mm=95,
        unit_weight_kg=9.8,
        box_length_mm=665,
        box_width_mm=393,
        box_height_mm=405,
        max_box_weight_kg=40,
        carton_max_load_kg=35,
    ) == 3


def test_pallet_enumeration_computes_layers_and_units():
    box = enumerate_box_candidates([2], unit_weight_kg=9.8, max_box_weight_kg=25)[0]
    pallets = enumerate_pallet_candidates(
        box,
        box_length_mm=665,
        box_width_mm=393,
        box_height_mm=405,
        pallet_length_mm=1100,
        pallet_width_mm=1100,
        pallet_height_mm=120,
        max_height_mm=1500,
    )
    best = pallets[0]

    assert best.boxes_per_layer >= 2
    assert best.layers == 3
    assert best.units_per_pallet == best.boxes_per_layer * 3 * 2
    assert best.cols * best.rows == best.boxes_per_layer
    assert best.orientation in {"A", "B"}


def test_pallet_enumeration_caps_stack_layers_at_seven_by_default():
    box = enumerate_box_candidates([1], unit_weight_kg=1.0, max_box_weight_kg=25)[0]
    pallets = enumerate_pallet_candidates(
        box,
        box_length_mm=300,
        box_width_mm=250,
        box_height_mm=150,
        pallet_length_mm=1200,
        pallet_width_mm=1000,
        pallet_height_mm=120,
        max_height_mm=1500,
    )
    best = pallets[0]

    assert best.layers == 7
    assert best.total_height_mm == 1170
    assert best.units_per_pallet == best.boxes_per_layer * 7


def test_pallet_arrangement_prefers_box_length_along_pallet_length_on_tie():
    box = enumerate_box_candidates([2], unit_weight_kg=9.8, max_box_weight_kg=25)[0]
    pallets = enumerate_pallet_candidates(
        box,
        box_length_mm=665,
        box_width_mm=393,
        box_height_mm=405,
        pallet_length_mm=1100,
        pallet_width_mm=1100,
        pallet_height_mm=120,
        max_height_mm=1500,
    )
    best = pallets[0]

    # 665×393 box on 1100×1100: layout_a = 1×2, layout_b = 2×1, tie → orientation A
    assert best.orientation == "A"
    assert (best.cols, best.rows) == (1, 2)


def test_rank_candidates_sorts_by_total_cost():
    ranked = rank_candidates([
        {"scheme_id": "A", "total_cost_per_unit": 90.0},
        {"scheme_id": "B", "total_cost_per_unit": 80.0},
    ])

    assert [item["scheme_id"] for item in ranked] == ["B", "A"]
