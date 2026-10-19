import assert from "node:assert/strict";
import {
  buildAccessorySummary,
  buildBoxAnalysisRows,
  buildCartonSelectionRows,
  buildCorrectionRows,
  buildCostRangeRows,
  buildEffectiveDimensionRows,
  buildFreightSourceNote,
  buildInnerLayoutSummary,
  buildPackagingDecisionRows,
  buildPackagingDesignRows,
  buildRecommendedKpiCards,
  buildStackingRows,
  buildValidationRows,
  buildUtilizationRows,
} from "./resultViewModel.js";

const result = {
  recommended: {
    units_per_box: 2,
    boxes_per_pallet: 18,
    units_per_pallet: 36,
    total_cost_per_unit: 18.66,
    confidence: "B",
  },
  box_analysis: {
    auto_units_per_box: 4,
    selected_units_per_box: 2,
    gross_weight_kg: 19.6,
    max_box_weight_kg: 25,
    carton_layers: 5,
    carton_flute: "BC",
    carton_thickness_mm: 7,
    carton_max_load_kg: 35,
    carton_required_load_kg: 29.4,
    carton_load_ok: true,
  },
  stacking: {
    pallet_size: "1200x1000",
    pallet_length_mm: 1200,
    pallet_width_mm: 1000,
    pallet_height_mm: 120,
    max_pallet_height_mm: 1500,
    box_height_mm: 405,
    theoretical_layers: 9,
    max_stack_layers: 7,
    actual_layers: 7,
    layer_limit_reason: "按通用托盘堆叠规范，默认不超过 7 层",
    stacking_pattern: "rotate_90_interlock",
    total_height_mm: 1335,
  },
  effective_dimensions: {
    base: { l: 260, w: 180, h: 45 },
    allowance: { l: 0, w: 0, h: 50 },
    used: { l: 260, w: 180, h: 95 },
  },
  carton_selection: {
    carton_id: "STD-01",
    source: "standard",
    modularity: "✅",
    typical_use: "小板、电源小板、样品箱",
    inner_size: { l: 300, w: 250, h: 180 },
  },
  utilization: { carton_product_volume: 0.12, carton_packaging_space: 0.86, pallet_plan_area: 0.62 },
  geometry: {
    box_view: {
      inner_layout: {
        type: "divider_grid",
        cols: 2,
        rows: 2,
        layers: 2,
        display_units: 4,
        slot: { l: 135, w: 100, h: 55 },
        clearance_mm: 15,
      },
    },
  },
  bom: [{ item: "木托盘摊销" }, { item: "缠绕膜摊销" }],
  cost_range: {
    low: { total_cost_per_unit: 16.2, packaging_material_per_unit: 5.1, pallet_accessory_per_unit: 1.2, freight_per_unit: 8.9 },
    typical: { total_cost_per_unit: 18.66, packaging_material_per_unit: 6.0, pallet_accessory_per_unit: 1.6, freight_per_unit: 8.9 },
    high: { total_cost_per_unit: 24.8, packaging_material_per_unit: 7.5, pallet_accessory_per_unit: 2.0, freight_per_unit: 8.9 },
    basis: "按当前包材与辅料行情估算",
  },
  validation_level: { level: "V0", label: "V0 仅系统估算，未完成人工工程确认", production_ready: false, next_level: "V1 包装工程师经验确认" },
  validation_recommendations: [
    { category: "transport_test", item: "跌落测试", reason: "验证运输冲击风险" },
    { category: "stacking_test", item: "堆码测试", reason: "验证纸箱承重" },
  ],
  packaging_decision: {
    requested_mode: "divider",
    recommended_mode: "foam",
    selected_mode: "foam",
    corrected: true,
    reasons: ["板长 620mm 接近或超过箱高 405mm×0.9，刀卡竖插容积利用率不合理"],
  },
};

