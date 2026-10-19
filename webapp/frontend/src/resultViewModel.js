function hasBomItem(result, itemName) {
  return result.bom?.some((item) => item.item === itemName);
}

const PACKAGING_MODE_LABELS = {
  auto: "自动判断",
  divider: "小板刀卡隔档包装",
  foam: "大板 EPE/EPS 成型缓冲包装",
};

const CONFIDENCE_LABELS = { A: "A 高", B: "B 中", C: "C 低", D: "D 待校准" };

function cartonSourceLabel(carton) {
  if (!carton) return "未选择";
  if (carton.source === "generated") {
    return String(carton.carton_id || "").startsWith("AUTO-") ? "系统设计箱" : "系统兜底";
  }
  return { standard: "内置标准箱", custom: "人工新增" }[carton.source] || carton.source || "未标注";
}

export function buildRecommendedKpiCards(result) {
  const recommended = result.recommended;
  if (!recommended) return [];
  const carton = result.carton_selection;
  const stacking = result.stacking;
  const palletSize = stacking?.pallet_length_mm && stacking?.pallet_width_mm
    ? `${stacking.pallet_length_mm}×${stacking.pallet_width_mm}`
    : stacking?.pallet_size;
  return [
    { label: "综合总价", value: String(recommended.total_cost_per_unit), unit: "元/台", tone: "primary" },
    { label: "装箱效率", value: String(recommended.units_per_box), unit: "台/箱" },
    { label: "整托能力", value: String(recommended.units_per_pallet), unit: "台/托" },
    { label: "选中箱型", value: carton?.carton_id || "未选择", unit: cartonSourceLabel(carton) },
    { label: "托盘规格", value: palletSize || "未标注", unit: palletSize ? "mm" : "" },
    { label: "报价置信度", value: CONFIDENCE_LABELS[recommended.confidence] || recommended.confidence || "未标注", unit: "" },
  ];
}

export function buildPackagingDecisionRows(result) {
  const decision = result.packaging_decision;
  if (!decision) return [];
  return [
    { label: "用户选择", value: PACKAGING_MODE_LABELS[decision.requested_mode] || decision.requested_mode },
    { label: "系统推荐", value: PACKAGING_MODE_LABELS[decision.recommended_mode] || decision.recommended_mode },
    { label: "实际采用", value: PACKAGING_MODE_LABELS[decision.selected_mode] || decision.selected_mode },
    { label: "是否纠偏", value: decision.corrected ? "已纠偏" : "未纠偏", status: decision.corrected ? "warning" : "ok" },
    { label: "判断原因", value: (decision.reasons || []).join("；") || "无" },
  ];
}

export function buildBoxAnalysisRows(result) {
  const box = result.box_analysis;
  if (!box) return [];
  return [
    { label: "自动可装数量", value: `${box.auto_units_per_box} 台/箱` },
    { label: "当前采用数量", value: `${box.selected_units_per_box} 台/箱` },
    { label: "单箱毛重", value: `${box.gross_weight_kg} kg` },
    ...(box.carton_tare_weight_kg != null
      ? [{ label: "其中空箱自重", value: `${box.carton_tare_weight_kg} kg` }]
      : []),
    { label: "单箱限重", value: `${box.max_box_weight_kg} kg` },
    { label: "纸箱结构", value: `${box.carton_layers}层 ${box.carton_flute}楞，约 ${box.carton_thickness_mm} mm` },
    { label: "纸箱承重上限", value: `${box.carton_max_load_kg} kg` },
    { label: "堆码所需承重", value: `${box.carton_required_load_kg} kg` },
    { label: "承重校验", value: box.carton_load_ok ? "通过" : "需复核", status: box.carton_load_ok ? "ok" : "warning" },
  ];
}

export function buildStackingRows(result) {
  const stacking = result.stacking;
  if (!stacking) return [];
  const patternLabels = {
    rotate_90_interlock: "奇偶层旋转90°互锁码放",
    offset_interlock: "错缝互锁码放",
    straight: "直上直下码放",
  };
  const pattern = patternLabels[stacking.stacking_pattern] || "直上直下码放";
  const rows = [];
  if (stacking.pallet_length_mm && stacking.pallet_width_mm) {
    rows.push({ label: "托盘规格", value: `${stacking.pallet_length_mm}×${stacking.pallet_width_mm} mm` });
  }
  rows.push(
    { label: "托盘高度", value: `${stacking.pallet_height_mm} mm` },
    { label: "托盘限高", value: `${stacking.max_pallet_height_mm} mm` },
    { label: "单箱高度", value: `${stacking.box_height_mm} mm` },
    { label: "理论可码层数", value: `${stacking.theoretical_layers} 层` },
  );
  if (stacking.max_stack_layers) {
    rows.push({ label: "最大预制层数", value: `${stacking.max_stack_layers} 层` });
  }
  rows.push(
    { label: "实际采用层数", value: `${stacking.actual_layers} 层` },
    ...(stacking.layer_limit_reason ? [{ label: "层数限制原因", value: stacking.layer_limit_reason }] : []),
    { label: "码放方式", value: pattern },
    { label: "整托总高", value: `${stacking.total_height_mm} mm` },
  );
  return rows;
}

