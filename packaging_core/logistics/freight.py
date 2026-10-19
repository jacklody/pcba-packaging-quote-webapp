from dataclasses import dataclass


@dataclass
class FreightRate:
    first_weight_kg: float
    first_price: float
    start_weight_kg: float
    minimum_charge: float
    segment_thresholds: list[float]
    segment_prices: list[float]
    volume_divisor: float = 6000
    source: str = "default"
    logistics_product: str = ""
    destination: str = ""


def _rate_from_dict(rate: dict, volume_divisor: float, source: str, logistics_product: str, destination: str) -> FreightRate:
    return FreightRate(
        first_weight_kg=rate["first_weight_kg"],
        first_price=rate["first_price"],
        start_weight_kg=rate["start_weight_kg"],
        minimum_charge=rate["minimum_charge"],
        segment_thresholds=rate["segment_thresholds"],
        segment_prices=rate["segment_prices"],
        volume_divisor=rate.get("volume_divisor", volume_divisor),
        source=source,
        logistics_product=logistics_product,
        destination=destination,
    )


def select_freight_rate(config: dict, logistics_product: str, destination: str) -> FreightRate:
    for rate in config.get("kuayue_rates", {}).get(logistics_product, []):
        if destination in rate.get("destinations", []):
            return _rate_from_dict(rate, config.get("volume_divisor", 6000), "kuayue_vip", logistics_product, destination)

    for rate in config.get("rates", {}).get(logistics_product, []):
        if destination in rate.get("destinations", []):
            return _rate_from_dict(rate, config.get("volume_divisor", 6000), "kuayue_vip", logistics_product, destination)

    return _rate_from_dict(config["default_rate"], config.get("volume_divisor", 6000), "default", logistics_product, destination)


def calculate_freight(
    rate: FreightRate,
    actual_weight_kg: float,
    volume_cm3: float,
    shipment_qty: int,
    declared_value: float = 0,
    insured: bool = False,
) -> dict:
    volume_weight_kg = volume_cm3 / rate.volume_divisor
    billable_weight_kg = max(actual_weight_kg, volume_weight_kg, rate.start_weight_kg)
    segment_price = rate.segment_prices[0]
    for threshold, price in zip(rate.segment_thresholds, rate.segment_prices):
        if billable_weight_kg >= threshold:
            segment_price = price

    freight_total = max(
        rate.first_price + (billable_weight_kg - rate.first_weight_kg) * segment_price,
        rate.minimum_charge,
    )
    freight_total = round(freight_total, 2)
    if insured:
        freight_total += max(0.004 * declared_value, 5)

    return {
        "volume_weight_kg": volume_weight_kg,
        "billable_weight_kg": billable_weight_kg,
        "segment_price": segment_price,
        "freight_total": freight_total,
        "freight_per_unit": freight_total / shipment_qty,
    }