assert.deepEqual(buildBoxAnalysisRows(result).map((row) => row.label), [
  "自动可装数量",
  "当前采用数量",
  "单箱毛重",
  "单箱限重",
  "纸箱结构",
  "纸箱承重上限",
  "堆码所需承重",
  "承重校验",
]);
assert.equal(buildBoxAnalysisRows(result).at(-1).value, "通过");
assert.equal(buildStackingRows(result).find((row) => row.label === "最大预制层数").value, "7 层");
assert.equal(buildStackingRows(result).find((row) => row.label === "实际采用层数").value, "7 层");
assert.equal(buildStackingRows(result).find((row) => row.label === "层数限制原因").value, "按通用托盘堆叠规范，默认不超过 7 层");
assert.equal(buildStackingRows(result).find((row) => row.label === "码放方式").value, "奇偶层旋转90°互锁码放");
assert.equal(buildCartonSelectionRows(result).find((row) => row.label === "选中纸箱").value, "STD-01（内置标准箱）");
assert.deepEqual(buildEffectiveDimensionRows(result).map((row) => row.value), ["260×180×45 mm", "0×0×50 mm", "260×180×95 mm"]);
assert.deepEqual(buildUtilizationRows(result).map((row) => row.value), ["86%", "62%", "12%"]);
assert.deepEqual(buildInnerLayoutSummary(result.geometry.box_view), [
  "刀卡格栅：2列 × 2排 × 2层，显示 4 台/箱",
  "单格约 135×100×55 mm，预留间隙 15 mm",
  "蓝色块为 PCBA，浅黄色薄板为刀卡隔板。",
]);
assert.deepEqual(buildPackagingDecisionRows(result).map((row) => row.label), ["用户选择", "系统推荐", "实际采用", "是否纠偏", "判断原因"]);
assert.equal(buildPackagingDecisionRows(result).find((row) => row.label === "是否纠偏").value, "已纠偏");
assert.deepEqual(buildAccessorySummary(result), ["已计入：缠绕膜", "未计入：打包带", "护角/护边：当前作为方案选项展示，待价格配置后纳入成本"]);
assert.deepEqual(buildCostRangeRows(result).map((row) => row.label), ["低位成本", "常用成本", "高位成本", "估算依据"]);
assert.deepEqual(buildCostRangeRows(result).map((row) => row.value), ["16.2 元/台", "18.66 元/台", "24.8 元/台", "按当前包材与辅料行情估算"]);
assert.deepEqual(buildValidationRows(result).map((row) => row.label), ["验证等级", "量产建议", "下一等级", "建议验证"]);
assert.equal(buildValidationRows(result).find((row) => row.label === "验证等级").value, "V0 仅系统估算，未完成人工工程确认");
assert.equal(buildValidationRows(result).find((row) => row.label === "建议验证").value, "跌落测试：验证运输冲击风险；堆码测试：验证纸箱承重");
assert.deepEqual(
  buildCorrectionRows({
    correction: {
      status: "已回填",
      actual_packaging_cost_per_unit: 2.35,
      actual_freight_per_unit: 1.72,
      actual_packaging_freight_per_unit: 4.07,
      estimated_total_cost_per_unit: 18.66,
      variance_per_unit: -14.59,
      variance_rate: -0.7819,
      variance_reason: "供应商纸价上涨，实际运费按月结账单回填",
    },
  }).map((row) => row.value),
  ["已回填", "2.35 元/台", "1.72 元/台", "4.07 元/台", "18.66 元/台", "-14.59 元/台", "-78.19%", "供应商纸价上涨，实际运费按月结账单回填"],
);
assert.deepEqual(buildCorrectionRows({ correction: { status: "未回填" } }).map((row) => row.value), ["未回填"]);
assert.deepEqual(buildCorrectionRows({}), []);

// 推荐方案报价看板
assert.deepEqual(buildRecommendedKpiCards(result).map((row) => row.label), [
  "综合总价",
  "装箱效率",
  "整托能力",
  "选中箱型",
  "托盘规格",
  "报价置信度",
]);
assert.deepEqual(buildRecommendedKpiCards(result).map((row) => row.value), ["18.66", "2", "36", "STD-01", "1200×1000", "B 中"]);
assert.deepEqual(buildRecommendedKpiCards(result).map((row) => row.unit), ["元/台", "台/箱", "台/托", "内置标准箱", "mm", ""]);
assert.deepEqual(buildRecommendedKpiCards({}).map((row) => row.value), []);

// 运费来源说明
assert.equal(
  buildFreightSourceNote(
    { source: "kuayue_vip", origin: "青岛市", logistics_product: "次日达", destination: "深圳市", minimum_charge: 171 },
    { original_freight_total: 200, discount: 0.9, freight_total: 180 },
  ),
  "运费来源：跨越VIP报价表（次日达 · 青岛市 → 深圳市，最低收费 171 元）；原始运费 200 元，折扣系数 0.9，折后运费 180 元",
);
assert.equal(
  buildFreightSourceNote({ source: "default", logistics_product: "特惠普运", destination: "深圳市", minimum_charge: 133 }),
  "运费来源：默认运价，未命中跨越报价表（特惠普运 · 深圳市，最低收费 133 元）",
);
assert.equal(buildFreightSourceNote(null), null);
assert.equal(buildFreightSourceNote({}), null);

