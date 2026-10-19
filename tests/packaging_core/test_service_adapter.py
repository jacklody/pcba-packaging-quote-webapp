import json
from pathlib import Path

import pytest
import yaml

from packaging_core.adapters.cbom_v82_adapter import estimate_packaging_cost
from packaging_core.api import service
from packaging_core.api.schema import (
    AccessoryOptionsInput,
    BusinessInput,
    CartonCandidateInput,
    CartonInput,
    ConstraintsInput,
    CostOverridesInput,
    DimensionAllowanceInput,
    LogisticsInput,
    PackagingRequest,
    ProductInput,
)
from packaging_core.api.service import estimate_packaging
from packaging_core.cost.calculator import calc_eps_molded
from packaging_core.export.json_exporter import to_json
from packaging_core.rules.config_loader import load_yaml_config


ROOT = Path(__file__).resolve().parents[2]


def make_request():
    return PackagingRequest(
        product=ProductInput("DRV-26P", "assembly", 620, 360, 95, 9.8, "medium", True),
        business=BusinessInput(5000, True, True),
        logistics=LogisticsInput("pallet", "深圳市", "特惠普运", "1100x1100", 1500, 700),
        constraints=ConstraintsInput([1, 2, 4, 6], 25),
    )


def test_estimate_packaging_returns_standard_json_sections():
    result = estimate_packaging(make_request())

    assert set(result) == {
        "recommended",
        "cost",
        "cost_range",
        "validation_level",
        "validation_recommendations",
        "bom",
        "risks",
        "alternatives",
        "geometry",
        "box_analysis",
        "stacking",
        "freight_rate",
        "freight",
        "cost_overrides_applied",
        "mold_amortization",
        "packaging_decision",
        "effective_dimensions",
        "carton_selection",
        "utilization",
        "packaging_design",
    }
    assert result["recommended"]["scheme_id"] == "EPS_PALLET_N2"
    assert result["recommended"]["summary"].startswith("EPS成型缓冲")
    assert result["recommended"]["confidence"] == "B"
    assert set(result["cost"]) == {
        "packaging_material_per_unit",
        "mold_amortize_per_unit",
        "pallet_accessory_per_unit",
        "freight_per_unit",
    }
    assert result["cost"]["packaging_material_per_unit"] > 0
    assert result["cost"]["mold_amortize_per_unit"] == 3.33
    assert result["cost"]["pallet_accessory_per_unit"] > 0
    assert result["cost"]["freight_per_unit"] > 0
    assert set(result["cost_range"]) == {"low", "typical", "high", "basis"}
    assert result["cost_range"]["low"]["total_cost_per_unit"] <= result["cost_range"]["typical"]["total_cost_per_unit"] <= result["cost_range"]["high"]["total_cost_per_unit"]
    assert result["validation_level"]["level"] == "V0"
    assert "仅系统估算" in result["validation_level"]["label"]
    assert any(item["category"] == "transport_test" for item in result["validation_recommendations"])
    assert any(item["item"] == "EPS左缓冲" for item in result["bom"])
    assert any(risk["type"] == "low_confidence" and "小件 EVA/CNC" in risk["message"] for risk in result["risks"])
    assert set(result["geometry"]) == {"box_view", "pallet_view"}


def test_estimate_packaging_uses_yaml_coefficients_for_eps_left_buffer():
    result = estimate_packaging(make_request())
    eps_config = yaml.safe_load((ROOT / "packaging_core/rules/coeff/eps_molded.yaml").read_text(encoding="utf-8"))
    left_buffer = next(item for item in result["bom"] if item["item"] == "EPS左缓冲")

    expected = calc_eps_molded(
        projected_area_m2=0.26334,
        height_m=0.115,
        base_fee=eps_config["base_fee"],
        vol_fee=eps_config["vol_fee"],
    )

    assert left_buffer["unit_price"] == round(expected, 2)


