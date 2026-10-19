from packaging_core.cost.calculator import (
    calc_corrugated_box_cost,
    calc_eps_molded,
    calc_epe_solid,
    calc_pallet_amortized,
    calc_stretch_film,
)


def test_eps_molded_reproduces_drv26p_samples():
    assert round(calc_eps_molded(projected_area_m2=0.26334, height_m=0.115), 2) == 22.10
    assert round(calc_eps_molded(projected_area_m2=0.26334, height_m=0.146), 2) == 24.70


def test_epe_solid_uses_verified_unit_price():
    assert round(calc_epe_solid(volume_m3=0.0274324), 2) == 8.69


def test_pallet_and_film_match_template_parameters():
    assert calc_pallet_amortized(pallet_price=80, reuse_count=5) == 16.0
    assert calc_stretch_film(unit_price_per_kg=9, kg_per_pallet=0.8) == 7.2


def test_corrugated_applies_processing_floor():
    assert round(calc_corrugated_box_cost(area_m2=0.0101, material_yuan_per_m2=2.0), 2) == 1.52
