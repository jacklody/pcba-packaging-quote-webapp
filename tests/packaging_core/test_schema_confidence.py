import pytest

from packaging_core.api.schema import (
    AccessoryOptionsInput,
    BusinessInput,
    CartonInput,
    ConfidenceGrade,
    ConstraintsInput,
    LogisticsInput,
    PackagingRequest,
    ProductInput,
)
from packaging_core.cost.confidence import grade_confidence


def test_packaging_request_accepts_drv26p_shape():
    request = PackagingRequest(
        product=ProductInput(
            name="DRV-26P",
            product_class="assembly",
            length_mm=620,
            width_mm=360,
            height_mm=95,
            weight_kg=9.8,
            fragility="medium",
            esd_sensitive=True,
        ),
        business=BusinessInput(annual_qty=5000, design_frozen=True, allow_mold=True),
        logistics=LogisticsInput(
            ship_mode="pallet",
            destination="深圳市",
            logistics_product="特惠普运",
            pallet_size="1100x1100",
            max_pallet_height_mm=1500,
            max_pallet_weight_kg=700,
        ),
        constraints=ConstraintsInput(units_per_box_candidates=[1, 2, 4, 6], max_box_weight_kg=25),
    )

    assert request.product.product_class == "assembly"
    assert request.logistics.ship_mode == "pallet"


def test_product_input_rejects_unsupported_product_class():
    with pytest.raises(ValueError):
        ProductInput(
            name="DRV-26P",
            product_class="whole_machine",
            length_mm=620,
            width_mm=360,
            height_mm=95,
            weight_kg=9.8,
            fragility="medium",
            esd_sensitive=True,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("length_mm", 0),
        ("length_mm", -1),
        ("width_mm", 0),
        ("width_mm", -1),
        ("height_mm", 0),
        ("height_mm", -1),
        ("weight_kg", 0),
        ("weight_kg", -1),
    ],
)
def test_product_input_rejects_non_positive_physical_values(field, value):
    product_data = {
        "name": "DRV-26P",
        "product_class": "assembly",
        "length_mm": 620,
        "width_mm": 360,
        "height_mm": 95,
        "weight_kg": 9.8,
        "fragility": "medium",
        "esd_sensitive": True,
    }
    product_data[field] = value

    with pytest.raises(ValueError):
        ProductInput(**product_data)


def test_constraints_input_default_config_version():
    assert ConstraintsInput().config_version == "2026-10-13"


def test_logistics_input_accepts_pallet_metadata_and_product_options():
    logistics = LogisticsInput(
        ship_mode="pallet",
        destination="深圳市",
        logistics_product="特惠普运",
        pallet_size="1200x1000",
        max_pallet_height_mm=1500,
        max_pallet_weight_kg=900,
        origin="青岛市",
        pallet_material="wood",
        pallet_reusable=False,
        pallet_height_mm=140,
        supported_logistics_products=["特惠普运", "次日达"],
        available_destinations=["深圳市", "上海市"],
    )

    assert logistics.origin == "青岛市"
    assert logistics.supported_logistics_products == ["特惠普运", "次日达"]
    assert logistics.available_destinations == ["深圳市", "上海市"]
    assert logistics.pallet_reusable is False


def test_accessory_and_carton_options_defaults():
    constraints = ConstraintsInput()

    assert constraints.accessories == AccessoryOptionsInput()
    assert constraints.carton == CartonInput()
    assert constraints.auto_units_per_box is True
    assert constraints.override_units_per_box is None


def test_confidence_grade_can_be_used_as_annotation():
    grade: ConfidenceGrade = "C"

    assert grade == "C"


def test_confidence_grades_match_design_rules():
    assert grade_confidence(sample_count=3, max_error_pct=2.7, has_external_cross_check=False) == "A"
    assert grade_confidence(sample_count=2, max_error_pct=0.0, has_external_cross_check=True) == "B"
    assert grade_confidence(sample_count=1, max_error_pct=None, has_external_cross_check=True) == "C"
    assert grade_confidence(sample_count=0, max_error_pct=None, has_external_cross_check=False) == "D"
