def calc_corrugated_box_cost(
    area_m2: float,
    material_yuan_per_m2: float,
    factory_factor: float = 0.65,
    fixed_processing_yuan: float = 1.5,
) -> float:
    factory_cost = area_m2 * material_yuan_per_m2 / factory_factor
    processing_floor = area_m2 * material_yuan_per_m2 + fixed_processing_yuan
    return max(factory_cost, processing_floor)


def calc_eps_molded(projected_area_m2: float, height_m: float, base_fee: float = 47.30, vol_fee: float = 318.5) -> float:
    return projected_area_m2 * (base_fee + vol_fee * height_m)


def calc_epe_solid(volume_m3: float, unit_price_per_m3: float = 316.86) -> float:
    return volume_m3 * unit_price_per_m3


def calc_pallet_amortized(pallet_price: float, reuse_count: int) -> float:
    return pallet_price / reuse_count


def calc_stretch_film(unit_price_per_kg: float, kg_per_pallet: float) -> float:
    return unit_price_per_kg * kg_per_pallet