def test_estimate_packaging_raises_when_max_pallet_height_has_no_feasible_candidate():
    # 限高 250：LEGACY(箱高405)与1层设计箱(箱高149)加托盘140后均超出，无解
    request = make_request()
    request = PackagingRequest(
        request.product,
        request.business,
        LogisticsInput("pallet", "深圳市", "特惠普运", "1100x1100", 250, 700),
        request.constraints,
    )

    with pytest.raises(ValueError, match="no feasible packaging candidate"):
        estimate_packaging(request)


def test_estimate_packaging_falls_back_to_shorter_designed_carton_under_height_limit():
    # 限高 500：LEGACY(箱高405+140>500)不可行，多层设计箱(最高284)可用并胜出
    request = make_request()
    request = PackagingRequest(
        request.product,
        request.business,
        LogisticsInput("pallet", "深圳市", "特惠普运", "1100x1100", 500, 700),
        request.constraints,
    )

    result = estimate_packaging(request)

    carton = result["carton_selection"]
    assert carton["carton_id"].startswith("AUTO-")
    assert carton["inner_size"]["h"] + 140 <= 500
    assert result["stacking"]["actual_layers"] >= 1


def test_estimate_packaging_raises_when_max_pallet_weight_has_no_feasible_candidate():
    request = make_request()
    request = PackagingRequest(
        request.product,
        request.business,
        LogisticsInput("pallet", "深圳市", "特惠普运", "1100x1100", 1500, 10),
        request.constraints,
    )

    with pytest.raises(ValueError, match="no feasible packaging candidate"):
        estimate_packaging(request)


def test_estimate_packaging_omits_mold_amortize_when_mold_not_allowed():
    request = make_request()
    request = PackagingRequest(request.product, BusinessInput(5000, True, False), request.logistics, request.constraints)

    result = estimate_packaging(request)

    assert result["cost"]["mold_amortize_per_unit"] == 0


def test_estimate_packaging_uses_auto_units_per_box_and_returns_explanations():
    request = make_request()
    request = PackagingRequest(
        request.product,
        request.business,
        request.logistics,
        ConstraintsInput(
            units_per_box_candidates=[1],
            max_box_weight_kg=40,
            auto_units_per_box=True,
            carton=CartonInput(max_load_kg=120),
        ),
    )

    result = estimate_packaging(request)

    # 空箱重计入毛重后，限重40kg下只能装1台（4台≈41.6kg超载）
    assert result["recommended"]["units_per_box"] == 1
    assert result["box_analysis"]["auto_units_per_box"] == 1
    assert result["box_analysis"]["gross_weight_kg"] == 10.51
    # 理论可码 9 层，但通用托盘堆叠预制封顶为 7 层
    assert result["box_analysis"]["carton_load_ok"] is True
    assert result["stacking"]["theoretical_layers"] == 9
    assert result["stacking"]["max_stack_layers"] == 7
    assert result["stacking"]["actual_layers"] == 7
    assert result["stacking"]["actual_layers"] == result["geometry"]["pallet_view"]["layout"]["layers"]
    assert result["stacking"]["layer_limit_reason"] == "按通用托盘堆叠规范，默认不超过 7 层"


def test_estimate_packaging_gross_weight_includes_carton_tare():
    # 回归：毛重必须计入空箱自重（纸箱面积×面密度），而非仅产品重
    request = make_request()
    request = PackagingRequest(
        request.product,
        request.business,
        request.logistics,
        ConstraintsInput(units_per_box_candidates=[1], auto_units_per_box=False),
    )

    result = estimate_packaging(request)

    product_weight = request.product.weight_kg
    gross = result["box_analysis"]["gross_weight_kg"]
    assert gross > product_weight  # 含空箱重
    assert round(gross - product_weight, 4) > 0


def test_estimate_packaging_respects_accessory_switches():
    request = make_request()
    request = PackagingRequest(
        request.product,
        request.business,
        request.logistics,
        ConstraintsInput(accessories=AccessoryOptionsInput(stretch_film=False, packing_band=False)),
    )

    result = estimate_packaging(request)

    # 托盘堆叠封顶 7 层后，整托 14 台，木托盘摊销 16/14≈1.14 元/台
    assert result["cost"]["pallet_accessory_per_unit"] == 1.14
    assert not any(item["item"] == "缠绕膜摊销" for item in result["bom"])
    assert not any(item["item"] == "打包带摊销" for item in result["bom"])


