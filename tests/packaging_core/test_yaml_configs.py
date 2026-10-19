from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILES = [
    ROOT / "packaging_core/rules/rules_chain.yaml",
    ROOT / "packaging_core/rules/templates/bare_board.yaml",
    ROOT / "packaging_core/rules/templates/assembly.yaml",
    ROOT / "packaging_core/rules/coeff/corrugated.yaml",
    ROOT / "packaging_core/rules/coeff/eps_molded.yaml",
    ROOT / "packaging_core/rules/coeff/epe_solid.yaml",
    ROOT / "packaging_core/rules/coeff/pallet.yaml",
    ROOT / "packaging_core/rules/coeff/freight.yaml",
]


def load_yaml(path):
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def test_yaml_configs_are_dicts_with_expected_version():
    for path in CONFIG_FILES:
        config = load_yaml(path)

        assert isinstance(config, dict), path
        assert config["version"] == "2026-10-13"


def test_coefficients_include_design_document_values():
    eps_molded = load_yaml(ROOT / "packaging_core/rules/coeff/eps_molded.yaml")
    assert eps_molded["base_fee"] == 47.30
    assert eps_molded["vol_fee"] == 318.5
    assert eps_molded["confidence"] == "B"

    epe_solid = load_yaml(ROOT / "packaging_core/rules/coeff/epe_solid.yaml")
    assert epe_solid["unit_price_per_m3"] == 316.86
    assert epe_solid["confidence"] == "B"

    pallet = load_yaml(ROOT / "packaging_core/rules/coeff/pallet.yaml")
    assert pallet["wood_pallet"]["purchase_price"] == 80
    assert pallet["wood_pallet"]["reuse_count"] == 5
    assert pallet["wood_pallet"]["amortized_price"] == 16
    assert pallet["stretch_film"]["unit_price_per_kg"] == 9
    assert pallet["stretch_film"]["kg_per_pallet"] == 0.8
    assert pallet["stretch_film"]["price_per_pallet"] == 7.2
    assert pallet["packing_band"]["price_per_pallet"] == 1.0
    assert pallet["confidence"] == "B"

    corrugated = load_yaml(ROOT / "packaging_core/rules/coeff/corrugated.yaml")
    assert corrugated["factory_factor"] == 0.65
    assert corrugated["fixed_processing_yuan"] == 1.5
    assert corrugated["confidence"] == "A"

    freight = load_yaml(ROOT / "packaging_core/rules/coeff/freight.yaml")
    assert freight["volume_divisor"] == 6000
    assert freight["pricing_mode"] == "全量段价非累进"


def test_templates_include_design_document_values():
    assembly = load_yaml(ROOT / "packaging_core/rules/templates/assembly.yaml")
    assert assembly["logistics"]["ship_mode"] == "pallet"
    assert assembly["logistics"]["default_pallet"] is True

    bare_board = load_yaml(ROOT / "packaging_core/rules/templates/bare_board.yaml")
    assert bare_board["source"] == "包装计算模板改造"
