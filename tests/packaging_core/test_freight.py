import pytest

from packaging_core.logistics.breakpoints import detect_cliff
from packaging_core.logistics.freight import FreightRate, calculate_freight, select_freight_rate


@pytest.fixture
def sample_rate():
    return FreightRate(
        first_weight_kg=1,
        first_price=20,
        start_weight_kg=15,
        minimum_charge=133,
        segment_thresholds=[1, 10, 30, 50, 100, 300, 500, 1000, 2000],
        segment_prices=[10.8, 10.8, 10.8, 9.9, 9.0, 8.1, 8.1, 8.1, 8.1],
    )


def test_calculate_freight_uses_volume_weight_and_matching_segment_price(sample_rate):
    result = calculate_freight(
        sample_rate,
        actual_weight_kg=11.3,
        volume_cm3=106032,
        shipment_qty=1,
    )

    assert result["volume_weight_kg"] == pytest.approx(17.672)
    assert result["billable_weight_kg"] == pytest.approx(17.672)
    assert result["freight_total"] == pytest.approx(200.06)
    assert result["freight_per_unit"] == pytest.approx(200.06)


def test_calculate_freight_adds_minimum_insurance_fee(sample_rate):
    uninsured = calculate_freight(
        sample_rate,
        actual_weight_kg=1,
        volume_cm3=1,
        shipment_qty=1,
    )
    insured = calculate_freight(
        sample_rate,
        actual_weight_kg=1,
        volume_cm3=1,
        shipment_qty=1,
        declared_value=1000,
        insured=True,
    )

    assert insured["freight_total"] - uninsured["freight_total"] == pytest.approx(5)
    assert insured["freight_per_unit"] - uninsured["freight_per_unit"] == pytest.approx(5)


def test_detect_cliff_returns_thresholds_within_tolerance():
    assert detect_cliff(49, [1, 10, 30, 50, 100], 0.05) == [50]
    assert detect_cliff(51, [1, 10, 30, 50, 100], 0.05) == [50]


def test_detect_cliff_returns_empty_when_no_threshold_is_nearby():
    assert detect_cliff(75, [1, 10, 30, 50, 100], 0.05) == []


def test_select_freight_rate_uses_kuayue_product_and_destination():
    config = {
        "volume_divisor": 6000,
        "default_rate": {
            "first_weight_kg": 1,
            "first_price": 20,
            "start_weight_kg": 15,
            "minimum_charge": 133,
            "segment_thresholds": [1, 10, 30],
            "segment_prices": [10, 9, 8],
        },
        "kuayue_rates": {
            "次日达": [
                {
                    "origin": "青岛市",
                    "province": "广东省",
                    "destinations": ["广州市", "深圳市"],
                    "charge_mode": "分段收费",
                    "first_weight_kg": 1,
                    "first_price": 20,
                    "start_weight_kg": 15,
                    "minimum_charge": 171,
                    "segment_thresholds": [1, 10, 30, 50, 100, 300, 500, 1000, 2000],
                    "segment_prices": [10.8, 10.8, 10.8, 9.9, 9, 8.1, 8.1, 8.1, 8.1],
                }
            ]
        },
    }

    rate = select_freight_rate(config, logistics_product="次日达", destination="深圳市")

    assert rate.minimum_charge == 171
    assert rate.start_weight_kg == 15
    assert rate.segment_prices[3] == 9.9


def test_select_freight_rate_falls_back_when_destination_missing():
    config = {
        "volume_divisor": 6000,
        "default_rate": {
            "first_weight_kg": 1,
            "first_price": 20,
            "start_weight_kg": 15,
            "minimum_charge": 133,
            "segment_thresholds": [1],
            "segment_prices": [10.8],
        },
        "kuayue_rates": {"特惠普运": []},
    }

    rate = select_freight_rate(config, logistics_product="特惠普运", destination="深圳市")

    assert rate.minimum_charge == 133
    assert rate.segment_prices == [10.8]