def test_estimate_packaging_uses_kuayue_rate_when_product_and_destination_match():
    request = make_request()
    request = PackagingRequest(
        request.product,
        request.business,
        LogisticsInput("pallet", "深圳市", "次日达", "1100x1100", 1500, 700),
        request.constraints,
    )

    result = estimate_packaging(request)

    assert result["freight_rate"]["source"] == "kuayue_vip"
    assert result["freight_rate"]["logistics_product"] == "次日达"
    assert result["freight_rate"]["destination"] == "深圳市"
    assert result["freight_rate"]["minimum_charge"] == 171


def test_estimate_packaging_records_origin_and_applies_freight_discount():
    base = make_request()
    no_discount = PackagingRequest(
        base.product,
        base.business,
        LogisticsInput("pallet", "深圳市", "特惠普运", "1100x1100", 1500, 700, origin="青岛市", freight_discount=1.0),
        base.constraints,
    )
    discounted = PackagingRequest(
        base.product,
        base.business,
        LogisticsInput("pallet", "深圳市", "特惠普运", "1100x1100", 1500, 700, origin="上海市", freight_discount=0.85),
        base.constraints,
    )

    full_price = estimate_packaging(no_discount)
    discount_price = estimate_packaging(discounted)

    assert discount_price["freight_rate"]["origin"] == "上海市"
    assert discount_price["freight"]["discount"] == 0.85
    assert discount_price["freight"]["original_freight_total"] == full_price["freight"]["freight_total"]
    assert discount_price["freight"]["freight_total"] == round(full_price["freight"]["freight_total"] * 0.85, 2)
    assert discount_price["cost"]["freight_per_unit"] == round(discount_price["freight"]["freight_total"] / discount_price["recommended"]["units_per_pallet"], 2)


def test_estimate_packaging_applies_cost_overrides_to_material_and_mold():
    request = make_request()
    request = PackagingRequest(
        request.product,
        request.business,
        request.logistics,
        ConstraintsInput(
            units_per_box_candidates=[1, 2, 4, 6],
            max_box_weight_kg=25,
            cost_overrides=CostOverridesInput(
                eps_base_fee=50.0,
                eps_vol_fee=320.0,
                mold_amortize_per_unit=5.0,
            ),
        ),
    )

    result = estimate_packaging(request)

    expected_eps = round(0.26334 * (50.0 + 320.0 * 0.115), 2)
    left_buffer = next(item for item in result["bom"] if item["item"] == "EPS左缓冲")
    assert left_buffer["unit_price"] == expected_eps
    assert result["cost"]["mold_amortize_per_unit"] == 5.0
    assert sorted(result["cost_overrides_applied"]) == ["eps_base_fee", "eps_vol_fee", "mold_amortize_per_unit"]


def test_estimate_packaging_uses_corrugated_area_formula_by_default_and_supports_direct_override():
    result = estimate_packaging(make_request())
    # 选中箱为设计箱 AUTO-01（外 674×414×149），按面积公式计价
    box_area_m2 = 2 * (0.674 + 0.414) * (0.414 + 0.149) * 1.05
    expected_price = round(max(box_area_m2 * 14.35 / 0.65, box_area_m2 * 14.35 + 1.5), 2)
    box_item = next(item for item in result["bom"] if item["item"] == "5层加厚纸箱")
    assert box_item["unit_price"] == expected_price
    assert result["cost_overrides_applied"] == []

    request = make_request()
    request = PackagingRequest(
        request.product,
        request.business,
        request.logistics,
        ConstraintsInput(
            units_per_box_candidates=[1, 2, 4, 6],
            max_box_weight_kg=25,
            cost_overrides=CostOverridesInput(corrugated_box_price=50.0),
        ),
    )
    result = estimate_packaging(request)
    box_item = next(item for item in result["bom"] if item["item"] == "5层加厚纸箱")
    assert box_item["unit_price"] == 50.0