// 自动设计箱型展示
const designedResult = {
  packaging_design: {
    enabled: true,
    designed: true,
    design_basis: {
      product_mm: { l: 160, w: 95, h: 35 },
      units_per_box: 24,
      wall_thickness_mm: 5,
      end_margin_mm: 10,
      clearance_mm: 1,
    },
    inner_mm: { l: 606, w: 356, h: 116 },
    outer_mm: { l: 616, w: 366, h: 126 },
    liner: {
      type: "divider_grid",
      clearance_mm: 1,
      card_thickness_mm: 3,
      divider_card_count: 9,
      pitch_mm: { l: 105.5, w: 99.5, h: 39.5 },
    },
    pallet_selection_reason: "自动选型 1200x1000：候选托盘中平面利用率最高（1200x1000 平面利用率 0.912；1100x1100 平面利用率 0.883）",
  },
  stacking: {
    pallet_size: "1200x1000",
    pallet_length_mm: 1200,
    pallet_width_mm: 1000,
    pallet_height_mm: 140,
    max_pallet_height_mm: 1500,
    box_height_mm: 126,
    theoretical_layers: 10,
    actual_layers: 10,
    stacking_pattern: "offset_interlock",
    total_height_mm: 1400,
  },
  carton_selection: {
    carton_id: "AUTO-01",
    source: "generated",
    modularity: "定制",
    typical_use: "按 160×95×35 自动设计",
    inner_size: { l: 606, w: 356, h: 116 },
  },
};

const designRows = buildPackagingDesignRows(designedResult);
assert.deepEqual(designRows.map((row) => row.label), [
  "功能开关",
  "设计结果",
  "设计箱内尺寸",
  "设计箱外尺寸",
  "内衬方案",
  "设计依据",
  "自动托盘选型",
]);
assert.equal(designRows.find((row) => row.label === "设计结果").value, "已生成设计箱并与标准箱同台竞争");
assert.equal(designRows.find((row) => row.label === "设计箱内尺寸").value, "606×356×116 mm");
assert.equal(designRows.find((row) => row.label === "设计箱外尺寸").value, "616×366×126 mm");
assert.equal(designRows.find((row) => row.label === "内衬方案").value, "刀卡格栅：9 张刀卡，卡厚 3 mm，单格间隙 1 mm");
assert.equal(
  designRows.find((row) => row.label === "设计依据").value,
  "按实物 160×95×35 mm、24 台/箱设计（壁厚 5 mm，端距 10 mm，间隙 1 mm）",
);
assert.equal(
  designRows.find((row) => row.label === "自动托盘选型").value,
  "自动选型 1200x1000：候选托盘中平面利用率最高（1200x1000 平面利用率 0.912；1100x1100 平面利用率 0.883）",
);

// 标准箱胜出：designed=false
const standardWon = buildPackagingDesignRows({
  packaging_design: {
    ...designedResult.packaging_design,
    designed: false,
    inner_mm: null,
    outer_mm: null,
    liner: null,
  },
});
assert.equal(standardWon.find((row) => row.label === "设计结果").value, "未采用设计箱（标准箱胜出）");
assert.equal(standardWon.some((row) => row.label === "设计箱内尺寸"), false);
assert.equal(standardWon.some((row) => row.label === "内衬方案"), false);
assert.ok(standardWon.some((row) => row.label === "自动托盘选型"));

// 未启用
const designDisabled = buildPackagingDesignRows({
  packaging_design: { enabled: false, designed: false, design_basis: null, inner_mm: null, outer_mm: null, liner: null, pallet_selection_reason: null },
});
assert.deepEqual(designDisabled.map((row) => row.label), ["功能开关"]);
assert.equal(designDisabled[0].value, "未启用");

// 缺字段返回空
assert.deepEqual(buildPackagingDesignRows({}), []);

// foam 内衬文案
assert.equal(
  buildPackagingDesignRows({
    packaging_design: {
      enabled: true,
      designed: true,
      inner_mm: { l: 244, w: 179, h: 119 },
      outer_mm: { l: 254, w: 189, h: 129 },
      liner: { type: "foam_cavity", foam_thickness_mm: 20, fit_clearance_mm: 2, cavity_mm: { l: 240, w: 175, h: 115 } },
    },
  }).find((row) => row.label === "内衬方案").value,
  "EPE/EPS 成型缓冲：缓冲厚 20 mm，内腔 240×175×115 mm",
);

// 堆叠行显示托盘规格
assert.equal(buildStackingRows(designedResult).find((row) => row.label === "托盘规格").value, "1200×1000 mm");
// 无托盘规格字段时兼容旧行为
assert.equal(
  buildStackingRows({ stacking: { pallet_height_mm: 120, max_pallet_height_mm: 1500, box_height_mm: 405, theoretical_layers: 3, actual_layers: 3, stacking_pattern: "straight", total_height_mm: 1335 } }).some((row) => row.label === "托盘规格"),
  false,
);

// 设计箱来源标签
assert.equal(buildCartonSelectionRows(designedResult).find((row) => row.label === "选中纸箱").value, "AUTO-01（系统设计箱）");

console.log("result view model ok");
