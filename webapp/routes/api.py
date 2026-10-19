from flask import Blueprint, request
from werkzeug.exceptions import NotFound

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
from packaging_core.rules.config_loader import load_yaml_config
from webapp.errors import ApiValidationError
from webapp.quote_store import get_quote, list_quotes, save_quote, save_quote_correction
from webapp.responses import ok

api_bp = Blueprint("api", __name__, url_prefix="/api")

COST_OVERRIDE_FIELDS = [field for field in CostOverridesInput.__dataclass_fields__]
COST_FIELD_META = {
    "eps_base_fee": ("EPS 基础费", "元/m²", "coeff/eps_molded.yaml", "base_fee"),
    "eps_vol_fee": ("EPS 体积费", "元/m³", "coeff/eps_molded.yaml", "vol_fee"),
    "epe_unit_price_per_m3": ("EPE 单价", "元/m³", "coeff/epe_solid.yaml", "unit_price_per_m3"),
    "corrugated_material_yuan_per_m2": ("纸箱材料单价", "元/m²", "coeff/corrugated.yaml", "material_yuan_per_m2"),
    "corrugated_box_price": ("纸箱整箱单价覆盖", "元/箱", None, None),
    "pallet_purchase_price": ("木托盘采购价", "元", "coeff/pallet.yaml", "wood_pallet.purchase_price"),
    "pallet_reuse_count": ("托盘复用次数", "次", "coeff/pallet.yaml", "wood_pallet.reuse_count"),
    "stretch_film_unit_price_per_kg": ("缠绕膜单价", "元/kg", "coeff/pallet.yaml", "stretch_film.unit_price_per_kg"),
    "stretch_film_kg_per_pallet": ("缠绕膜单托用量", "kg/托", "coeff/pallet.yaml", "stretch_film.kg_per_pallet"),
    "packing_band_price_per_pallet": ("打包带单价", "元/托", "coeff/pallet.yaml", "packing_band.price_per_pallet"),
    "mold_tooling_cost": ("EPS 模具总费用", "元", None, None),
    "mold_amortize_qty": ("EPS 模具摊销数量", "台", None, None),
    "mold_amortize_per_unit": ("EPS 模具摊销/台", "元/台", None, None),
    "anti_static_bag_price_per_unit": ("防静电袋单价", "元/台", None, None),
    "corner_protector_price_per_pallet": ("护角单价", "元/托", None, None),
    "edge_protector_price_per_pallet": ("护边单价", "元/托", None, None),
}


def _require_object(value, field: str) -> dict:
    if not isinstance(value, dict):
        raise ApiValidationError(f"{field} must be an object")
    return value


def _require_bool(value, field: str) -> bool:
    if not isinstance(value, bool):
        raise ApiValidationError(f"{field} must be a boolean")
    return value


def _optional_bool(data: dict, key: str, default: bool, field: str) -> bool:
    if key not in data or data[key] is None:
        return default
    return _require_bool(data[key], field)