def test_estimate_packaging_counts_bag_corner_edge_when_priced():
    request = make_request()
    request = PackagingRequest(
        request.product,
        request.business,
        request.logistics,
        ConstraintsInput(
            units_per_box_candidates=[1, 2, 4, 6],
            max_box_weight_kg=25,
            cost_overrides=CostOverridesInput(
                anti_static_bag_price_per_unit=1.2,
                corner_protector_price_per_pallet=3.0,
                edge_protector_price_per_pallet=2.0,
            ),
        ),
    )

    result = estimate_packaging(request)

    units_per_pallet = result["recommended"]["units_per_pallet"]
    bag_item = next(item for item in result["bom"] if item["item"] == "防静电袋")
    assert bag_item["cost_per_unit"] == 1.2
    corner_item = next(item for item in result["bom"] if item["item"] == "护角摊销")
    assert corner_item["cost_per_unit"] == round(3.0 / units_per_pallet, 2)
    edge_item = next(item for item in result["bom"] if item["item"] == "护边摊销")
    assert edge_item["cost_per_unit"] == round(2.0 / units_per_pallet, 2)
    assert result["cost"]["pallet_accessory_per_unit"] == round((16 + 7.2 + 1.0 + 3.0 + 2.0) / units_per_pallet, 2)
    material_from_bom = round(
        bag_item["cost_per_unit"]
        + next(i for i in result["bom"] if i["item"] == "EPS左缓冲")["cost_per_unit"]
        + next(i for i in result["bom"] if i["item"] == "EPS右缓冲")["cost_per_unit"]
        + next(i for i in result["bom"] if i["item"] == "5层加厚纸箱")["cost_per_unit"],
        2,
    )
    assert result["cost"]["packaging_material_per_unit"] == material_from_bom


def test_auto_packaging_mode_selects_divider_for_small_board():
    request = PackagingRequest(
        ProductInput("FAN-CTRL", "pcba", 240, 180, 30, 0.4, "low", True),
        BusinessInput(5000, True, False),
        LogisticsInput("pallet", "深圳市", "特惠普运", "1100x1100", 1500, 700),
        ConstraintsInput([6, 10, 20, 30], 18, packaging_mode="auto"),
    )

    result = estimate_packaging(request)

    assert result["packaging_decision"]["requested_mode"] == "auto"
    assert result["packaging_decision"]["selected_mode"] == "divider"
    assert result["recommended"]["scheme_id"] == "DIVIDER_CARTON_PALLET"
    assert result["recommended"]["summary"].startswith("刀卡隔档包装")
    assert any(item["item"] == "刀卡隔板" for item in result["bom"])
    assert not any(item["item"].startswith("EPS") for item in result["bom"])


def test_eps_mold_amortization_can_be_calculated_from_tooling_cost_and_quantity():
    request = PackagingRequest(
        ProductInput("LARGE-PCBA", "assembly", 620, 360, 95, 9.8, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "深圳市", "特惠普运", "1100x1100", 1500, 700),
        ConstraintsInput(
            [1, 2, 4, 6],
            25,
            packaging_mode="auto",
            cost_overrides=CostOverridesInput(mold_tooling_cost=12000, mold_amortize_qty=6000),
        ),
    )

    result = estimate_packaging(request)

    assert result["packaging_decision"]["selected_mode"] == "foam"
    assert result["cost"]["mold_amortize_per_unit"] == 2
    assert result["mold_amortization"]["applied"] is True
    assert result["mold_amortization"]["tooling_cost"] == 12000
    assert result["mold_amortization"]["amortize_qty"] == 6000
    assert result["mold_amortization"]["formula"] == "12000 ÷ 6000 = 2.00 元/台"


def test_divider_packaging_does_not_charge_mold_even_when_mold_allowed():
    request = PackagingRequest(
        ProductInput("SMALL-PCBA", "pcba", 120, 60, 30, 0.1, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "上海市", "特惠普运", "1100x1100", 1500, 700),
        ConstraintsInput([12, 24, 36], 18, packaging_mode="auto"),
    )

    result = estimate_packaging(request)

    assert result["packaging_decision"]["selected_mode"] == "divider"
    assert result["cost"]["mold_amortize_per_unit"] == 0
    assert result["mold_amortization"]["applied"] is False
    assert "未计入" in result["mold_amortization"]["reason"]


