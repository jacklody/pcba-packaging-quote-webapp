from packaging_core.adapters.cbom_v82_adapter import build_packaging_backfill, merge_packaging_backfill
from packaging_core.api.schema import BusinessInput, ConstraintsInput, LogisticsInput, PackagingRequest, ProductInput
from packaging_core.api.service import estimate_packaging


def make_request():
    return PackagingRequest(
        ProductInput("DRV-26P", "assembly", 620, 360, 95, 9.8, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "深圳市", "特惠普运", "1100x1100", 1500, 700),
        ConstraintsInput([1, 2, 4, 6], 25),
    )


def test_backfill_contains_all_cost_items_and_consistent_total():
    backfill = build_packaging_backfill({"request": make_request()})

    assert backfill["packaging_material_cost"] > 0
    assert backfill["packaging_mold_amortize"] >= 0
    assert backfill["packaging_pallet_accessory"] > 0
    assert backfill["packaging_freight"] > 0
    total = (
        backfill["packaging_material_cost"]
        + backfill["packaging_mold_amortize"]
        + backfill["packaging_pallet_accessory"]
        + backfill["packaging_freight"]
    )
    assert abs(backfill["packaging_total_per_unit"] - total) < 0.01
    assert backfill["confidence"] in {"A", "B", "C", "D"}
    assert isinstance(backfill["risk_flags"], list)


def test_merge_attaches_packaging_and_updates_total_when_present():
    backfill = build_packaging_backfill({"request": make_request()})

    cbom_row = {"total_cost_per_unit": 100.0, "items": []}
    merged = merge_packaging_backfill(cbom_row, backfill)
    assert merged["packaging"] == backfill
    assert merged["total_cost_per_unit"] == round(100.0 + backfill["packaging_total_per_unit"], 2)
    # original row not mutated
    assert cbom_row["total_cost_per_unit"] == 100.0


def test_merge_without_total_field_only_attaches():
    backfill = build_packaging_backfill({"request": make_request()})

    merged = merge_packaging_backfill({"bom_cost": 55}, backfill)
    assert merged["packaging"] == backfill
    assert merged["bom_cost"] == 55


def test_backfill_matches_service_output():
    result = estimate_packaging(make_request())
    backfill = build_packaging_backfill({"request": make_request()})

    assert backfill["packaging_material_cost"] == result["cost"]["packaging_material_per_unit"]
    assert backfill["packaging_freight"] == result["cost"]["freight_per_unit"]