export function buildEffectiveDimensionRows(result) {
  const dims = result.effective_dimensions;
  if (!dims) return [];
  return [
    { label: "基础尺寸", value: `${dims.base.l}×${dims.base.w}×${dims.base.h} mm` },
    { label: "结构外扩", value: `${dims.allowance.l}×${dims.allowance.w}×${dims.allowance.h} mm` },
    { label: "计算采用尺寸", value: `${dims.used.l}×${dims.used.w}×${dims.used.h} mm` },
  ];
}

export function buildCartonSelectionRows(result) {
  const carton = result.carton_selection;
  if (!carton) return [];
  return [
    { label: "选中纸箱", value: `${carton.carton_id}（${cartonSourceLabel(carton)}）` },
    { label: "内尺寸", value: `${carton.inner_size.l}×${carton.inner_size.w}×${carton.inner_size.h} mm` },
    ...(carton.outer_size ? [{ label: "外尺寸", value: `${carton.outer_size.l}×${carton.outer_size.w}×${carton.outer_size.h} mm` }] : []),
    { label: "模数友好度", value: carton.modularity || "未标注" },
    { label: "典型用途", value: carton.typical_use || "未标注" },
  ];
}

function linerSummary(liner) {
  if (liner.type === "divider_grid") {
    return `刀卡格栅：${liner.divider_card_count} 张刀卡，卡厚 ${liner.card_thickness_mm} mm，单格间隙 ${liner.clearance_mm} mm`;
  }
  if (liner.type === "foam_cavity") {
    const cavity = liner.cavity_mm;
    return `EPE/EPS 成型缓冲：缓冲厚 ${liner.foam_thickness_mm} mm，内腔 ${cavity.l}×${cavity.w}×${cavity.h} mm`;
  }
  return JSON.stringify(liner);
}

export function buildPackagingDesignRows(result) {
  const design = result.packaging_design;
  if (!design) return [];
  const rows = [{ label: "功能开关", value: design.enabled ? "已启用" : "未启用" }];
  if (!design.enabled) return rows;
  rows.push({
    label: "设计结果",
    value: design.designed ? "已生成设计箱并与标准箱同台竞争" : "未采用设计箱（标准箱胜出）",
    status: design.designed ? "ok" : undefined,
  });
  if (design.inner_mm) {
    rows.push({ label: "设计箱内尺寸", value: `${design.inner_mm.l}×${design.inner_mm.w}×${design.inner_mm.h} mm` });
  }
  if (design.outer_mm) {
    rows.push({ label: "设计箱外尺寸", value: `${design.outer_mm.l}×${design.outer_mm.w}×${design.outer_mm.h} mm` });
  }
  if (design.liner) {
    rows.push({ label: "内衬方案", value: linerSummary(design.liner) });
  }
  const basis = design.design_basis;
  if (basis) {
    rows.push({
      label: "设计依据",
      value: `按实物 ${basis.product_mm.l}×${basis.product_mm.w}×${basis.product_mm.h} mm、${basis.units_per_box} 台/箱设计（壁厚 ${basis.wall_thickness_mm} mm，端距 ${basis.end_margin_mm} mm，间隙 ${basis.clearance_mm} mm）`,
    });
  }
  if (design.pallet_selection_reason) {
    rows.push({ label: "自动托盘选型", value: design.pallet_selection_reason });
  }
  return rows;
}

export function buildUtilizationRows(result) {
  const utilization = result.utilization;
  if (!utilization) return [];
  const percent = (value) => `${Math.round(Number(value) * 1000) / 10}%`;
  return [
    { label: "单箱包装占位利用率", value: percent(utilization.carton_packaging_space) },
    { label: "托盘平面利用率", value: percent(utilization.pallet_plan_area) },
    { label: "裸板实体体积占比", value: percent(utilization.carton_product_volume) },
  ];
}

