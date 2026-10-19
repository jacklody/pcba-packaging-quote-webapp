from packaging_core.api.service import estimate_packaging


def build_packaging_backfill(product_input: dict) -> dict:
    """生成供 CBOM V8.2 消费的包装成本回填载荷（薄适配，不含包装规则）。"""
    result = estimate_packaging(product_input["request"])
    cost = result["cost"]
    return {
        "packaging_material_cost": cost["packaging_material_per_unit"],
        "packaging_mold_amortize": cost["mold_amortize_per_unit"],
        "packaging_pallet_accessory": cost["pallet_accessory_per_unit"],
        "packaging_freight": cost["freight_per_unit"],
        "packaging_total_per_unit": round(
            cost["packaging_material_per_unit"]
            + cost["mold_amortize_per_unit"]
            + cost["pallet_accessory_per_unit"]
            + cost["freight_per_unit"],
            2,
        ),
        "confidence": result["recommended"]["confidence"],
        "risk_flags": result["risks"],
    }


def merge_packaging_backfill(cbom_result: dict, backfill: dict) -> dict:
    """将包装成本载荷挂到 CBOM 结果上；若存在 total_cost_per_unit 字段则同步累加。"""
    merged = dict(cbom_result)
    merged["packaging"] = dict(backfill)
    if "total_cost_per_unit" in merged and isinstance(merged["total_cost_per_unit"], (int, float)):
        merged["total_cost_per_unit"] = round(merged["total_cost_per_unit"] + backfill["packaging_total_per_unit"], 2)
    return merged


def estimate_packaging_cost(product_input: dict) -> dict:
    result = estimate_packaging(product_input["request"])
    return {
        "packaging_material_cost": result["cost"]["packaging_material_per_unit"],
        "packaging_mold_amortize": result["cost"]["mold_amortize_per_unit"],
        "packaging_freight": result["cost"]["freight_per_unit"],
        "confidence": result["recommended"]["confidence"],
        "risk_flags": result["risks"],
    }