def test_manual_divider_mode_is_corrected_when_board_long_edge_exceeds_box_height():
    request = PackagingRequest(
        ProductInput("DRV-26P", "assembly", 620, 360, 95, 9.8, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "深圳市", "特惠普运", "1100x1100", 1500, 700),
        ConstraintsInput([1, 2, 4, 6], 25, packaging_mode="divider"),
    )

    result = estimate_packaging(request)

    assert result["packaging_decision"]["requested_mode"] == "divider"
    assert result["packaging_decision"]["selected_mode"] == "foam"
    assert any("板长" in reason and "箱高" in reason for reason in result["packaging_decision"]["reasons"])
    assert any(risk["type"] == "packaging_mode_corrected" for risk in result["risks"])


def test_structure_flags_do_not_change_packaging_without_dimension_allowance():
    base = PackagingRequest(
        ProductInput("FILTER-PCBA", "assembly", 260, 180, 45, 0.8, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "深圳市", "特惠普运", "1100x1100", 1500, 700),
        ConstraintsInput([1, 2, 4, 6], 25, packaging_mode="auto"),
    )
    flagged = PackagingRequest(
        ProductInput(
            "FILTER-PCBA",
            "assembly",
            260,
            180,
            45,
            0.8,
            "medium",
            True,
            has_heat_sink=True,
            has_sheet_metal=True,
            has_wire_harness=True,
            has_tall_fragile_components=True,
        ),
        base.business,
        base.logistics,
        base.constraints,
    )

    base_result = estimate_packaging(base)
    flagged_result = estimate_packaging(flagged)

    assert flagged_result["packaging_decision"]["selected_mode"] == base_result["packaging_decision"]["selected_mode"]
    assert flagged_result["effective_dimensions"]["used"] == {"l": 260, "w": 180, "h": 45}
    assert flagged_result["recommended"]["total_cost_per_unit"] == base_result["recommended"]["total_cost_per_unit"]
    assert any(risk["type"] == "structure_feature_requires_dimension_check" for risk in flagged_result["risks"])


def test_dimension_allowance_changes_effective_dimensions_and_packaging_decision():
    request = PackagingRequest(
        ProductInput("FILTER-PCBA", "assembly", 260, 180, 45, 0.8, "medium", True, has_heat_sink=True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "深圳市", "特惠普运", "1100x1100", 1500, 700),
        ConstraintsInput([1, 2, 4, 6], 25, packaging_mode="auto", dimension_allowance=DimensionAllowanceInput(height_mm=50)),
    )

    result = estimate_packaging(request)

    assert result["effective_dimensions"]["base"] == {"l": 260, "w": 180, "h": 45}
    assert result["effective_dimensions"]["allowance"] == {"l": 0, "w": 0, "h": 50}
    assert result["effective_dimensions"]["used"] == {"l": 260, "w": 180, "h": 95}
    assert result["packaging_decision"]["selected_mode"] == "foam"
    assert any("有效高度" in reason for reason in result["packaging_decision"]["reasons"])


def test_standard_carton_library_optimizes_small_board_box_and_utilization():
    request = PackagingRequest(
        ProductInput("FAN-CTRL", "pcba", 120, 85, 40, 0.1, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "上海市", "特惠普运", "1219x1016", 1500, 700),
        ConstraintsInput([1, 2, 4, 6, 8, 10, 12], 25, packaging_mode="auto"),
    )

    result = estimate_packaging(request)

    assert result["carton_selection"]["source"] == "standard"
    assert result["carton_selection"]["carton_id"] in {"STD-01", "STD-02"}
    assert result["recommended"]["units_per_box"] >= 8
    assert result["geometry"]["box_view"]["inner_layout"]["type"] == "divider_grid"
    layout = result["geometry"]["pallet_view"]["layout"]
    assert layout["cols"] * result["geometry"]["pallet_view"]["box"]["l"] <= result["geometry"]["pallet_view"]["pallet"]["l"]
    assert layout["rows"] * result["geometry"]["pallet_view"]["box"]["w"] <= result["geometry"]["pallet_view"]["pallet"]["w"]
    assert layout["stacking_pattern"] == "offset_interlock"
    assert 0 < result["utilization"]["carton_product_volume"] <= 1
    assert result["utilization"]["carton_packaging_space"] > 0.75
    assert result["utilization"]["pallet_plan_area"] > 0.7


