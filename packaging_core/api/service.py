from dataclasses import replace

from packaging_core.api.schema import CartonCandidateInput, PackagingRequest
from packaging_core.cost.calculator import (
    calc_corrugated_box_cost,
    calc_epe_solid,
    calc_eps_molded,
    calc_pallet_amortized,
    calc_stretch_film,
)
from packaging_core.logistics.freight import FreightRate, calculate_freight, select_freight_rate
from packaging_core.optimizer.carton_designer import CartonDesign, design_divider_cartons, design_foam_cartons
from packaging_core.optimizer.enumerate_box import BoxCandidate
from packaging_core.optimizer.enumerate_pallet import DEFAULT_MAX_STACK_LAYERS, enumerate_pallet_candidates
from packaging_core.optimizer.packing_solver import (
    CartonDims,
    ProductDims,
    enumerate_divider_arrangements,
    solve_divider_arrangement,
)
from packaging_core.rules.config_loader import load_yaml_config


MOLD_AMORTIZE_PER_UNIT = 3.33
PALLET_LENGTH_MM = 1100
PALLET_WIDTH_MM = 1100
PALLET_HEIGHT_MM = 120
EPS_PROJECTED_AREA_M2 = 0.26334
EPS_HEIGHT_M = 0.115
EPE_REFERENCE_VOLUME_M3 = 0.0274324
DIVIDER_CARD_PRICE_PER_BOX = 12.0
BUBBLE_BAG_DEFAULT_PRICE_PER_UNIT = 0.8
SMALL_BOARD_LONG_EDGE_MM = 300
SMALL_BOARD_HEIGHT_MM = 50
SMALL_BOARD_WEIGHT_KG = 1.0
DIVIDER_BOX_UTILIZATION_HEIGHT_RATIO = 0.9
DIVIDER_CLEARANCE_MM = 15
FOAM_CLEARANCE_MM = 60

LEGACY_FOAM_CARTON = CartonCandidateInput("LEGACY-FOAM", 665, 393, 405, "legacy", "既有大板EPS方案兜底箱", "generated")

STANDARD_CARTONS = [
    ("STD-01", 300, 250, 180, "✅", "小板、电源小板、样品箱"),
    ("STD-02", 350, 300, 200, "✅", "中小控制器板，小号ESD箱"),
    ("STD-03", 400, 300, 220, "✅", "A5-A4尺寸PCBA，多SKU小批量"),
    ("STD-04", 400, 300, 260, "✅", "A5-A4尺寸PCBA，容量加大"),
    ("STD-05", 450, 350, 230, "✅", "行业通用，家电控制板主力中小批量"),
    ("STD-06", 450, 350, 280, "✅", "家电控制板，加高版，高元件注意隔板"),
    ("STD-07", 500, 400, 240, "✅✅", "黄金优选，大批量家电/商空PCBA"),
    ("STD-08", 500, 400, 280, "✅✅", "液冷泵、变频板大批量出货"),
    ("STD-09", 500, 400, 320, "✅✅", "大容量，连接器多板慎用，注意堆码总高"),
    ("STD-10", 530, 380, 260, "⚠️", "海尔系供应商常用，大板拼板，托盘利用率一般"),
    ("STD-11", 530, 380, 300, "⚠️", "空调主控大板"),
    ("STD-12", 550, 400, 260, "⚠️", "大板多拼板，空隙略大"),
    ("STD-13", 580, 420, 300, "⚠️", "超大PCBA，优先评估托盘利用率"),
    ("STD-14", 600, 400, 250, "✅✅", "模数基准，适合超大板，纸箱单价偏高"),
    ("STD-15", 600, 400, 300, "✅✅", "纸质ESD箱上限，偏重建议改用中空周转箱"),
]


def _standard_cartons() -> list[CartonCandidateInput]:
    return [CartonCandidateInput(cid, l, w, h, mod, use, "standard") for cid, l, w, h, mod, use in STANDARD_CARTONS]


def _parse_pallet_size(pallet_size: str) -> tuple[float, float]:
    parts = pallet_size.lower().replace("×", "x").split("x")
    if len(parts) != 2:
        return PALLET_LENGTH_MM, PALLET_WIDTH_MM
    return float(parts[0]), float(parts[1])


AUTO_PALLET_OPTIONS = ("1100x1100", "1200x1000", "1219x1016")


def _pallet_options(pallet_size: str) -> list[tuple[str, float, float]]:
    """托盘候选：auto 时枚举常用托盘，否则仅用户指定尺寸。"""
    if pallet_size == "auto":
        return [(label, *_parse_pallet_size(label)) for label in AUTO_PALLET_OPTIONS]
    return [(pallet_size, *_parse_pallet_size(pallet_size))]