def _positive_float(value, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ApiValidationError(f"{field} must be a number") from exc
    if number <= 0:
        raise ApiValidationError(f"{field} must be positive")
    return number


def _non_negative_float(value, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ApiValidationError(f"{field} must be a number") from exc
    if number < 0:
        raise ApiValidationError(f"{field} must be non-negative")
    return number


def _positive_int(value, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ApiValidationError(f"{field} must be an integer") from exc
    if number <= 0:
        raise ApiValidationError(f"{field} must be positive")
    return number


def _discount(value, field: str) -> float:
    number = _positive_float(value, field)
    if number > 1:
        raise ApiValidationError(f"{field} must be > 0 and <= 1")
    return number


def _string(value, field: str, max_length: int = 100) -> str:
    if not isinstance(value, str):
        raise ApiValidationError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ApiValidationError(f"{field} is required")
    if len(text) > max_length:
        raise ApiValidationError(f"{field} is too long")
    return text


def _list(value, field: str) -> list:
    if not isinstance(value, list):
        raise ApiValidationError(f"{field} must be an array")
    return value


def _parse_cost_overrides(constraints: dict) -> CostOverridesInput:
    overrides = constraints.get("cost_overrides", {})
    if overrides in (None, ""):
        overrides = {}
    if not isinstance(overrides, dict):
        raise ApiValidationError("cost_overrides must be an object")
    kwargs = {}
    for field in COST_OVERRIDE_FIELDS:
        if overrides.get(field) in (None, ""):
            continue
        value = _positive_float(overrides[field], f"cost_overrides.{field}")
        kwargs[field] = int(value) if field in {"pallet_reuse_count", "mold_amortize_qty"} else value
    return CostOverridesInput(**kwargs)


def _nested_get(data: dict, path: str | None):
    if not path:
        return None
    value = data
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _cost_field_catalog() -> list[dict]:
    cache: dict[str, dict] = {}
    fields = []
    for key in COST_OVERRIDE_FIELDS:
        label, unit, config_file, path = COST_FIELD_META[key]
        default = None
        if config_file:
            cache.setdefault(config_file, load_yaml_config(config_file))
            default = _nested_get(cache[config_file], path)
        elif key == "mold_amortize_per_unit":
            default = 3.33
        fields.append({
            "key": key,
            "label": label,
            "unit": unit,
            "default": default,
            "source": config_file or "前端/人工覆盖",
            "config_path": path,
        })
    return fields


def _parse_carton_candidates(constraints: dict) -> list[CartonCandidateInput]:
    result = []
    for index, item in enumerate(_list(constraints.get("carton_candidates", []), "constraints.carton_candidates"), start=1):
        item = _require_object(item, f"constraints.carton_candidates[{index}]")
        result.append(
            CartonCandidateInput(
                carton_id=str(item.get("carton_id") or f"CUSTOM-{index}"),
                length_mm=_positive_float(item.get("length_mm"), "carton_candidate.length_mm"),
                width_mm=_positive_float(item.get("width_mm"), "carton_candidate.width_mm"),
                height_mm=_positive_float(item.get("height_mm"), "carton_candidate.height_mm"),
                modularity=str(item.get("modularity", "")),
                typical_use=str(item.get("typical_use", "人工新增纸箱")),
                source=str(item.get("source", "custom")),
            )
        )
    return result


def _parse_request(payload: dict) -> PackagingRequest:
    product = _require_object(payload.get("product"), "product")
    business = _require_object(payload.get("business"), "business")
    logistics = _require_object(payload.get("logistics"), "logistics")
    constraints = _require_object(payload.get("constraints", {}), "constraints")
    carton = _require_object(constraints.get("carton", {}), "constraints.carton")
    accessories = _require_object(constraints.get("accessories", {}), "constraints.accessories")
    allowance = _require_object(constraints.get("dimension_allowance", {}), "constraints.dimension_allowance")

    return PackagingRequest(
        product=ProductInput(
            name=_string(product.get("name"), "product.name"),
            product_class=_string(product.get("product_class"), "product.product_class"),
            length_mm=_positive_float(product.get("length_mm"), "product.length_mm"),
            width_mm=_positive_float(product.get("width_mm"), "product.width_mm"),
            height_mm=_positive_float(product.get("height_mm"), "product.height_mm"),
            weight_kg=_positive_float(product.get("weight_kg"), "product.weight_kg"),
            fragility=_string(product.get("fragility"), "product.fragility"),
            esd_sensitive=_require_bool(product.get("esd_sensitive"), "product.esd_sensitive"),
            has_heat_sink=_optional_bool(product, "has_heat_sink", False, "product.has_heat_sink"),
            has_sheet_metal=_optional_bool(product, "has_sheet_metal", False, "product.has_sheet_metal"),
            has_wire_harness=_optional_bool(product, "has_wire_harness", False, "product.has_wire_harness"),
            has_tall_fragile_components=_optional_bool(product, "has_tall_fragile_components", False, "product.has_tall_fragile_components"),
        ),
        business=BusinessInput(
            annual_qty=_positive_int(business.get("annual_qty"), "business.annual_qty"),
            design_frozen=_require_bool(business.get("design_frozen"), "business.design_frozen"),
            allow_mold=_require_bool(business.get("allow_mold"), "business.allow_mold"),
        ),
        logistics=LogisticsInput(
            ship_mode=_string(logistics.get("ship_mode"), "logistics.ship_mode"),
            destination=_string(logistics.get("destination"), "logistics.destination"),
            logistics_product=_string(logistics.get("logistics_product"), "logistics.logistics_product"),
            pallet_size=_string(logistics.get("pallet_size"), "logistics.pallet_size"),
            max_pallet_height_mm=_positive_float(logistics.get("max_pallet_height_mm"), "logistics.max_pallet_height_mm"),
            max_pallet_weight_kg=_positive_float(logistics.get("max_pallet_weight_kg"), "logistics.max_pallet_weight_kg"),
            origin=_string(logistics.get("origin", "青岛市"), "logistics.origin"),
            freight_discount=_discount(logistics.get("freight_discount", 1.0), "logistics.freight_discount"),
            pallet_material=str(logistics.get("pallet_material", "wood")),
            pallet_reusable=_optional_bool(logistics, "pallet_reusable", False, "logistics.pallet_reusable"),
            pallet_height_mm=_positive_float(logistics.get("pallet_height_mm", 120.0), "logistics.pallet_height_mm"),
            supported_logistics_products=_list(logistics.get("supported_logistics_products", ["特惠普运", "次日达"]), "logistics.supported_logistics_products"),
            available_destinations=_list(logistics.get("available_destinations", []), "logistics.available_destinations"),
        ),
        constraints=ConstraintsInput(
            units_per_box_candidates=[_positive_int(n, "constraints.units_per_box_candidates") for n in _list(constraints.get("units_per_box_candidates", [1, 2, 4, 6]), "constraints.units_per_box_candidates")],
            max_box_weight_kg=_positive_float(constraints.get("max_box_weight_kg", 25.0), "constraints.max_box_weight_kg"),
            auto_units_per_box=_optional_bool(constraints, "auto_units_per_box", True, "constraints.auto_units_per_box"),
            auto_design_carton=_optional_bool(constraints, "auto_design_carton", True, "constraints.auto_design_carton"),
            override_units_per_box=(
                _positive_int(constraints["override_units_per_box"], "constraints.override_units_per_box")
                if constraints.get("override_units_per_box") is not None
                else None
            ),
            packaging_mode=str(constraints.get("packaging_mode", "auto")),
            carton=CartonInput(
                layers=_positive_int(carton.get("layers", 5), "constraints.carton.layers"),
                flute=str(carton.get("flute", "BC")),
                thickness_mm=_positive_float(carton.get("thickness_mm", 7.0), "constraints.carton.thickness_mm"),
                max_load_kg=_positive_float(carton.get("max_load_kg", 35.0), "constraints.carton.max_load_kg"),
                stack_safety_factor=_positive_float(carton.get("stack_safety_factor", 1.5), "constraints.carton.stack_safety_factor"),
            ),
            carton_candidates=_parse_carton_candidates(constraints),
            dimension_allowance=DimensionAllowanceInput(
                length_mm=_non_negative_float(allowance.get("length_mm", 0) or 0, "constraints.dimension_allowance.length_mm"),
                width_mm=_non_negative_float(allowance.get("width_mm", 0) or 0, "constraints.dimension_allowance.width_mm"),
                height_mm=_non_negative_float(allowance.get("height_mm", 0) or 0, "constraints.dimension_allowance.height_mm"),
            ),
            accessories=AccessoryOptionsInput(
                stretch_film=_optional_bool(accessories, "stretch_film", True, "constraints.accessories.stretch_film"),
                packing_band=_optional_bool(accessories, "packing_band", True, "constraints.accessories.packing_band"),
                corner_protector=_optional_bool(accessories, "corner_protector", True, "constraints.accessories.corner_protector"),
                edge_protector=_optional_bool(accessories, "edge_protector", True, "constraints.accessories.edge_protector"),
            ),
            cost_overrides=_parse_cost_overrides(constraints),
        ),
    )


@api_bp.get("/health")
def health():
    return ok({"status": "ok"})


@api_bp.get("/cost-overrides/fields")
def cost_override_fields():
    return ok({"fields": _cost_field_catalog()})


@api_bp.get("/quote-history")
def quote_history():
    query = request.args.get("q", "").strip()
    try:
        limit = int(request.args.get("limit", 50))
    except (TypeError, ValueError) as exc:
        raise ApiValidationError("limit must be an integer") from exc
    if limit <= 0 or limit > 200:
        raise ApiValidationError("limit must be between 1 and 200")
    return ok({"records": list_quotes(limit=limit, query=query)})


@api_bp.get("/quote-history/<int:quote_id>")
def quote_history_detail(quote_id: int):
    record = get_quote(quote_id)
    if record is None:
        raise NotFound("quote history record not found")
    return ok(record)


@api_bp.post("/quote-history/<int:quote_id>/correction")
def quote_history_correction(quote_id: int):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiValidationError("request body must be a JSON object")
    actuals = {
        "actual_carton_purchase_price": (
            _non_negative_float(payload["actual_carton_purchase_price"], "actual_carton_purchase_price")
            if payload.get("actual_carton_purchase_price") not in (None, "")
            else None
        ),
        "actual_packaging_cost_per_unit": _non_negative_float(payload.get("actual_packaging_cost_per_unit"), "actual_packaging_cost_per_unit"),
        "actual_freight_per_unit": _non_negative_float(payload.get("actual_freight_per_unit"), "actual_freight_per_unit"),
        "variance_reason": _string(payload.get("variance_reason"), "variance_reason", max_length=300),
    }
    correction = save_quote_correction(quote_id, actuals)
    if correction is None:
        raise NotFound("quote history record not found")
    return ok({"correction": correction})


@api_bp.post("/estimate")
def estimate():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiValidationError("request body must be a JSON object")
    try:
        result = estimate_packaging(_parse_request(payload))
        result["quote_record_id"] = save_quote(payload, result)
    except (KeyError, TypeError, ValueError) as exc:
        raise ApiValidationError(str(exc)) from exc
    return ok(result)