def test_divider_layout_supports_real_vertical_case_600x400x200_with_24_units():
    custom = CartonCandidateInput(
        "REAL-600-400-200",
        600,
        400,
        200,
        "✅✅",
        "真实案例：160×95×35板竖放两行，每行12块",
        source="custom",
    )
    request = PackagingRequest(
        ProductInput("REAL-PCBA", "pcba", 160, 95, 35, 0.12, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "上海市", "特惠普运", "1200x1000", 1500, 700),
        ConstraintsInput([24], 25, packaging_mode="divider", override_units_per_box=24, auto_design_carton=False, carton_candidates=[custom]),
    )

    result = estimate_packaging(request)
    layout = result["geometry"]["box_view"]["inner_layout"]

    assert result["carton_selection"]["carton_id"] == "REAL-600-400-200"
    assert result["recommended"]["units_per_box"] == 24
    assert layout["type"] == "divider_grid"
    assert layout["orientation"] == "vertical_dense_two_rows"
    assert layout["cols"] == 12
    assert layout["rows"] == 2
    assert layout["layers"] == 1
    assert layout["capacity"] == 24


def test_geometry_outputs_coordinates_that_stay_inside_carton_and_pallet():
    custom = CartonCandidateInput(
        "REAL-600-400-200",
        600,
        400,
        200,
        "✅✅",
        "真实案例",
        source="custom",
    )
    request = PackagingRequest(
        ProductInput("REAL-PCBA", "pcba", 160, 95, 35, 0.12, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "上海市", "特惠普运", "1200x1000", 1500, 700),
        ConstraintsInput([24], 25, packaging_mode="divider", override_units_per_box=24, carton_candidates=[custom]),
    )

    result = estimate_packaging(request)
    box_view = result["geometry"]["box_view"]
    pallet_view = result["geometry"]["pallet_view"]
    outer = box_view["outer_box"]
    pallet = pallet_view["pallet"]

    items = box_view["inner_layout"]["placed_items"]
    assert len(items) == 24
    for item in items:
        # 求解器坐标约定：x=箱长，y=箱宽，z=箱高
        assert item["x_mm"] - item["dx_mm"] / 2 >= 0
        assert item["x_mm"] + item["dx_mm"] / 2 <= outer["l"] + 1e-6
        assert item["y_mm"] - item["dy_mm"] / 2 >= 0
        assert item["y_mm"] + item["dy_mm"] / 2 <= outer["w"] + 1e-6
        assert item["z_mm"] - item["dz_mm"] / 2 >= 0
        assert item["z_mm"] + item["dz_mm"] / 2 <= outer["h"] + 1e-6

    placed_boxes = pallet_view["layout"]["placed_boxes"]
    expected_box_count = pallet_view["layout"]["boxes_per_layer"] * pallet_view["layout"]["layers"]
    assert len(placed_boxes) == expected_box_count
    for placed in placed_boxes:
        footprint_l = box_view["outer_box"]["w"] if placed["rotation_y_deg"] else box_view["outer_box"]["l"]
        footprint_w = box_view["outer_box"]["l"] if placed["rotation_y_deg"] else box_view["outer_box"]["w"]
        # 托盘中心坐标，合法范围为 ±托盘尺寸/2
        assert placed["x_mm"] - footprint_l / 2 >= -pallet["l"] / 2 - 1e-6
        assert placed["x_mm"] + footprint_l / 2 <= pallet["l"] / 2 + 1e-6
        assert placed["z_mm"] - footprint_w / 2 >= -pallet["w"] / 2 - 1e-6
        assert placed["z_mm"] + footprint_w / 2 <= pallet["w"] / 2 + 1e-6


