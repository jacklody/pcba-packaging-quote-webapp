import pytest

from packaging_core.optimizer.packing_solver import (
    CartonDims,
    ProductDims,
    assert_arrangement_feasible,
    solve_divider_arrangement,
)

from tests.packaging_core.golden_packing_cases import (
    BOUNDARY_PRODUCTS,
    GOLDEN_DIVIDER_CASES,
    STANDARD_CARTONS,
)


CLEARANCE = 15


@pytest.mark.parametrize("case", GOLDEN_DIVIDER_CASES, ids=[c["case_id"] for c in GOLDEN_DIVIDER_CASES])
def test_golden_divider_cases_match_real_packing(case):
    product = ProductDims(case["product"]["l"], case["product"]["w"], case["product"]["h"])
    carton = CartonDims(case["carton"]["l"], case["carton"]["w"], case["carton"]["h"])

    arrangement = solve_divider_arrangement(product, carton, units=case["expected_units"], clearance_mm=CLEARANCE)

    assert arrangement is not None, f"{case['case_id']} 无可行摆法"
    assert arrangement.capacity == case["expected_units"]
    assert (arrangement.cols, arrangement.rows, arrangement.layers) == case["expected_grid"]
    assert arrangement.orientation == case["expected_orientation"]
    assert_arrangement_feasible(arrangement, carton)


@pytest.mark.parametrize("product", BOUNDARY_PRODUCTS, ids=[p["id"] for p in BOUNDARY_PRODUCTS])
@pytest.mark.parametrize("carton", STANDARD_CARTONS, ids=[c[0] for c in STANDARD_CARTONS])
def test_every_arrangement_is_geometrically_feasible(product, carton):
    from packaging_core.optimizer.packing_solver import enumerate_divider_arrangements

    p = ProductDims(product["l"], product["w"], product["h"])
    box = CartonDims(carton[1], carton[2], carton[3])

    for arrangement in enumerate_divider_arrangements(p, box, clearance_mm=CLEARANCE):
        assert arrangement.capacity == arrangement.cols * arrangement.rows * arrangement.layers
        assert arrangement.capacity == len(arrangement.items)
        assert_arrangement_feasible(arrangement, box)
        for axis in ("x", "y", "z"):
            assert 0 <= arrangement.axis_utilization[axis] <= 1


PALLET_SIZES = [
    ("1100x1100", 1100, 1100),
    ("1200x1000", 1200, 1000),
    ("1219x1016", 1219, 1016),
]


@pytest.mark.parametrize("pallet", PALLET_SIZES, ids=[p[0] for p in PALLET_SIZES])
@pytest.mark.parametrize("carton", STANDARD_CARTONS, ids=[c[0] for c in STANDARD_CARTONS])
def test_every_pallet_box_stays_inside_pallet(carton, pallet):
    from packaging_core.api.schema import CartonCandidateInput
    from packaging_core.api.service import _pallet_placed_boxes, _stacking_pattern
    from packaging_core.optimizer.enumerate_box import BoxCandidate
    from packaging_core.optimizer.enumerate_pallet import enumerate_pallet_candidates

    pallet_id, pallet_l, pallet_w = pallet
    candidate = CartonCandidateInput(carton[0], carton[1], carton[2], carton[3], "test", "test", "standard")
    box = BoxCandidate(units_per_box=8, gross_weight_kg=1.0)
    pallets = enumerate_pallet_candidates(
        box, candidate.length_mm, candidate.width_mm, candidate.height_mm,
        pallet_l, pallet_w, 120, 1500,
    )
    for pallet_candidate in pallets:
        pattern = _stacking_pattern(pallet_candidate, candidate, pallet_l, pallet_w)
        placed_boxes = _pallet_placed_boxes(pallet_candidate, candidate, pallet_l, pallet_w, 120, pattern)
        assert len(placed_boxes) == pallet_candidate.boxes_per_layer * pallet_candidate.layers
        for placed in placed_boxes:
            footprint_l = candidate.width_mm if placed["rotation_y_deg"] else candidate.length_mm
            footprint_w = candidate.length_mm if placed["rotation_y_deg"] else candidate.width_mm
            assert placed["x_mm"] - footprint_l / 2 >= -pallet_l / 2 - 1e-6
            assert placed["x_mm"] + footprint_l / 2 <= pallet_l / 2 + 1e-6
            assert placed["z_mm"] - footprint_w / 2 >= -pallet_w / 2 - 1e-6
            assert placed["z_mm"] + footprint_w / 2 <= pallet_w / 2 + 1e-6

