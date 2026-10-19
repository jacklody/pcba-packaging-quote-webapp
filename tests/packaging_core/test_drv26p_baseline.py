from packaging_core.api.schema import BusinessInput, ConstraintsInput, LogisticsInput, PackagingRequest, ProductInput
from packaging_core.api.service import estimate_packaging


def test_drv26p_baseline_estimate_packaging_integration():
    request = PackagingRequest(
        ProductInput("DRV-26P", "assembly", 620, 360, 95, 9.8, "medium", True),
        BusinessInput(5000, True, True),
        LogisticsInput("pallet", "深圳市", "特惠普运", "1100x1100", 1500, 700),
        ConstraintsInput([1, 2, 4, 6], 25),
    )

    result = estimate_packaging(request)

    assert result["recommended"]["summary"].startswith("EPS成型缓冲")
    assert result["cost"]["packaging_material_per_unit"] > 0
    assert result["cost"]["freight_per_unit"] > 0
    assert result["bom"][0]["confidence"] in {"A", "B", "C", "D"}
    assert result["geometry"]["pallet_view"]["total_height_mm"] <= 1500
