import pytest

from packaging_core.optimizer.carton_designer import (
    design_divider_carton,
    design_divider_cartons,
    design_foam_carton,
    design_foam_cartons,
)
from packaging_core.optimizer.packing_solver import (
    CartonDims,
    ProductDims,
    assert_arrangement_feasible,
)

from tests.packaging_core.golden_packing_cases import GOLDEN_DESIGN_CASES


@pytest.mark.parametrize("case", GOLDEN_DESIGN_CASES, ids=[c["case_id"] for c in GOLDEN_DESIGN_CASES])
def test_golden_design_cases_derive_carton_from_product(case):
    product = ProductDims(case["product"]["l"], case["product"]["w"], case["product"]["h"])

    designs = design_divider_cartons(product, case["units"])
    assert designs, f"{case['case_id']} 无可行设计"

    # 金标准摆法必须存在于设计列表中（最优摆法由批次2托盘+运费评分决定）
    grid = case.get("expected_grid")
    target = next(
        (
            d
            for d in designs
            if d.orientation == case["expected_orientation"]
            and (grid is None or (d.cols, d.rows, d.layers) == grid)
        ),
        None,
    )
    assert target is not None, f"{case['case_id']} 缺少 {case['expected_orientation']} 摆法"
    if "expected_inner" in case:
        assert target.inner_mm == case["expected_inner"]
        assert target.outer_mm == case["expected_outer"]

    # 每个设计都必须能被求解器校验：摆法在箱内几何可行
    for design in designs:
        assert_arrangement_feasible(design.arrangement, CartonDims(design.inner_mm["l"], design.inner_mm["w"], design.inner_mm["h"]))


def test_every_divider_design_is_feasible_and_within_height_limit():
    product = ProductDims(260, 180, 45)

    designs = design_divider_cartons(product, units=8)

    assert designs
    for design in designs:
        assert design.cols * design.rows * design.layers == 8
        assert design.outer_mm["h"] <= 400
        assert_arrangement_feasible(design.arrangement, CartonDims(design.inner_mm["l"], design.inner_mm["w"], design.inner_mm["h"]))


def test_designs_sorted_by_outer_volume_then_flat_preference():
    product = ProductDims(160, 95, 35)

    designs = design_divider_cartons(product, units=24)
    volumes = [d.outer_volume_mm3 for d in designs]

    assert volumes == sorted(volumes)
    best = designs[0]
    same_volume = [d for d in designs if d.outer_volume_mm3 == best.outer_volume_mm3]
    flat_first = [d for d in same_volume if d.orientation == "flat_stacked"]
    if flat_first:
        assert best.orientation == "flat_stacked"


def test_foam_carton_design_wraps_product_with_liner_thickness():
    product = ProductDims(380, 300, 60)

    design = design_foam_carton(product, foam_thickness_mm=20, fit_clearance_mm=2, wall_thickness_mm=5)

    assert design.liner["type"] == "foam_cavity"
    assert design.liner["cavity_mm"] == {"l": 420, "w": 340, "h": 100}
    assert design.inner_mm == {"l": 424, "w": 344, "h": 104}
    assert design.outer_mm == {"l": 434, "w": 354, "h": 114}


def test_design_returns_none_when_units_unreachable_within_height_limit():
    product = ProductDims(120, 85, 40)

    # 限高50mm时任何一层都放不下40+15=55的层高
    assert design_divider_carton(product, units=12, max_outer_height_mm=50) is None


def test_design_foam_cartons_supports_multi_layer_stacking():
    product = ProductDims(620, 360, 95)

    designs = design_foam_cartons(
        product, foam_thickness_mm=20, fit_clearance_mm=2, wall_thickness_mm=5, max_layers=4, max_outer_height_mm=1360
    )

    assert [d.layers for d in designs] == [1, 2, 3, 4]
    assert all(d.units == d.layers for d in designs)
    two = designs[1]
    assert two.liner["layers"] == 2
    assert two.inner_mm == {"l": 664, "w": 404, "h": 274}
    assert two.outer_mm == {"l": 674, "w": 414, "h": 284}


def test_design_foam_cartons_respects_outer_height_limit():
    product = ProductDims(550, 380, 470)  # 层高 470+40=510

    designs = design_foam_cartons(product, max_layers=8, max_outer_height_mm=1360)

    assert [d.layers for d in designs] == [1, 2]


def test_design_foam_cartons_single_layer_matches_legacy_design():
    product = ProductDims(160, 95, 35)

    designs = design_foam_cartons(product, max_layers=3, max_outer_height_mm=1360)

    assert designs[0] == design_foam_carton(product)