export function buildInnerLayoutSummary(boxView) {
  const layout = boxView?.inner_layout;
  if (!layout) return [];
  if (layout.type === "divider_grid") {
    return [
      `刀卡格栅：${layout.cols}列 × ${layout.rows || 1}排 × ${layout.layers}层，显示 ${layout.display_units} 台/箱`,
      `单格约 ${layout.slot.l}×${layout.slot.w}×${layout.slot.h} mm，预留间隙 ${layout.clearance_mm} mm`,
      ...(layout.product_footprint_mm
        ? [`产品沿箱 x/y/z 占长 ${layout.product_footprint_mm.l}×${layout.product_footprint_mm.w}×${layout.product_footprint_mm.h} mm`]
        : []),
      "蓝色块为 PCBA，浅黄色薄板为刀卡隔板。",
    ];
  }
  if (layout.type === "foam_cavity") {
    return [
      `EPE/EPS 成型缓冲：${layout.cols}列 × ${layout.rows}排 × ${layout.layers}层，显示 ${layout.display_units} 台/箱`,
      `内腔约 ${layout.cavity.l}×${layout.cavity.w}×${layout.cavity.h} mm，缓冲厚度约 ${layout.buffer_thickness_mm} mm`,
      "蓝色块为 PCBA，浅橙色块为左右缓冲材料。",
    ];
  }
  return [];
}

export function buildAccessorySummary(result) {
  return [
    hasBomItem(result, "缠绕膜摊销") ? "已计入：缠绕膜" : "未计入：缠绕膜",
    hasBomItem(result, "打包带摊销") ? "已计入：打包带" : "未计入：打包带",
    "护角/护边：当前作为方案选项展示，待价格配置后纳入成本",
  ];
}

export function buildCostRangeRows(result) {
  const range = result.cost_range;
  if (!range) return [];
  return [
    { label: "低位成本", value: `${range.low.total_cost_per_unit} 元/台` },
    { label: "常用成本", value: `${range.typical.total_cost_per_unit} 元/台`, status: "ok" },
    { label: "高位成本", value: `${range.high.total_cost_per_unit} 元/台`, status: "warning" },
    { label: "估算依据", value: range.basis },
  ];
}

export function buildValidationRows(result) {
  const level = result.validation_level;
  if (!level) return [];
  const recommendations = result.validation_recommendations || [];
  return [
    { label: "验证等级", value: level.label, status: level.production_ready ? "ok" : "warning" },
    { label: "量产建议", value: level.production_ready ? "可量产" : "未完成验证，不建议直接量产", status: level.production_ready ? "ok" : "warning" },
    { label: "下一等级", value: level.next_level || "未标注" },
    { label: "建议验证", value: recommendations.map((item) => `${item.item}：${item.reason}`).join("；") || "无" },
  ];
}

function yuan(value) {
  return value == null ? "-" : `${Number(value).toFixed(2)} 元/台`;
}

function percent(value) {
  return value == null ? "-" : `${(Number(value) * 100).toFixed(2)}%`;
}

export function buildCorrectionRows(record) {
  const correction = record.correction;
  if (!correction) return [];
  if (correction.status !== "已回填") return [{ label: "纠偏状态", value: correction.status || "未回填", status: "warning" }];
  return [
    { label: "纠偏状态", value: correction.status, status: "ok" },
    { label: "实际包装费", value: yuan(correction.actual_packaging_cost_per_unit) },
    { label: "实际运费", value: yuan(correction.actual_freight_per_unit) },
    { label: "实际包装+运费", value: yuan(correction.actual_packaging_freight_per_unit) },
    { label: "原估算综合总价", value: yuan(correction.estimated_total_cost_per_unit) },
    { label: "单台偏差", value: yuan(correction.variance_per_unit), status: Number(correction.variance_per_unit) > 0 ? "warning" : "ok" },
    { label: "偏差率", value: percent(correction.variance_rate), status: Math.abs(Number(correction.variance_rate)) > 0.1 ? "warning" : "ok" },
    { label: "偏差原因", value: correction.variance_reason || "未填写" },
  ];
}

export function buildFreightSourceNote(freightRate, freight) {
  if (!freightRate?.source || !freightRate.logistics_product || !freightRate.destination) return null;
  const route = freightRate.origin ? `${freightRate.origin} → ${freightRate.destination}` : freightRate.destination;
  const scope = `${freightRate.logistics_product} · ${route}，最低收费 ${freightRate.minimum_charge} 元`;
  const sourceNote = freightRate.source === "kuayue_vip"
    ? `运费来源：跨越VIP报价表（${scope}）`
    : `运费来源：默认运价，未命中跨越报价表（${scope}）`;
  if (!freight || freight.discount === undefined) return sourceNote;
  return `${sourceNote}；原始运费 ${freight.original_freight_total} 元，折扣系数 ${freight.discount}，折后运费 ${freight.freight_total} 元`;
}