def _design_units_seed(request: PackagingRequest) -> list[int]:
    """设计箱的装箱数量候选：人工指定优先，其次按限重最大值，再次用户候选列表。"""
    if request.constraints.override_units_per_box is not None:
        return [request.constraints.override_units_per_box]
    if request.constraints.auto_units_per_box:
        weight_limit = int(request.constraints.max_box_weight_kg // request.product.weight_kg)
        load_limit = int(request.constraints.carton.max_load_kg // request.product.weight_kg)
        return [min(weight_limit, load_limit)]
    return request.constraints.units_per_box_candidates


def _design_carton_candidates(request: PackagingRequest, product, is_divider_mode: bool, packing_config: dict) -> tuple[list[CartonCandidateInput], dict[str, CartonDesign]]:
    """按产品有效尺寸自动设计箱型候选，返回 (候选列表, carton_id→设计记录)。"""
    if not request.constraints.auto_design_carton:
        return [], {}
    carton_config = packing_config["carton"]
    product_dims = ProductDims(product.length_mm, product.width_mm, product.height_mm)
    candidates: list[CartonCandidateInput] = []
    designs: dict[str, CartonDesign] = {}

    def _register(design: CartonDesign) -> None:
        carton_id = f"AUTO-{len(candidates) + 1:02d}"
        candidates.append(
            CartonCandidateInput(
                carton_id,
                design.outer_mm["l"],
                design.outer_mm["w"],
                design.outer_mm["h"],
                "auto",
                "按产品实物尺寸自动设计",
                "generated",
            )
        )
        designs[carton_id] = design

    if is_divider_mode:
        divider_config = packing_config["divider"]
        for units in _design_units_seed(request):
            for design in design_divider_cartons(
                product_dims,
                units,
                clearance_mm=divider_config["clearance_mm"],
                card_thickness_mm=divider_config["card_thickness_mm"],
                wall_thickness_mm=carton_config["wall_thickness_mm"],
                end_margin_mm=carton_config["end_margin_mm"],
                max_outer_height_mm=carton_config["max_outer_height_mm"],
            )[:3]:
                _register(design)
    else:
        foam_config = packing_config["foam"]
        weight_layers = 1
        if request.product.weight_kg > 0:
            weight_layers = max(1, int(request.constraints.max_box_weight_kg // request.product.weight_kg))
        if request.constraints.override_units_per_box is not None:
            weight_layers = max(weight_layers, request.constraints.override_units_per_box)
        for design in design_foam_cartons(
            product_dims,
            foam_thickness_mm=foam_config["thickness_mm"],
            fit_clearance_mm=foam_config["fit_clearance_mm"],
            wall_thickness_mm=carton_config["wall_thickness_mm"],
            max_layers=weight_layers,
            max_outer_height_mm=request.logistics.max_pallet_height_mm - 140,
        ):
            _register(design)
    return candidates, designs


def _freight_rate_from_config(freight_config: dict) -> FreightRate:
    rate = freight_config["default_rate"]
    return FreightRate(
        first_weight_kg=rate["first_weight_kg"],
        first_price=rate["first_price"],
        start_weight_kg=rate["start_weight_kg"],
        minimum_charge=rate["minimum_charge"],
        segment_thresholds=rate["segment_thresholds"],
        segment_prices=rate["segment_prices"],
        volume_divisor=rate.get("volume_divisor", freight_config["volume_divisor"]),
    )


def _effective_product(request: PackagingRequest):
    allowance = request.constraints.dimension_allowance
    return replace(
        request.product,
        length_mm=request.product.length_mm + allowance.length_mm,
        width_mm=request.product.width_mm + allowance.width_mm,
        height_mm=request.product.height_mm + allowance.height_mm,
    )


def _effective_dimensions(request: PackagingRequest) -> dict:
    allowance = request.constraints.dimension_allowance
    used = _effective_product(request)
    return {
        "base": {"l": request.product.length_mm, "w": request.product.width_mm, "h": request.product.height_mm},
        "allowance": {"l": allowance.length_mm, "w": allowance.width_mm, "h": allowance.height_mm},
        "used": {"l": used.length_mm, "w": used.width_mm, "h": used.height_mm},
    }


def _packaging_decision(request: PackagingRequest, box_height_mm: float, product=None) -> dict:
    product = product or request.product
    long_edge_mm = max(product.length_mm, product.width_mm)
    short_edge_mm = min(product.length_mm, product.width_mm)
    foam_reasons = []
    divider_reasons = []

    if long_edge_mm > SMALL_BOARD_LONG_EDGE_MM or short_edge_mm > SMALL_BOARD_LONG_EDGE_MM:
        foam_reasons.append(f"板面尺寸 {int(product.length_mm)}×{int(product.width_mm)}mm 超出小板刀卡经验边界")
    else:
        divider_reasons.append("板面尺寸处于小板刀卡常用范围")
    if product.height_mm > SMALL_BOARD_HEIGHT_MM:
        height_label = "有效高度" if product.height_mm != request.product.height_mm else "元器件高度"
        foam_reasons.append(f"{height_label} {product.height_mm:g}mm 大于 {SMALL_BOARD_HEIGHT_MM}mm，刀卡仅隔离平面，局部支撑不足")
    else:
        divider_reasons.append("元器件高度适合刀卡隔格限位")
    if product.weight_kg > SMALL_BOARD_WEIGHT_KG:
        foam_reasons.append(f"单板重量 {product.weight_kg:g}kg 大于 {SMALL_BOARD_WEIGHT_KG:g}kg，多件刀卡装箱承重和跌落风险偏高")
    else:
        divider_reasons.append("单板重量适合多件刀卡装箱")
    if long_edge_mm > SMALL_BOARD_LONG_EDGE_MM and long_edge_mm > box_height_mm * DIVIDER_BOX_UTILIZATION_HEIGHT_RATIO:
        foam_reasons.append(f"板长 {long_edge_mm:g}mm 接近或超过箱高 {box_height_mm:g}mm×{DIVIDER_BOX_UTILIZATION_HEIGHT_RATIO:g}，刀卡竖插容积利用率不合理")
    else:
        divider_reasons.append("板长与箱高匹配，刀卡竖插空间利用率可接受")

    requested = request.constraints.packaging_mode
    recommended = "foam" if foam_reasons else "divider"
    selected = recommended if requested == "auto" or requested != recommended else requested
    corrected = requested != "auto" and requested != recommended
    reasons = foam_reasons if recommended == "foam" else divider_reasons
    return {
        "requested_mode": requested,
        "recommended_mode": recommended,
        "selected_mode": selected,
        "corrected": corrected,
        "reasons": reasons,
    }


def _carton_area_m2(carton: CartonCandidateInput, waste_factor: float) -> float:
    return 2 * (carton.length_mm + carton.width_mm) * (carton.width_mm + carton.height_mm) * waste_factor / 1_000_000


def _build_cost_range(cost: dict, recommended: dict) -> dict:
    total = recommended["total_cost_per_unit"]
    packaging = cost["packaging_material_per_unit"]
    mold = cost["mold_amortize_per_unit"]
    pallet = cost["pallet_accessory_per_unit"]
    freight = cost["freight_per_unit"]

    def scenario(factor: float) -> dict:
        ranged_packaging = round(packaging * factor, 2)
        ranged_pallet = round(pallet * factor, 2)
        ranged_total = round(ranged_packaging + mold + ranged_pallet + freight, 2)
        return {
            "packaging_material_per_unit": ranged_packaging,
            "mold_amortize_per_unit": mold,
            "pallet_accessory_per_unit": ranged_pallet,
            "freight_per_unit": freight,
            "total_cost_per_unit": ranged_total,
        }

    return {
        "low": scenario(0.85),
        "typical": {
            "packaging_material_per_unit": packaging,
            "mold_amortize_per_unit": mold,
            "pallet_accessory_per_unit": pallet,
            "freight_per_unit": freight,
            "total_cost_per_unit": total,
        },
        "high": scenario(1.25),
        "basis": "按当前包材与辅料行情估算：低位按0.85系数、常用按当前报价、高位按1.25系数；运费按当前线路与折扣保持不变。",
    }


def _build_validation_assessment(request: PackagingRequest, carton_load_ok: bool, is_divider_mode: bool) -> tuple[dict, list[dict]]:
    recommendations = [
        {"category": "transport_test", "item": "跌落测试", "reason": "报价方案仍为系统估算，量产前需验证运输冲击风险。"},
        {"category": "transport_test", "item": "随机振动测试", "reason": "PCBA 焊点、端子和高大器件需确认长途运输振动可靠性。"},
        {"category": "stacking_test", "item": "堆码测试", "reason": "需确认纸箱承重、托盘层数和仓储堆叠安全系数。"},
    ]
    if request.product.esd_sensitive:
        recommendations.append({"category": "esd", "item": "ESD 防护确认", "reason": "ESD 敏感产品需确认防静电袋、屏蔽袋或导电缓冲材料。"})
    if not carton_load_ok:
        recommendations.append({"category": "strength", "item": "纸箱强度复核", "reason": "当前纸箱承重低于堆码安全校验需求。"})
    if not is_divider_mode and request.business.allow_mold:
        recommendations.append({"category": "tooling", "item": "EPS 模具评审", "reason": "成型缓冲涉及模具投入，需确认模具费、摊销数量和试模计划。"})
    return {
        "level": "V0",
        "label": "V0 仅系统估算，未完成人工工程确认",
        "production_ready": False,
        "next_level": "V1 包装工程师经验确认",
    }, recommendations


def _carton_tare_weight_kg(carton: CartonCandidateInput, waste_factor: float, areal_weight_kg_per_m2: float) -> float:
    """空箱自重 = 纸箱展开面积 × 面密度。"""
    return _carton_area_m2(carton, waste_factor) * areal_weight_kg_per_m2


def _product_dims(product) -> ProductDims:
    return ProductDims(product.length_mm, product.width_mm, product.height_mm)


def _divider_capacity(product, carton: CartonCandidateInput, clearance_mm: float, card_thickness_mm: float) -> int:
    arrangements = enumerate_divider_arrangements(
        _product_dims(product), CartonDims(carton.length_mm, carton.width_mm, carton.height_mm),
        clearance_mm, card_thickness_mm,
    )
    return max((arrangement.capacity for arrangement in arrangements), default=0)


def _divider_layout(product, carton: CartonCandidateInput, units_per_box: int, clearance_mm: float = DIVIDER_CLEARANCE_MM, card_thickness_mm: float = 3) -> dict | None:
    arrangement = solve_divider_arrangement(
        _product_dims(product), CartonDims(carton.length_mm, carton.width_mm, carton.height_mm),
        units_per_box, clearance_mm, card_thickness_mm,
    )
    if arrangement is None:
        return None
    return {
        "type": "divider_grid",
        "orientation": arrangement.orientation,
        "axis_map": arrangement.axis_map,
        "cols": arrangement.cols,
        "rows": arrangement.rows,
        "layers": arrangement.layers,
        "capacity": arrangement.capacity,
        "slot": arrangement.slot_mm,
        "product_footprint_mm": arrangement.product_footprint_mm,
        "clearance_mm": arrangement.clearance_mm,
        "display_units": units_per_box,
        "placed_items": [
            {
                "index": item.index,
                "x_mm": round(item.x_mm, 1),
                "y_mm": round(item.y_mm, 1),
                "z_mm": round(item.z_mm, 1),
                "dx_mm": round(item.dx_mm, 1),
                "dy_mm": round(item.dy_mm, 1),
                "dz_mm": round(item.dz_mm, 1),
            }
            for item in arrangement.items
        ],
        "divider_cards": [
            {
                "axis": card.axis,
                "position_mm": round(card.position_mm, 1),
                "span_a_mm": round(card.span_a_mm, 1),
                "span_b_mm": round(card.span_b_mm, 1),
                "thickness_mm": card.thickness_mm,
            }
            for card in arrangement.divider_cards
        ],
    }


def _foam_layout(product, carton: CartonCandidateInput, units_per_box: int) -> dict | None:
    if carton.carton_id == LEGACY_FOAM_CARTON.carton_id and units_per_box <= 6:
        # 边界校验：产品任一方向超出兜底箱即不可行，禁止产生物理装不下的布局
        if (
            product.length_mm > carton.length_mm
            or product.width_mm > carton.width_mm
            or product.height_mm > carton.height_mm
        ):
            return None
        return {
            "type": "foam_cavity",
            "cols": 1,
            "rows": 1,
            "layers": 6,
            "capacity": 6,
            "cavity": {"l": product.length_mm, "w": product.width_mm, "h": product.height_mm},
            "buffer_thickness_mm": 30,
            "display_units": units_per_box,
        }
    cols = int((carton.length_mm - FOAM_CLEARANCE_MM) // (product.length_mm + FOAM_CLEARANCE_MM / 2))
    rows = int((carton.width_mm - FOAM_CLEARANCE_MM) // (product.width_mm + FOAM_CLEARANCE_MM / 2))
    layers = int((carton.height_mm - FOAM_CLEARANCE_MM) // (product.height_mm + FOAM_CLEARANCE_MM / 3))
    capacity = max(cols, 0) * max(rows, 0) * max(layers, 0)
    if units_per_box > capacity or capacity <= 0:
        return None
    return {
        "type": "foam_cavity",
        "cols": cols,
        "rows": rows,
        "layers": layers,
        "capacity": capacity,
        "cavity": {"l": product.length_mm, "w": product.width_mm, "h": product.height_mm},
        "buffer_thickness_mm": FOAM_CLEARANCE_MM / 2,
        "display_units": units_per_box,
    }


def _layout_from_design(design: CartonDesign, units_per_box: int) -> dict:
    """设计箱布局直接采用设计器排布，容器口径为外箱尺寸。"""
    arrangement = design.arrangement
    if arrangement is None:
        # EPE/EPS 成型缓冲设计箱：每层一个全包络成型腔，层数与容量来自设计器
        return {
            "type": "foam_cavity",
            "cols": 1,
            "rows": 1,
            "layers": design.layers,
            "capacity": design.units,
            "cavity": dict(design.liner["cavity_mm"]),
            "buffer_thickness_mm": design.liner["foam_thickness_mm"],
            "display_units": units_per_box,
        }
    return {
        "type": "divider_grid",
        "orientation": arrangement.orientation,
        "axis_map": arrangement.axis_map,
        "cols": arrangement.cols,
        "rows": arrangement.rows,
        "layers": arrangement.layers,
        "capacity": arrangement.capacity,
        "slot": arrangement.slot_mm,
        "product_footprint_mm": arrangement.product_footprint_mm,
        "clearance_mm": arrangement.clearance_mm,
        "display_units": units_per_box,
        "placed_items": [
            {
                "index": item.index,
                "x_mm": round(item.x_mm, 1),
                "y_mm": round(item.y_mm, 1),
                "z_mm": round(item.z_mm, 1),
                "dx_mm": round(item.dx_mm, 1),
                "dy_mm": round(item.dy_mm, 1),
                "dz_mm": round(item.dz_mm, 1),
            }
            for item in arrangement.items
        ],
        "divider_cards": [
            {
                "axis": card.axis,
                "position_mm": round(card.position_mm, 1),
                "span_a_mm": round(card.span_a_mm, 1),
                "span_b_mm": round(card.span_b_mm, 1),
                "thickness_mm": card.thickness_mm,
            }
            for card in arrangement.divider_cards
        ],
    }


def _candidate_units(request: PackagingRequest, layout_capacity: int) -> list[int]:
    if request.constraints.override_units_per_box is not None:
        return [request.constraints.override_units_per_box]
    if request.constraints.auto_units_per_box:
        return [min(layout_capacity, int(request.constraints.max_box_weight_kg // request.product.weight_kg), int(request.constraints.carton.max_load_kg // request.product.weight_kg))]
    return request.constraints.units_per_box_candidates


def _structure_dimension_risks(request: PackagingRequest) -> list[dict]:
    feature_labels = [
        (request.product.has_heat_sink, "铝散热器"),
        (request.product.has_sheet_metal, "结构钣金"),
        (request.product.has_wire_harness, "线束/附件同箱"),
        (request.product.has_tall_fragile_components, "高大/易损器件"),
    ]
    if not any(enabled for enabled, _ in feature_labels):
        return []
    allowance = request.constraints.dimension_allowance
    if allowance.length_mm or allowance.width_mm or allowance.height_mm:
        return []
    labels = "、".join(label for enabled, label in feature_labels if enabled)
    return [{
        "level": "info",
        "type": "structure_feature_requires_dimension_check",
        "message": f"已勾选{labels}，但未录入外扩尺寸；本次仍按基础长宽高计算，仅作为结构风险提示。",
    }]


def _stacking_pattern(pallet, carton: CartonCandidateInput, pallet_length_mm: float, pallet_width_mm: float) -> str:
    if pallet.layers < 3 or pallet.boxes_per_layer <= 1:
        return "straight"
    # 旋转90互锁是相对偶数层实际朝向再转90°，因此奇数层沿托盘长/宽的箱边要对调
    if pallet.orientation == "B":
        rotated_along_l, rotated_along_w = carton.length_mm, carton.width_mm
    else:
        rotated_along_l, rotated_along_w = carton.width_mm, carton.length_mm
    rotated_cols = int(pallet_length_mm // rotated_along_l)
    rotated_rows = int(pallet_width_mm // rotated_along_w)
    if rotated_cols * rotated_rows >= pallet.boxes_per_layer:
        return "rotate_90_interlock"
    return "offset_interlock"


def _layer_box_positions(cols, rows, along_l, along_w, pallet_l, pallet_w, offset_x=0.0, offset_z=0.0) -> list[tuple[float, float]]:
    gap_x = max((pallet_l - cols * along_l) / (cols + 1), 0)
    gap_z = max((pallet_w - rows * along_w) / (rows + 1), 0)
    span_x = (cols - 1) * (along_l + gap_x) + along_l
    span_z = (rows - 1) * (along_w + gap_z) + along_w
    # 偏移量必须与实际排布跨度同一口径，保证错缝后任何箱子仍在托盘内
    max_offset_x = max((pallet_l - span_x) / 2, 0)
    max_offset_z = max((pallet_w - span_z) / 2, 0)
    offset_x = min(abs(offset_x), max_offset_x) * (1 if offset_x >= 0 else -1)
    offset_z = min(abs(offset_z), max_offset_z) * (1 if offset_z >= 0 else -1)
    positions = []
    for row in range(rows):
        for col in range(cols):
            x = -span_x / 2 + along_l / 2 + col * (along_l + gap_x) + offset_x
            z = -span_z / 2 + along_w / 2 + row * (along_w + gap_z) + offset_z
            positions.append((x, z))
    return positions


def _pallet_placed_boxes(pallet, carton: CartonCandidateInput, pallet_length_mm: float, pallet_width_mm: float, pallet_height_mm: float, pattern: str) -> list[dict]:
    """生成每层每只箱的中心坐标与旋转角，所有坐标保证不超出托盘边界。"""
    base_rotated = pallet.orientation == "B"
    along_base = (carton.width_mm, carton.length_mm) if base_rotated else (carton.length_mm, carton.width_mm)
    along_rotated = (carton.length_mm, carton.width_mm) if base_rotated else (carton.width_mm, carton.length_mm)
    rotated_cols = int(pallet_length_mm // along_rotated[0])
    rotated_rows = int(pallet_width_mm // along_rotated[1])

    placed: list[dict] = []
    index = 0
    for layer in range(pallet.layers):
        if pattern == "rotate_90_interlock" and layer % 2 == 1:
            cols, rows, along_l, along_w, rotation = rotated_cols, rotated_rows, along_rotated[0], along_rotated[1], 0 if base_rotated else 90
            positions = _layer_box_positions(cols, rows, along_l, along_w, pallet_length_mm, pallet_width_mm)[:pallet.boxes_per_layer]
        else:
            along_l, along_w = along_base
            offset_x = offset_z = 0.0
            if pattern == "offset_interlock" and layer % 2 == 1:
                span_x = (pallet.cols - 1) * along_l + along_l
                span_z = (pallet.rows - 1) * along_w + along_w
                max_offset_x = max((pallet_length_mm - span_x) / 2, 0)
                max_offset_z = max((pallet_width_mm - span_z) / 2, 0)
                offset_x = min(along_l * 0.18, max_offset_x)
                offset_z = min(along_w * 0.18, max_offset_z)
            cols, rows, rotation = pallet.cols, pallet.rows, 90 if base_rotated else 0
            positions = _layer_box_positions(cols, rows, along_l, along_w, pallet_length_mm, pallet_width_mm, offset_x, offset_z)[:pallet.boxes_per_layer]

        y_mm = pallet_height_mm + layer * carton.height_mm + carton.height_mm / 2
        for x_mm, z_mm in positions:
            placed.append({
                "index": index,
                "layer": layer,
                "x_mm": round(x_mm, 1),
                "y_mm": round(y_mm, 1),
                "z_mm": round(z_mm, 1),
                "rotation_y_deg": rotation,
            })
            index += 1
    return placed


def estimate_packaging(request: PackagingRequest) -> dict:
    eps_config = load_yaml_config("coeff/eps_molded.yaml")
    epe_config = load_yaml_config("coeff/epe_solid.yaml")
    corrugated_config = load_yaml_config("coeff/corrugated.yaml")
    pallet_config = load_yaml_config("coeff/pallet.yaml")
    freight_config = load_yaml_config("coeff/freight.yaml")
    kuayue_config = load_yaml_config("coeff/kuayue_vip.yaml")
    freight_config["rates"] = kuayue_config.get("rates", {})
    assembly_config = load_yaml_config("templates/assembly.yaml")
    cost_overrides = request.constraints.cost_overrides
    product_for_packaging = _effective_product(request)
    effective_dimensions = _effective_dimensions(request)

    eps_base_fee = cost_overrides.eps_base_fee if cost_overrides.eps_base_fee is not None else eps_config["base_fee"]
    eps_vol_fee = cost_overrides.eps_vol_fee if cost_overrides.eps_vol_fee is not None else eps_config["vol_fee"]
    epe_unit_price = cost_overrides.epe_unit_price_per_m3 if cost_overrides.epe_unit_price_per_m3 is not None else epe_config["unit_price_per_m3"]
    pallet_purchase_price = cost_overrides.pallet_purchase_price if cost_overrides.pallet_purchase_price is not None else pallet_config["wood_pallet"]["purchase_price"]
    pallet_reuse_count = cost_overrides.pallet_reuse_count if cost_overrides.pallet_reuse_count is not None else pallet_config["wood_pallet"]["reuse_count"]
    stretch_film_unit_price = cost_overrides.stretch_film_unit_price_per_kg if cost_overrides.stretch_film_unit_price_per_kg is not None else pallet_config["stretch_film"]["unit_price_per_kg"]
    stretch_film_kg_per_pallet = cost_overrides.stretch_film_kg_per_pallet if cost_overrides.stretch_film_kg_per_pallet is not None else pallet_config["stretch_film"]["kg_per_pallet"]
    packing_band_price = cost_overrides.packing_band_price_per_pallet if cost_overrides.packing_band_price_per_pallet is not None else pallet_config["packing_band"]["price_per_pallet"]
    bag_price_per_unit = cost_overrides.anti_static_bag_price_per_unit
    corner_price_per_pallet = cost_overrides.corner_protector_price_per_pallet if request.constraints.accessories.corner_protector else None
    edge_price_per_pallet = cost_overrides.edge_protector_price_per_pallet if request.constraints.accessories.edge_protector else None

    eps_left_price = round(calc_eps_molded(EPS_PROJECTED_AREA_M2, EPS_HEIGHT_M, eps_base_fee, eps_vol_fee), 2)
    eps_right_price = round(calc_eps_molded(EPS_PROJECTED_AREA_M2, EPS_HEIGHT_M, eps_base_fee, eps_vol_fee), 2)
    epe_reference_price = round(calc_epe_solid(EPE_REFERENCE_VOLUME_M3, epe_unit_price), 2)
    pallet_price = calc_pallet_amortized(pallet_purchase_price, pallet_reuse_count)
    stretch_film_price = calc_stretch_film(stretch_film_unit_price, stretch_film_kg_per_pallet) if request.constraints.accessories.stretch_film else 0
    pallet_accessory_per_pallet = pallet_price + stretch_film_price + (packing_band_price if request.constraints.accessories.packing_band else 0) + (corner_price_per_pallet or 0) + (edge_price_per_pallet or 0)
    if cost_overrides.mold_tooling_cost is not None and cost_overrides.mold_amortize_qty is not None:
        mold_amortize_input = round(cost_overrides.mold_tooling_cost / cost_overrides.mold_amortize_qty, 2)
        mold_formula = f"{cost_overrides.mold_tooling_cost:g} ÷ {cost_overrides.mold_amortize_qty:g} = {mold_amortize_input:.2f} 元/台"
        mold_input_source = "tooling_cost_and_quantity"
    elif cost_overrides.mold_amortize_per_unit is not None:
        mold_amortize_input = cost_overrides.mold_amortize_per_unit
        mold_formula = f"直接输入 {mold_amortize_input:g} 元/台"
        mold_input_source = "manual_per_unit"
    else:
        mold_amortize_input = MOLD_AMORTIZE_PER_UNIT
        mold_formula = f"系统默认 {MOLD_AMORTIZE_PER_UNIT:g} 元/台"
        mold_input_source = "default_per_unit"

    pallet_size = request.logistics.pallet_size or assembly_config["logistics"]["pallet_size"]
    pallet_options = _pallet_options(pallet_size)
    pallet_height_mm = request.logistics.pallet_height_mm or PALLET_HEIGHT_MM
    packing_config = load_yaml_config("coeff/packing.yaml")
    divider_clearance_mm = packing_config["divider"]["clearance_mm"]
    divider_card_thickness_mm = packing_config["divider"]["card_thickness_mm"]
    user_cartons = request.constraints.carton_candidates
    base_cartons = [*user_cartons, LEGACY_FOAM_CARTON] if user_cartons else [*_standard_cartons(), LEGACY_FOAM_CARTON]
    packaging_decision = _packaging_decision(request, LEGACY_FOAM_CARTON.height_mm, product_for_packaging)
    is_divider_mode = packaging_decision["selected_mode"] == "divider"
    mold_applied = (not is_divider_mode) and request.business.allow_mold
    mold_amortize_per_unit = mold_amortize_input if mold_applied else 0
    if is_divider_mode:
        mold_reason = "当前采用刀卡隔档包装，不涉及 EPS 成型模具，未计入模具摊销。"
    elif not request.business.allow_mold:
        mold_reason = "当前业务未允许开模，未计入模具摊销。"
    elif mold_input_source == "tooling_cost_and_quantity":
        mold_reason = "当前采用 EPS 成型缓冲，按前端输入的模具总费用和摊销数量自动计算。"
    elif mold_input_source == "manual_per_unit":
        mold_reason = "当前采用 EPS 成型缓冲，按前端人工输入的每台模具摊销计入。"
    else:
        mold_reason = "当前采用 EPS 成型缓冲，按系统默认每台模具摊销计入。"
    designed_cartons, design_records = _design_carton_candidates(request, product_for_packaging, is_divider_mode, packing_config)
    carton_candidates = [*designed_cartons, *base_cartons]
    freight_rate = select_freight_rate(freight_config, request.logistics.logistics_product, request.logistics.destination)

    candidates = []
    for pallet_label, pallet_length_mm, pallet_width_mm in pallet_options:
        for carton in carton_candidates:
            design = design_records.get(carton.carton_id)
            if design is not None:
                # 设计箱容量以设计器排布为准，不再按通用布局公式探测
                probe_capacity = design.units
            elif is_divider_mode:
                probe_capacity = _divider_capacity(product_for_packaging, carton, divider_clearance_mm, divider_card_thickness_mm)
                if probe_capacity <= 0:
                    continue
            else:
                probe_layout = _foam_layout(product_for_packaging, carton, 1)
                if not probe_layout:
                    continue
                probe_capacity = probe_layout["capacity"]
            units_seed = _candidate_units(request, probe_capacity)
            if design is not None:
                units_seed = [units for units in units_seed if units == design.units]
            for units_per_box in units_seed:
                if units_per_box <= 0:
                    continue
                if design is not None:
                    layout = _layout_from_design(design, units_per_box)
                else:
                    layout = _divider_layout(product_for_packaging, carton, units_per_box, divider_clearance_mm, divider_card_thickness_mm) if is_divider_mode else _foam_layout(product_for_packaging, carton, units_per_box)
                if not layout:
                    continue
                tare_kg = _carton_tare_weight_kg(carton, corrugated_config["waste_factor"], packing_config["carton"].get("areal_weight_kg_per_m2", 0))
                gross_weight_kg = round(units_per_box * request.product.weight_kg + tare_kg, 4)
                if gross_weight_kg > request.constraints.max_box_weight_kg or gross_weight_kg > request.constraints.carton.max_load_kg:
                    continue
                box = BoxCandidate(units_per_box=units_per_box, gross_weight_kg=gross_weight_kg, layout=layout)
                pallet_candidates = enumerate_pallet_candidates(
                    box,
                    carton.length_mm,
                    carton.width_mm,
                    carton.height_mm,
                    pallet_length_mm,
                    pallet_width_mm,
                    pallet_height_mm,
                    request.logistics.max_pallet_height_mm,
                )
                for pallet in pallet_candidates:
                    pallet_gross_weight_kg = pallet.boxes_per_pallet * box.gross_weight_kg
                    if pallet_gross_weight_kg > request.logistics.max_pallet_weight_kg:
                        continue
                    box_area_m2 = _carton_area_m2(carton, corrugated_config["waste_factor"])
                    box_unit_price = cost_overrides.corrugated_box_price if cost_overrides.corrugated_box_price is not None else round(calc_corrugated_box_cost(box_area_m2, cost_overrides.corrugated_material_yuan_per_m2 if cost_overrides.corrugated_material_yuan_per_m2 is not None else corrugated_config["material_yuan_per_m2"], corrugated_config["factory_factor"], corrugated_config["fixed_processing_yuan"]), 2)
                    pallet_accessory_per_unit = pallet_accessory_per_pallet / pallet.units_per_pallet
                    box_cost_per_unit = box_unit_price / box.units_per_box
                    inner_pack_cost_per_unit = DIVIDER_CARD_PRICE_PER_BOX / box.units_per_box + (bag_price_per_unit or BUBBLE_BAG_DEFAULT_PRICE_PER_UNIT) if is_divider_mode else eps_left_price + eps_right_price + (bag_price_per_unit or 0)
                    packaging_material_per_unit = round(inner_pack_cost_per_unit + box_cost_per_unit, 2)
                    freight = calculate_freight(
                        freight_rate,
                        actual_weight_kg=pallet_gross_weight_kg,
                        volume_cm3=(pallet_length_mm * pallet_width_mm * pallet.total_height_mm) / 1000,
                        shipment_qty=pallet.units_per_pallet,
                    )
                    original_freight_total = freight["freight_total"]
                    discounted_freight_total = round(original_freight_total * request.logistics.freight_discount, 2)
                    freight = {
                        **freight,
                        "original_freight_total": original_freight_total,
                        "discount": request.logistics.freight_discount,
                        "freight_total": discounted_freight_total,
                        "freight_per_unit": discounted_freight_total / pallet.units_per_pallet,
                    }
                    freight_per_unit = round(freight["freight_per_unit"], 2)
                    carton_product_volume_util = (product_for_packaging.length_mm * product_for_packaging.width_mm * product_for_packaging.height_mm * units_per_box) / (carton.length_mm * carton.width_mm * carton.height_mm)
                    if layout["type"] == "divider_grid":
                        length_util = min(layout["cols"] * layout["slot"]["l"] / carton.length_mm, 1)
                        width_util = min(layout["rows"] * layout["slot"]["w"] / carton.width_mm, 1)
                        height_util = min(layout["layers"] * layout["slot"]["h"] / carton.height_mm, 1)
                        carton_packaging_space_util = (length_util + width_util + height_util) / 3
                    else:
                        occupied_volume = (product_for_packaging.length_mm + FOAM_CLEARANCE_MM) * (product_for_packaging.width_mm + FOAM_CLEARANCE_MM) * (product_for_packaging.height_mm + FOAM_CLEARANCE_MM) * units_per_box
                        carton_packaging_space_util = min(occupied_volume / (carton.length_mm * carton.width_mm * carton.height_mm), 1)
                    pallet_area_util = (pallet.boxes_per_layer * carton.length_mm * carton.width_mm) / (pallet_length_mm * pallet_width_mm)
                    total_cost_per_unit = round(packaging_material_per_unit + mold_amortize_per_unit + pallet_accessory_per_unit + freight_per_unit, 2)
                    candidates.append({
                        "box": box,
                        "carton": carton,
                        "pallet": pallet,
                        "pallet_size": pallet_label,
                        "pallet_length_mm": pallet_length_mm,
                        "pallet_width_mm": pallet_width_mm,
                        "box_unit_price": box_unit_price,
                        "freight": freight,
                        "freight_rate": freight_rate,
                        "pallet_accessory_per_unit": pallet_accessory_per_unit,
                        "packaging_material_per_unit": packaging_material_per_unit,
                        "total_cost_per_unit": total_cost_per_unit,
                        "utilization": {
                            "carton_product_volume": round(carton_product_volume_util, 4),
                            "carton_packaging_space": round(carton_packaging_space_util, 4),
                            "pallet_plan_area": round(pallet_area_util, 4),
                        },
                        "score": (
                            -carton_packaging_space_util * 100
                            - pallet_area_util * 12
                            + total_cost_per_unit
                            + carton.length_mm * carton.width_mm * carton.height_mm / 1_000_000
                        ),
                    })

    if not candidates:
        raise ValueError("no feasible packaging candidate")

    pallet_selection_reason = None
    if pallet_size == "auto":
        best_by_pallet: dict[str, dict] = {}
        for item in candidates:
            label = item["pallet_size"]
            current = best_by_pallet.get(label)
            key = (item["utilization"]["pallet_plan_area"], -item["total_cost_per_unit"])
            current_key = (current["utilization"]["pallet_plan_area"], -current["total_cost_per_unit"]) if current else None
            if current_key is None or key > current_key:
                best_by_pallet[label] = item
        ranked = sorted(best_by_pallet.items(), key=lambda kv: (-kv[1]["utilization"]["pallet_plan_area"], kv[1]["total_cost_per_unit"]))
        best = ranked[0][1]
        comparison = "；".join(f"{label} 平面利用率 {item['utilization']['pallet_plan_area']:.3f}" for label, item in ranked)
        pallet_selection_reason = f"自动选型 {best['pallet_size']}：候选托盘中平面利用率最高（{comparison}）"
    else:
        best = sorted(candidates, key=lambda item: item["score"])[0]
    pallet_length_mm = best["pallet_length_mm"]
    pallet_width_mm = best["pallet_width_mm"]
    box = best["box"]
    carton = best["carton"]
    pallet = best["pallet"]
    box_gross_weight_kg = round(box.gross_weight_kg, 2)
    carton_required_load_kg = round(box_gross_weight_kg * max(pallet.layers - 1, 0) * request.constraints.carton.stack_safety_factor, 2)
    carton_load_ok = carton_required_load_kg <= request.constraints.carton.max_load_kg
    theoretical_layers = int((request.logistics.max_pallet_height_mm - pallet_height_mm) // carton.height_mm)
    layer_limit_reason = "按通用托盘堆叠规范，默认不超过 7 层" if theoretical_layers > DEFAULT_MAX_STACK_LAYERS else "未触发层数封顶"
    stacking_pattern = _stacking_pattern(pallet, carton, pallet_length_mm, pallet_width_mm)
    placed_boxes = _pallet_placed_boxes(pallet, carton, pallet_length_mm, pallet_width_mm, pallet_height_mm, stacking_pattern)
    cost_summary = {"packaging_material_per_unit": best["packaging_material_per_unit"], "mold_amortize_per_unit": mold_amortize_per_unit, "pallet_accessory_per_unit": round(best["pallet_accessory_per_unit"], 2), "freight_per_unit": round(best["freight"]["freight_per_unit"], 2)}
    recommended_summary = {"scheme_id": "DIVIDER_CARTON_PALLET" if is_divider_mode else "EPS_PALLET_N2", "summary": "刀卡隔档包装 + 防静电气泡袋 + 5层加厚纸箱 + 木托盘整托" if is_divider_mode else "EPS成型缓冲 + 防静电袋 + 5层加厚纸箱 + 木托盘整托", "units_per_box": box.units_per_box, "boxes_per_pallet": pallet.boxes_per_pallet, "units_per_pallet": pallet.units_per_pallet, "total_cost_per_unit": best["total_cost_per_unit"], "confidence": "B"}
    validation_level, validation_recommendations = _build_validation_assessment(request, carton_load_ok, is_divider_mode)

    if is_divider_mode:
        inner_bom = [
            {"item": "刀卡隔板", "spec": f"{box.layout['cols']}列×{box.layout['layers']}层，单格约{box.layout['slot']['l']}×{box.layout['slot']['w']}×{box.layout['slot']['h']}mm", "qty": round(1 / box.units_per_box, 4), "unit_price": DIVIDER_CARD_PRICE_PER_BOX, "cost_per_unit": round(DIVIDER_CARD_PRICE_PER_BOX / box.units_per_box, 2), "confidence": "C", "formula": "按单箱刀卡隔板摊销"},
            {"item": "防静电气泡袋", "spec": "ESD bubble bag", "qty": 1, "unit_price": bag_price_per_unit or BUBBLE_BAG_DEFAULT_PRICE_PER_UNIT, "cost_per_unit": bag_price_per_unit or BUBBLE_BAG_DEFAULT_PRICE_PER_UNIT, "confidence": "D", "formula": "小板刀卡方案默认每台1个防静电气泡袋；可用人工防静电袋单价覆盖"},
        ]
    else:
        inner_bom = [
            {"item": "EPS左缓冲", "spec": "660×399×115", "qty": 1, "unit_price": eps_left_price, "cost_per_unit": eps_left_price, "confidence": eps_config["confidence"], "formula": eps_config["formula"]},
            {"item": "EPS右缓冲", "spec": "660×399×115", "qty": 1, "unit_price": eps_right_price, "cost_per_unit": eps_right_price, "confidence": eps_config["confidence"], "formula": eps_config["formula"]},
            {"item": "EPE参考项", "spec": "reference volume", "qty": 1, "unit_price": epe_reference_price, "cost_per_unit": epe_reference_price, "confidence": epe_config["confidence"], "formula": epe_config["formula"]},
        ]

    packing_carton_config = packing_config["carton"]
    selected_design = design_records.get(carton.carton_id)
    packaging_design = {
        "enabled": request.constraints.auto_design_carton,
        "designed": selected_design is not None,
        "design_basis": {
            "product_mm": {"l": product_for_packaging.length_mm, "w": product_for_packaging.width_mm, "h": product_for_packaging.height_mm},
            "units_per_box": box.units_per_box,
            "wall_thickness_mm": packing_carton_config["wall_thickness_mm"],
            "end_margin_mm": packing_carton_config["end_margin_mm"],
            "clearance_mm": divider_clearance_mm if is_divider_mode else packing_config["foam"]["fit_clearance_mm"],
        },
        "inner_mm": dict(selected_design.inner_mm) if selected_design else None,
        "outer_mm": dict(selected_design.outer_mm) if selected_design else None,
        "liner": dict(selected_design.liner) if selected_design else None,
        "pallet_selection_reason": pallet_selection_reason,
    }

    result = {
        "recommended": recommended_summary,
        "cost": cost_summary,
        "cost_range": _build_cost_range(cost_summary, recommended_summary),
        "validation_level": validation_level,
        "validation_recommendations": validation_recommendations,
        "mold_amortization": {"applied": mold_applied, "cost_per_unit": mold_amortize_per_unit, "input_per_unit": mold_amortize_input, "tooling_cost": cost_overrides.mold_tooling_cost, "amortize_qty": cost_overrides.mold_amortize_qty, "input_source": mold_input_source, "basis": "EPS 成型缓冲" if not is_divider_mode else "刀卡隔档", "formula": mold_formula if mold_applied else "未使用成型模具，模具摊销/台 = 0", "reason": mold_reason},
        "freight": {**best["freight"], "freight_per_unit": round(best["freight"]["freight_per_unit"], 2), "route_note": "当前跨越费率表按物流产品和目的地匹配，始发地作为报价路线记录。"},
        "freight_rate": {"source": best["freight_rate"].source, "origin": request.logistics.origin, "logistics_product": best["freight_rate"].logistics_product, "destination": best["freight_rate"].destination, "first_weight_kg": best["freight_rate"].first_weight_kg, "first_price": best["freight_rate"].first_price, "start_weight_kg": best["freight_rate"].start_weight_kg, "minimum_charge": best["freight_rate"].minimum_charge, "segment_thresholds": best["freight_rate"].segment_thresholds, "segment_prices": best["freight_rate"].segment_prices, "volume_divisor": best["freight_rate"].volume_divisor},
        "cost_overrides_applied": cost_overrides.applied_fields(),
        "packaging_decision": packaging_decision,
        "effective_dimensions": effective_dimensions,
        "carton_selection": {"carton_id": carton.carton_id, "source": carton.source, "modularity": carton.modularity, "typical_use": carton.typical_use, "inner_size": {"l": carton.length_mm, "w": carton.width_mm, "h": carton.height_mm}, "outer_size": {"l": carton.length_mm + 2 * packing_config["carton"]["wall_thickness_mm"], "w": carton.width_mm + 2 * packing_config["carton"]["wall_thickness_mm"], "h": carton.height_mm + 2 * packing_config["carton"]["wall_thickness_mm"]}, "wall_thickness_mm": packing_config["carton"]["wall_thickness_mm"]},
        "utilization": best["utilization"],
        "packaging_design": packaging_design,
        "bom": [*inner_bom, {"item": "5层加厚纸箱", "spec": f"{int(carton.length_mm)}×{int(carton.width_mm)}×{int(carton.height_mm)}", "qty": round(1 / box.units_per_box, 4), "unit_price": best["box_unit_price"], "cost_per_unit": round(best["box_unit_price"] / box.units_per_box, 2), "confidence": "A"}, {"item": "木托盘摊销", "spec": best["pallet_size"], "qty": round(1 / pallet.units_per_pallet, 4), "unit_price": round(pallet_price, 2), "cost_per_unit": round(pallet_price / pallet.units_per_pallet, 2), "confidence": pallet_config["confidence"]}, {"item": "缠绕膜摊销", "spec": "stretch film", "qty": round(1 / pallet.units_per_pallet, 4), "unit_price": round(stretch_film_price, 2), "cost_per_unit": round(stretch_film_price / pallet.units_per_pallet, 2), "confidence": pallet_config["confidence"]}, {"item": "打包带摊销", "spec": "packing band", "qty": round(1 / pallet.units_per_pallet, 4), "unit_price": round(packing_band_price, 2), "cost_per_unit": round(packing_band_price / pallet.units_per_pallet, 2), "confidence": pallet_config["confidence"]}],
        "risks": [*_structure_dimension_risks(request), {"level": "warning", "type": "low_confidence", "message": "小件 EVA/CNC 为D级价格，建议补2-3个样本后复核。"}],
        "alternatives": [{"scheme_id": "EPE_NO_MOLD", "summary": "EPE免模具方案", "total_cost_per_unit": round(epe_reference_price + best["box_unit_price"] / box.units_per_box + best["freight"]["freight_per_unit"], 2), "confidence": "C"}],
        "box_analysis": {"auto_units_per_box": box.units_per_box, "selected_units_per_box": box.units_per_box, "gross_weight_kg": box_gross_weight_kg, "carton_tare_weight_kg": round(box_gross_weight_kg - box.units_per_box * request.product.weight_kg, 4), "max_box_weight_kg": request.constraints.max_box_weight_kg, "carton_layers": request.constraints.carton.layers, "carton_flute": request.constraints.carton.flute, "carton_thickness_mm": request.constraints.carton.thickness_mm, "carton_max_load_kg": request.constraints.carton.max_load_kg, "carton_required_load_kg": carton_required_load_kg, "carton_load_ok": carton_load_ok, "partial_pallet_note": "整托码垛能力 %d 台，若本批订单量小于整托台数，不满托仍按整托/实际箱数计费" % pallet.units_per_pallet},
        "stacking": {"pallet_size": best["pallet_size"], "pallet_length_mm": pallet_length_mm, "pallet_width_mm": pallet_width_mm, "pallet_height_mm": pallet_height_mm, "max_pallet_height_mm": request.logistics.max_pallet_height_mm, "box_height_mm": carton.height_mm, "theoretical_layers": theoretical_layers, "max_stack_layers": DEFAULT_MAX_STACK_LAYERS, "actual_layers": pallet.layers, "layer_limit_reason": layer_limit_reason, "total_height_mm": pallet.total_height_mm, "stacking_pattern": stacking_pattern},
        "geometry": {"box_view": {"outer_box": {"l": carton.length_mm, "w": carton.width_mm, "h": carton.height_mm}, "product": {"l": product_for_packaging.length_mm, "w": product_for_packaging.width_mm, "h": product_for_packaging.height_mm}, "inner_layout": box.layout, "buffers": [{"name": "刀卡隔板", "position": "grid"}, {"name": "防静电气泡袋", "position": "per_unit"}] if is_divider_mode else [{"name": "EPS左缓冲", "position": "left"}, {"name": "EPS右缓冲", "position": "right"}]}, "pallet_view": {"pallet": {"l": pallet_length_mm, "w": pallet_width_mm, "h": pallet_height_mm}, "box": {"l": carton.length_mm, "w": carton.width_mm, "h": carton.height_mm}, "layout": {"boxes_per_layer": pallet.boxes_per_layer, "layers": pallet.layers, "cols": pallet.cols, "rows": pallet.rows, "orientation": pallet.orientation, "stacking_pattern": stacking_pattern, "placed_boxes": placed_boxes}, "total_height_mm": pallet.total_height_mm}},
    }
    if bag_price_per_unit is not None and not is_divider_mode:
        result["bom"].append({"item": "防静电袋", "spec": "ESD bag", "qty": 1, "unit_price": bag_price_per_unit, "cost_per_unit": bag_price_per_unit, "confidence": "D", "source": "manual"})
    if corner_price_per_pallet is not None:
        result["bom"].append({"item": "护角摊销", "spec": "corner protector", "qty": round(1 / pallet.units_per_pallet, 4), "unit_price": corner_price_per_pallet, "cost_per_unit": round(corner_price_per_pallet / pallet.units_per_pallet, 2), "confidence": "D", "source": "manual"})
    if edge_price_per_pallet is not None:
        result["bom"].append({"item": "护边摊销", "spec": "edge protector", "qty": round(1 / pallet.units_per_pallet, 4), "unit_price": edge_price_per_pallet, "cost_per_unit": round(edge_price_per_pallet / pallet.units_per_pallet, 2), "confidence": "D", "source": "manual"})
    if not request.constraints.accessories.stretch_film:
        result["bom"] = [item for item in result["bom"] if item["item"] != "缠绕膜摊销"]
    if not request.constraints.accessories.packing_band:
        result["bom"] = [item for item in result["bom"] if item["item"] != "打包带摊销"]
    if packaging_decision["corrected"]:
        result["risks"].append({"level": "warning", "type": "packaging_mode_corrected", "message": "人工选择的包装方式与PCBA包材工程经验不匹配，系统已按更稳妥方式纠偏。", "data": packaging_decision})
    if not carton_load_ok:
        result["risks"].append({"level": "warning", "type": "carton_stack_load", "message": "当前纸箱承重低于堆码安全校验需求，建议提高纸箱强度或降低堆叠层数。", "data": result["box_analysis"]})
    return result