def test_custom_carton_candidates_can_be_selected_when_better_than_standard():
    custom = CartonCandidateInput(
        "CUS-TIGHT-01",
        260,
        250,
        180,
        "✅",
        "小板紧凑自定义箱",
        source="custom",
    )
    request = PackagingRequest(
        ProductInput("PUMP-CTRL", "pcba", 120, 85, 40, 0.1, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "上海市", "特惠普运", "1100x1100", 1500, 700),
        ConstraintsInput([1, 2, 4], 25, packaging_mode="auto", carton_candidates=[custom]),
    )

    result = estimate_packaging(request)

    assert result["carton_selection"]["source"] == "custom"
    assert result["carton_selection"]["carton_id"] == "CUS-TIGHT-01"
    assert result["geometry"]["box_view"]["outer_box"] == {"l": 260, "w": 250, "h": 180}


def test_to_json_serializes_standard_result():
    result = estimate_packaging(make_request())

    exported = to_json(result)

    assert json.loads(exported) == result
    assert "EPS成型缓冲" in exported


def test_auto_design_carton_generates_design_box_and_packaging_design_section():
    # 非标板 285×205×42：标准箱无法贴合，自动设计箱参与选优后胜出
    request = PackagingRequest(
        ProductInput("SPECIAL-PCBA", "pcba", 285, 205, 42, 0.35, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "上海市", "特惠普运", "1200x1000", 1500, 700),
        ConstraintsInput([12], 25, packaging_mode="divider", override_units_per_box=12, auto_design_carton=True),
    )

    result = estimate_packaging(request)
    design = result["packaging_design"]

    assert design["enabled"] is True
    assert design["designed"] is True
    assert result["carton_selection"]["source"] == "generated"
    assert result["carton_selection"]["carton_id"].startswith("AUTO-")
    assert result["recommended"]["units_per_box"] == 12
    assert design["design_basis"]["product_mm"] == {"l": 285, "w": 205, "h": 42}
    assert design["design_basis"]["units_per_box"] == 12
    # 外尺寸 = 内尺寸 + 2×壁厚(5mm)
    assert design["outer_mm"]["l"] == design["inner_mm"]["l"] + 10
    assert design["outer_mm"]["w"] == design["inner_mm"]["w"] + 10
    assert design["outer_mm"]["h"] == design["inner_mm"]["h"] + 10
    assert design["liner"]["type"] == "divider_grid"
    assert result["geometry"]["pallet_view"]["box"] == design["outer_mm"]
    layout = result["geometry"]["box_view"]["inner_layout"]
    assert layout["type"] == "divider_grid"
    assert len(layout["placed_items"]) == 12


def test_design_carton_candidates_register_generated_boxes():
    request = PackagingRequest(
        ProductInput("REAL-PCBA", "pcba", 160, 95, 35, 0.12, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "上海市", "特惠普运", "1200x1000", 1500, 700),
        ConstraintsInput([24], 25, packaging_mode="divider", override_units_per_box=24),
    )
    packing_config = load_yaml_config("coeff/packing.yaml")

    candidates, records = service._design_carton_candidates(request, request.product, True, packing_config)

    assert [c.carton_id for c in candidates] == ["AUTO-01", "AUTO-02", "AUTO-03"]
    assert all(c.source == "generated" for c in candidates)
    assert sorted(records) == ["AUTO-01", "AUTO-02", "AUTO-03"]
    assert all(design.units == 24 for design in records.values())
    # 候选登记口径：CartonCandidateInput 携带设计箱外尺寸
    assert all(
        c.length_mm == records[c.carton_id].outer_mm["l"]
        and c.width_mm == records[c.carton_id].outer_mm["w"]
        and c.height_mm == records[c.carton_id].outer_mm["h"]
        for c in candidates
    )


