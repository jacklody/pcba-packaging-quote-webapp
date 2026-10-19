import assert from "node:assert/strict";
import {
  COST_FIELDS,
  DESTINATIONS,
  DESTINATION_GROUPS,
  LOGISTICS_PRODUCTS,
  ORIGIN_GROUPS,
  ORIGINS,
  PACKAGING_MODE_OPTIONS,
  PALLET_AUTO_OPTION,
  STANDARD_CARTONS,
  STRUCTURE_FEATURE_FIELDS,
  SUPPORTED_3D_FILE_EXTENSIONS,
  getCartonPreset,
  getPalletPreset,
} from "./formOptions.js";

assert.deepEqual(LOGISTICS_PRODUCTS, ["特惠普运", "次日达"]);
assert.deepEqual(PACKAGING_MODE_OPTIONS.map((o) => o.value), ["auto", "divider", "foam"]);
assert.deepEqual(STRUCTURE_FEATURE_FIELDS.map((f) => f.key), [
  "has_heat_sink",
  "has_sheet_metal",
  "has_wire_harness",
  "has_tall_fragile_components",
]);
assert.equal(STRUCTURE_FEATURE_FIELDS.every((f) => f.label && f.help && f.allowanceHelp), true);
assert.deepEqual(SUPPORTED_3D_FILE_EXTENSIONS, [".step", ".stp", ".iges", ".igs", ".stl", ".obj", ".glb", ".gltf", ".png", ".jpg", ".jpeg"]);
assert.equal(STANDARD_CARTONS.length, 15);
assert.deepEqual(STANDARD_CARTONS[0], {
  carton_id: "STD-01",
  length_mm: 300,
  width_mm: 250,
  height_mm: 180,
  modularity: "✅",
  typical_use: "小板、电源小板、样品箱",
  source: "standard",
  enabled: true,
});
assert.equal(STANDARD_CARTONS.some((c) => c.carton_id === "STD-07" && c.length_mm === 500 && c.width_mm === 400 && c.height_mm === 240), true);
assert.equal(DESTINATIONS.includes("深圳市"), true);
assert.equal(DESTINATIONS.includes("黔东南苗族侗族自治州"), true);
assert.equal(DESTINATIONS.length > 300, true);

// 目的地省份分组
assert.equal(Array.isArray(DESTINATION_GROUPS), true);
assert.equal(DESTINATION_GROUPS.length, 30);
assert.ok(DESTINATION_GROUPS.every((g) => g.province && Array.isArray(g.destinations) && g.destinations.length > 0));
const flatFromGroups = DESTINATION_GROUPS.flatMap((g) => g.destinations);
assert.equal(flatFromGroups.length, DESTINATIONS.length);
assert.equal(new Set(flatFromGroups).size, flatFromGroups.length);
assert.deepEqual([...flatFromGroups].sort(), [...DESTINATIONS].sort());
const guangdong = DESTINATION_GROUPS.find((g) => g.province === "广东省");
assert.ok(guangdong);
assert.equal(guangdong.destinations.includes("深圳市"), true);
assert.equal(DESTINATION_GROUPS[0].province, "北京");
assert.equal(ORIGINS.includes("青岛市"), true);
assert.equal(ORIGINS.includes("上海市"), true);
assert.equal(ORIGIN_GROUPS[0].province, "山东省");
assert.equal(ORIGIN_GROUPS[0].destinations.includes("青岛市"), true);

const costKeys = COST_FIELDS.map((f) => f.key);
assert.equal(costKeys.length, new Set(costKeys).size);
assert.ok(COST_FIELDS.every((f) => f.label && f.unit && f.grade));
assert.equal(COST_FIELDS.find((f) => f.key === "anti_static_bag_price_per_unit").grade, "D");
assert.equal(COST_FIELDS.find((f) => f.key === "corrugated_material_yuan_per_m2").default, 14.35);

const rangedCostFields = COST_FIELDS.filter((f) => f.low !== undefined || f.typical !== undefined || f.high !== undefined);
assert.equal(rangedCostFields.length >= 9, true);
assert.ok(rangedCostFields.every((f) => typeof f.low === "number" && typeof f.typical === "number" && typeof f.high === "number"));
assert.ok(rangedCostFields.every((f) => f.low <= f.typical && f.typical <= f.high));
assert.deepEqual(
  ["eps_base_fee", "eps_vol_fee", "epe_unit_price_per_m3", "pallet_purchase_price", "anti_static_bag_price_per_unit"].map((key) => {
    const field = COST_FIELDS.find((f) => f.key === key);
    return [field.key, field.default, field.low, field.typical, field.high];
  }),
  [
    ["eps_base_fee", 60, 40, 60, 90],
    ["eps_vol_fee", 520, 350, 520, 700],
    ["epe_unit_price_per_m3", 650, 450, 650, 1200],
    ["pallet_purchase_price", 110, 80, 110, 180],
    ["anti_static_bag_price_per_unit", 1.2, 0.5, 1.2, 3.5],
  ],
);

const pallet = getPalletPreset("1200x1000");
assert.equal(pallet.max_weight_kg, 900);
assert.equal(pallet.reusable, false);

// 托盘自动选型选项
assert.deepEqual(PALLET_AUTO_OPTION, { value: "auto", label: "自动选托盘（枚举标准托盘）" });
assert.equal(getPalletPreset("auto"), null);

const carton = getCartonPreset("7-BC");
assert.equal(carton.layers, 7);
assert.equal(carton.max_load_kg, 55);

console.log("form options ok");