def test_auto_design_flow_runs_for_real_case_dimensions():
    # 真实案例 160×95×35×24：设计箱与标准箱同台竞争，胜者由评分决定
    request = PackagingRequest(
        ProductInput("REAL-PCBA", "pcba", 160, 95, 35, 0.12, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "上海市", "特惠普运", "1200x1000", 1500, 700),
        ConstraintsInput([24], 25, packaging_mode="divider", override_units_per_box=24, auto_design_carton=True),
    )

    result = estimate_packaging(request)

    assert result["packaging_design"]["enabled"] is True
    assert result["packaging_design"]["design_basis"]["units_per_box"] == 24
    assert len(result["geometry"]["box_view"]["inner_layout"]["placed_items"]) == 24
    assert result["recommended"]["units_per_box"] == 24


def test_auto_design_carton_disabled_omits_packaging_design_and_keeps_standard_flow():
    request = PackagingRequest(
        ProductInput("REAL-PCBA", "pcba", 160, 95, 35, 0.12, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "上海市", "特惠普运", "1200x1000", 1500, 700),
        ConstraintsInput([24], 25, packaging_mode="divider", override_units_per_box=24, auto_design_carton=False),
    )

    result = estimate_packaging(request)
    design = result["packaging_design"]

    assert design["enabled"] is False
    assert design["designed"] is False
    assert design["inner_mm"] is None
    assert design["outer_mm"] is None
    assert result["carton_selection"]["source"] == "standard"


def test_pallet_size_auto_selects_pallet_with_highest_plan_area_and_reports_reason():
    custom = CartonCandidateInput("REAL-600-400-200", 600, 400, 200, "✅✅", "真实案例", source="custom")
    request = PackagingRequest(
        ProductInput("REAL-PCBA", "pcba", 160, 95, 35, 0.12, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "上海市", "特惠普运", "auto", 1500, 700),
        ConstraintsInput([24], 25, packaging_mode="divider", override_units_per_box=24, auto_design_carton=False, carton_candidates=[custom]),
    )

    result = estimate_packaging(request)
    design = result["packaging_design"]

    assert result["stacking"]["pallet_size"] == "1200x1000"
    assert result["stacking"]["pallet_length_mm"] == 1200
    assert result["stacking"]["pallet_width_mm"] == 1000
    assert result["geometry"]["pallet_view"]["pallet"] == {"l": 1200, "w": 1000, "h": 120}
    assert "1200x1000" in design["pallet_selection_reason"]
    assert "1100x1100" in design["pallet_selection_reason"]
    assert "1219x1016" in design["pallet_selection_reason"]


def test_pallet_size_manual_has_no_auto_selection_reason():
    request = make_request()

    result = estimate_packaging(request)

    assert result["packaging_design"]["pallet_selection_reason"] is None
    assert result["stacking"]["pallet_size"] == "1100x1100"


def test_cbom_adapter_returns_only_thin_fields():
    result = estimate_packaging_cost({"request": make_request()})

    assert sorted(result.keys()) == [
        "confidence",
        "packaging_freight",
        "packaging_material_cost",
        "packaging_mold_amortize",
        "risk_flags",
    ]
    assert result["confidence"] == "B"
    assert result["packaging_material_cost"] > 0
    assert result["packaging_mold_amortize"] == 3.33
    assert result["packaging_freight"] > 0


def test_legacy_foam_layout_rejects_product_exceeding_carton_boundary():
    # 产品高 470mm 超出 LEGACY-FOAM 外箱 405mm，布局必须判为不可行
    product = ProductInput("TALL-BOARD", "pcba", 550, 380, 470, 3.0, "medium", True)
    assert service._foam_layout(product, service.LEGACY_FOAM_CARTON, 1) is None
    assert service._foam_layout(product, service.LEGACY_FOAM_CARTON, 6) is None


def test_tall_product_550x380x470_never_selects_carton_smaller_than_product():
    request = PackagingRequest(
        ProductInput("TALL-BOARD", "pcba", 550, 380, 470, 3.0, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "深圳市", "特惠普运", "auto", 1500, 700),
        ConstraintsInput([1, 2, 4, 6], 25),
    )

    result = estimate_packaging(request)

    carton = result["carton_selection"]
    assert carton["inner_size"]["h"] >= 470
    assert carton["inner_size"]["l"] >= 550
    assert carton["inner_size"]["w"] >= 380
    assert result["utilization"]["carton_product_volume"] <= 1
    assert result["packaging_design"]["designed"] is True
