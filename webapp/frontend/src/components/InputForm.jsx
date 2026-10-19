import {
  CARTON_PRESETS,
  COST_FIELDS,
  DESTINATION_GROUPS,
  DESTINATIONS,
  LOGISTICS_PRODUCTS,
  ORIGIN_GROUPS,
  PACKAGING_MODE_OPTIONS,
  PALLET_AUTO_OPTION,
  PALLET_PRESETS,
  STANDARD_CARTONS,
  STRUCTURE_FEATURE_FIELDS,
  SUPPORTED_3D_FILE_EXTENSIONS,
  getCartonPreset,
  getPalletPreset,
} from "../formOptions.js";

const defaultPallet = getPalletPreset("1100x1100");
const defaultCarton = getCartonPreset("5-BC");

export const DEFAULT_FORM = {
  product: {
    name: "DRV-26P",
    product_class: "assembly",
    length_mm: 620,
    width_mm: 360,
    height_mm: 95,
    weight_kg: 9.8,
    fragility: "medium",
    esd_sensitive: true,
    has_heat_sink: true,
    has_sheet_metal: false,
    has_wire_harness: false,
    has_tall_fragile_components: true,
  },
  business: { annual_qty: 5000, design_frozen: true, allow_mold: true },
  logistics: {
    ship_mode: "pallet",
    origin: "青岛市",
    destination: "深圳市",
    logistics_product: "特惠普运",
    freight_discount: 1,
    pallet_size: defaultPallet.value,
    pallet_material: defaultPallet.material,
    pallet_reusable: defaultPallet.reusable,
    pallet_height_mm: defaultPallet.height_mm,
    max_pallet_height_mm: 1500,
    max_pallet_weight_kg: defaultPallet.max_weight_kg,
    supported_logistics_products: LOGISTICS_PRODUCTS,
    available_destinations: DESTINATIONS,
  },
  constraints: {
    auto_units_per_box: true,
    auto_design_carton: true,
    override_units_per_box: "",
    units_per_box_candidates: "1, 2, 4, 6",
    max_box_weight_kg: 25,
    carton_preset: defaultCarton.value,
    carton: {
      layers: defaultCarton.layers,
      flute: defaultCarton.flute,
      thickness_mm: defaultCarton.thickness_mm,
      max_load_kg: defaultCarton.max_load_kg,
      stack_safety_factor: defaultCarton.stack_safety_factor,
    },
    accessories: {
      stretch_film: true,
      packing_band: true,
      corner_protector: true,
      edge_protector: true,
    },
    packaging_mode: "auto",
    dimension_allowance: { length_mm: "", width_mm: "", height_mm: "" },
    drawing_file: null,
    carton_candidates: STANDARD_CARTONS,
    new_carton: { length_mm: "", width_mm: "", height_mm: "", typical_use: "" },
    cost_overrides: {},
  },
};

function toPayload(form) {
  const override = form.constraints.override_units_per_box;
  const costOverrides = {};
  for (const field of COST_FIELDS) {
    const raw = form.constraints.cost_overrides[field.key];
    if (raw !== undefined && raw !== "" && raw !== null) {
      costOverrides[field.key] = Number(raw);
    }
  }
  return {
    product: { ...form.product },
    business: { ...form.business },
    logistics: { ...form.logistics, freight_discount: Number(form.logistics.freight_discount) },
    constraints: {
      units_per_box_candidates: form.constraints.units_per_box_candidates
        .split(/[,，\s]+/)
        .map((s) => s.trim())
        .filter(Boolean)
        .map(Number),
      max_box_weight_kg: Number(form.constraints.max_box_weight_kg),
      auto_units_per_box: Boolean(form.constraints.auto_units_per_box),
      auto_design_carton: Boolean(form.constraints.auto_design_carton),
      override_units_per_box: !form.constraints.auto_units_per_box && override !== "" ? Number(override) : null,
      packaging_mode: form.constraints.packaging_mode,
      dimension_allowance: {
        length_mm: Number(form.constraints.dimension_allowance.length_mm || 0),
        width_mm: Number(form.constraints.dimension_allowance.width_mm || 0),
        height_mm: Number(form.constraints.dimension_allowance.height_mm || 0),
      },
      carton_candidates: form.constraints.carton_candidates
        .filter((carton) => carton.enabled)
        .map(({ enabled, ...carton }) => carton),
      carton: {
        layers: Number(form.constraints.carton.layers),
        flute: form.constraints.carton.flute,
        thickness_mm: Number(form.constraints.carton.thickness_mm),
        max_load_kg: Number(form.constraints.carton.max_load_kg),
        stack_safety_factor: Number(form.constraints.carton.stack_safety_factor),
      },
      accessories: { ...form.constraints.accessories },
      cost_overrides: costOverrides,
    },
  };
}

function validate(form) {
  const p = form.product;
  const dims = [
    ["长度", p.length_mm],
    ["宽度", p.width_mm],
    ["高度", p.height_mm],
    ["重量", p.weight_kg],
    ["托盘限高", form.logistics.max_pallet_height_mm],
    ["托盘限重", form.logistics.max_pallet_weight_kg],
    ["纸箱承重", form.constraints.carton.max_load_kg],
  ];
  for (const [label, value] of dims) {
    if (value === "" || Number(value) <= 0) return `${label}必须为正数`;
  }
  if (!p.name.trim()) return "请填写产品名称";
  if (!form.logistics.origin?.trim()) return "请选择始发地";
  const freightDiscount = Number(form.logistics.freight_discount);
  if (!Number.isFinite(freightDiscount) || freightDiscount <= 0 || freightDiscount > 1) return "运费折扣系数必须大于0且不超过1";
  const payload = toPayload(form);
  const list = payload.constraints.units_per_box_candidates;
  if (!list.length || list.some((n) => !Number.isInteger(n) || n <= 0)) {
    return "每箱数量候选必须为正整数列表，如 1, 2, 4";
  }
  const override = payload.constraints.override_units_per_box;
  if (override !== null && (!Number.isInteger(override) || override <= 0)) {
    return "人工指定每箱数量必须为正整数";
  }
  const activeCartons = form.constraints.carton_candidates.filter((carton) => carton.enabled);
  if (!activeCartons.length) return "请至少启用一个候选纸箱";
  for (const carton of activeCartons) {
    for (const key of ["length_mm", "width_mm", "height_mm"]) {
      if (!Number.isFinite(Number(carton[key])) || Number(carton[key]) <= 0) return "候选纸箱长宽高必须为正数";
    }
  }
  for (const key of ["length_mm", "width_mm", "height_mm"]) {
    const value = form.constraints.dimension_allowance[key];
    if (value !== "" && (!Number.isFinite(Number(value)) || Number(value) < 0)) return "结构件外扩尺寸必须为非负数";
  }
  const fileName = form.constraints.drawing_file?.name;
  if (fileName) {
    const lowerName = fileName.toLowerCase();
    if (!SUPPORTED_3D_FILE_EXTENSIONS.some((ext) => lowerName.endsWith(ext))) return "请上传支持的3D图纸或装配图片格式";
  }
  for (const field of COST_FIELDS) {
    const raw = form.constraints.cost_overrides[field.key];
    if (raw !== undefined && raw !== "" && raw !== null && (!Number.isFinite(Number(raw)) || Number(raw) <= 0)) {
      return `成本参数「${field.label}」必须为正数，留空则使用系统默认值`;
    }
  }
  return null;
}

function NumberField({ label, value, onChange, suffix, disabled = false, help }) {
  return (
    <label className="field">
      <span>{label}{suffix ? `（${suffix}）` : ""}</span>
      <input type="number" step="any" value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)} />
      {help && <small>{help}</small>}
    </label>
  );
}

function TextField({ label, value, onChange, disabled = false, help }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="text" value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)} />
      {help && <small>{help}</small>}
    </label>
  );
}

function SelectField({ label, value, onChange, options, help }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((option) => (
          <option key={option.value ?? option} value={option.value ?? option}>{option.label ?? option}</option>
        ))}
      </select>
      {help && <small>{help}</small>}
    </label>
  );
}

function CityField({ label, value, onChange, groups, help }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {groups.map((group) => (
          <optgroup key={group.province} label={group.province}>
            {group.destinations.map((city) => (
              <option key={city} value={city}>{city}</option>
            ))}
          </optgroup>
        ))}
      </select>
      {help && <small>{help}</small>}
    </label>
  );
}

function DestinationField({ value, onChange, help }) {
  return <CityField label="目的地" value={value} onChange={onChange} groups={DESTINATION_GROUPS} help={help} />;
}

function OriginField({ value, onChange, help }) {
  return <CityField label="始发地" value={value} onChange={onChange} groups={ORIGIN_GROUPS} help={help} />;
}

function CheckField({ label, checked, onChange, help, className = "" }) {
  return (
    <label className={`field field-check ${className}`.trim()} title={help || label}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{label}</span>
    </label>
  );
}

export default function InputForm({ form, setForm, onSubmit, submitting }) {
  const update = (section, key) => (value) =>
    setForm((f) => ({ ...f, [section]: { ...f[section], [key]: value } }));

  const updateConstraint = (key) => (value) =>
    setForm((f) => ({ ...f, constraints: { ...f.constraints, [key]: value } }));

  const updateAccessory = (key) => (value) =>
    setForm((f) => ({
      ...f,
      constraints: {
        ...f.constraints,
        accessories: { ...f.constraints.accessories, [key]: value },
      },
    }));

  const updateDimensionAllowance = (key) => (value) =>
    setForm((f) => ({
      ...f,
      constraints: {
        ...f.constraints,
        dimension_allowance: { ...f.constraints.dimension_allowance, [key]: value },
      },
    }));

  const updateDrawingFile = (file) =>
    setForm((f) => ({
      ...f,
      constraints: { ...f.constraints, drawing_file: file || null },
    }));

  const updateCostOverride = (key) => (value) =>
    setForm((f) => ({
      ...f,
      constraints: {
        ...f.constraints,
        cost_overrides: { ...f.constraints.cost_overrides, [key]: value },
      },
    }));

  const toggleCartonCandidate = (cartonId) => (enabled) =>
    setForm((f) => ({
      ...f,
      constraints: {
        ...f.constraints,
        carton_candidates: f.constraints.carton_candidates.map((carton) =>
          carton.carton_id === cartonId ? { ...carton, enabled } : carton
        ),
      },
    }));

  const updateNewCarton = (key) => (value) =>
    setForm((f) => ({
      ...f,
      constraints: { ...f.constraints, new_carton: { ...f.constraints.new_carton, [key]: value } },
    }));

  const addCustomCarton = () =>
    setForm((f) => {
      const c = f.constraints.new_carton;
      if (![c.length_mm, c.width_mm, c.height_mm].every((v) => Number(v) > 0)) return f;
      const index = f.constraints.carton_candidates.filter((item) => item.source === "custom").length + 1;
      return {
        ...f,
        constraints: {
          ...f.constraints,
          carton_candidates: [
            ...f.constraints.carton_candidates,
            {
              carton_id: `CUSTOM-${index}`,
              length_mm: Number(c.length_mm),
              width_mm: Number(c.width_mm),
              height_mm: Number(c.height_mm),
              modularity: "自定义",
              typical_use: c.typical_use || "人工新增纸箱",
              source: "custom",
              enabled: true,
            },
          ],
          new_carton: { length_mm: "", width_mm: "", height_mm: "", typical_use: "" },
        },
      };
    });

  const applyPalletPreset = (value) => {
    if (value === "auto") {
      setForm((f) => ({ ...f, logistics: { ...f.logistics, pallet_size: "auto" } }));
      return;
    }
    const preset = getPalletPreset(value);
    setForm((f) => ({
      ...f,
      logistics: {
        ...f.logistics,
        pallet_size: preset.value,
        pallet_material: preset.material,
        pallet_reusable: preset.reusable,
        pallet_height_mm: preset.height_mm,
        max_pallet_weight_kg: preset.max_weight_kg,
      },
    }));
  };

  const applyCartonPreset = (value) => {
    const preset = getCartonPreset(value);
    setForm((f) => ({
      ...f,
      constraints: {
        ...f.constraints,
        carton_preset: preset.value,
        carton: {
          layers: preset.layers,
          flute: preset.flute,
          thickness_mm: preset.thickness_mm,
          max_load_kg: preset.max_load_kg,
          stack_safety_factor: preset.stack_safety_factor,
        },
      },
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const error = validate(form);
    if (error) {
      alert(error);
      return;
    }
    onSubmit(toPayload(form));
  };

  return (
    <form className="input-form" onSubmit={handleSubmit}>
      <fieldset>
        <legend>产品</legend>
        <TextField label="产品名称" value={form.product.name} onChange={update("product", "name")} />
        <SelectField
          label="产品类别"
          value={form.product.product_class}
          onChange={update("product", "product_class")}
          options={[{ value: "pcba", label: "PCBA" }, { value: "assembly", label: "组件/整机" }]}
        />
        <NumberField label="长度" suffix="mm" value={form.product.length_mm} onChange={update("product", "length_mm")} />
        <NumberField label="宽度" suffix="mm" value={form.product.width_mm} onChange={update("product", "width_mm")} />
        <NumberField label="高度" suffix="mm" value={form.product.height_mm} onChange={update("product", "height_mm")} />
        <NumberField label="重量" suffix="kg/台" value={form.product.weight_kg} onChange={update("product", "weight_kg")} />
        <SelectField
          label="易碎等级"
          value={form.product.fragility}
          onChange={update("product", "fragility")}
          options={[{ value: "low", label: "低" }, { value: "medium", label: "中" }, { value: "high", label: "高" }]}
        />
        <CheckField
          label="ESD 敏感"
          checked={form.product.esd_sensitive}
          onChange={update("product", "esd_sensitive")}
          help="勾选后默认必须加入防静电袋；非防静电缓冲外需有防静电隔离层。"
        />
        {STRUCTURE_FEATURE_FIELDS.map((field) => (
          <CheckField
            key={field.key}
            label={field.label}
            checked={form.product[field.key]}
            onChange={update("product", field.key)}
            help={field.help}
          />
        ))}
        <details open className="structure-detail-panel">
          <summary>结构件尺寸外扩与3D图纸</summary>
          <p className="field-hint">复选项只做风险标记；只有这里录入的外扩尺寸会叠加到基础长宽高，并参与箱型、包装方式和成本计算。</p>
          <div className="dimension-allowance-row">
            <NumberField label="长向外扩" suffix="mm" value={form.constraints.dimension_allowance.length_mm} onChange={updateDimensionAllowance("length_mm")} />
            <NumberField label="宽向外扩" suffix="mm" value={form.constraints.dimension_allowance.width_mm} onChange={updateDimensionAllowance("width_mm")} />
            <NumberField label="高向外扩" suffix="mm" value={form.constraints.dimension_allowance.height_mm} onChange={updateDimensionAllowance("height_mm")} />
          </div>
          <small>可用于散热器、钣金、线束附件、易损高件的总包络外扩；多项同时存在时请输入合计最大外扩。</small>
          <label className="field file-field">
            <span>上传3D图纸/装配图片</span>
            <input type="file" accept={SUPPORTED_3D_FILE_EXTENSIONS.join(",")} onChange={(e) => updateDrawingFile(e.target.files?.[0])} />
            <small>{form.constraints.drawing_file ? `已选择：${form.constraints.drawing_file.name}。当前阶段请人工确认外扩尺寸，后续接入3D自动解析。` : `支持 ${SUPPORTED_3D_FILE_EXTENSIONS.join("、")}；图片类仅辅助识别，需人工确认尺寸。`}</small>
          </label>
        </details>
      </fieldset>

      <fieldset>
        <legend>业务</legend>
        <NumberField label="年用量" suffix="台" value={form.business.annual_qty} onChange={update("business", "annual_qty")} />
        <div className="business-check-grid">
          <CheckField
            label="设计冻结"
            checked={form.business.design_frozen}
            onChange={update("business", "design_frozen")}
            help="代表产品结构和尺寸稳定；冻结后才适合优先评估 EPS 开模方案。"
          />
          <CheckField
            label="允许开模"
            checked={form.business.allow_mold}
            onChange={update("business", "allow_mold")}
            help="勾选后允许 EPS 模具投入并计入摊销；不勾选时优先免模具方案。"
          />
        </div>
      </fieldset>

      <fieldset>
        <legend>物流</legend>
        <OriginField value={form.logistics.origin} onChange={update("logistics", "origin")} help="默认青岛市；当前跨越费率表按物流产品和目的地匹配，始发地作为报价路线记录。" />
        <DestinationField value={form.logistics.destination} onChange={update("logistics", "destination")} help="按省份分组展示，覆盖跨越报价表全部 354 个目的地。" />
        <SelectField label="物流产品" value={form.logistics.logistics_product} onChange={update("logistics", "logistics_product")} options={LOGISTICS_PRODUCTS} help="默认特惠普运；次日达作为加急比较项。" />
        <NumberField label="运费折扣系数" value={form.logistics.freight_discount} onChange={update("logistics", "freight_discount")} help="填写与物流商谈好的协议折扣：1 表示原价，0.95 表示 95 折，0.9 表示 9 折，0.85 表示 85 折；只能输入大于 0 且不超过 1 的数字。" />
        <SelectField label="托盘尺寸" value={form.logistics.pallet_size} onChange={applyPalletPreset} options={[PALLET_AUTO_OPTION, ...PALLET_PRESETS]} help="选「自动」时系统枚举标准托盘并按平面利用率最高选型，选型理由在结果页展示；选具体尺寸会自动带出限重和托盘高度。" />
        <NumberField label="托盘高度" suffix="mm" value={form.logistics.pallet_height_mm} disabled onChange={() => {}} />
        <NumberField label="托盘限高" suffix="mm" value={form.logistics.max_pallet_height_mm} onChange={update("logistics", "max_pallet_height_mm")} />
        <NumberField label="托盘限重" suffix="kg" value={form.logistics.max_pallet_weight_kg} onChange={update("logistics", "max_pallet_weight_kg")} help="根据托盘尺寸预设自动带出，可人工覆盖。" />
        <CheckField label="托盘回收" checked={form.logistics.pallet_reusable} onChange={update("logistics", "pallet_reusable")} help="默认不回收；后续影响托盘摊销口径。" />
      </fieldset>

      <fieldset>
        <legend>包装方式</legend>
        <SelectField
          label="包装方式选择"
          value={form.constraints.packaging_mode}
          onChange={updateConstraint("packaging_mode")}
          options={PACKAGING_MODE_OPTIONS}
          help="自动判断会结合尺寸、重量、元件高度和结构特征推荐刀卡隔档或 EPE/EPS 成型缓冲；人工选择不合理时结果页会提示原因并纠偏。"
        />
      </fieldset>

      <fieldset>
        <legend>装箱与纸箱</legend>
        <CheckField
          label="自动设计箱型"
          checked={form.constraints.auto_design_carton}
          onChange={updateConstraint("auto_design_carton")}
          help="按实物尺寸自动生成定制箱（含内衬/刀卡布局），与标准箱、人工新增箱按总成本+利用率同台竞争选优。"
        />
        <CheckField label="自动计算每箱数量" checked={form.constraints.auto_units_per_box} onChange={updateConstraint("auto_units_per_box")} help="按产品尺寸、重量、纸箱承重和单箱限重自动取最大可行值。" />
        <NumberField label="人工指定每箱数量" value={form.constraints.override_units_per_box} disabled={form.constraints.auto_units_per_box} onChange={updateConstraint("override_units_per_box")} help="关闭自动计算后生效。" />
        <TextField label="候选数量兜底" value={form.constraints.units_per_box_candidates} onChange={updateConstraint("units_per_box_candidates")} help="自动计算不可行或后续比较时使用，如 1,2,4,6。" />
        <NumberField label="单箱限重" suffix="kg" value={form.constraints.max_box_weight_kg} onChange={updateConstraint("max_box_weight_kg")} help="系统会按产品单重×每箱数量估算单箱毛重并校验。" />
        <SelectField label="纸箱结构" value={form.constraints.carton_preset} onChange={applyCartonPreset} options={CARTON_PRESETS} help="纸箱厚度本身不等于承重，主要通过层数、楞型、抗压/安全系数影响堆码。" />
        <NumberField label="纸箱承重" suffix="kg" value={form.constraints.carton.max_load_kg} onChange={(value) => setForm((f) => ({ ...f, constraints: { ...f.constraints, carton: { ...f.constraints.carton, max_load_kg: value } } }))} />
        <details open>
          <summary>候选纸箱库（标准箱优先，可人工增加）</summary>
          <div className="carton-candidate-grid">
            {form.constraints.carton_candidates.map((carton) => (
              <label className="carton-candidate" key={carton.carton_id}>
                <input type="checkbox" checked={carton.enabled} onChange={(e) => toggleCartonCandidate(carton.carton_id)(e.target.checked)} />
                <span>
                  <strong>{carton.carton_id}</strong> {carton.length_mm}×{carton.width_mm}×{carton.height_mm}mm · {carton.modularity}
                  <small>{carton.typical_use}</small>
                </span>
              </label>
            ))}
          </div>
          <div className="custom-carton-row">
            <NumberField label="新增箱长" suffix="mm" value={form.constraints.new_carton.length_mm} onChange={updateNewCarton("length_mm")} />
            <NumberField label="新增箱宽" suffix="mm" value={form.constraints.new_carton.width_mm} onChange={updateNewCarton("width_mm")} />
            <NumberField label="新增箱高" suffix="mm" value={form.constraints.new_carton.height_mm} onChange={updateNewCarton("height_mm")} />
            <TextField label="用途备注" value={form.constraints.new_carton.typical_use} onChange={updateNewCarton("typical_use")} />
            <button type="button" className="secondary-button" onClick={addCustomCarton}>增加纸箱</button>
          </div>
        </details>
      </fieldset>

      <fieldset>
        <legend>默认辅料</legend>
        <CheckField label="缠绕膜" checked={form.constraints.accessories.stretch_film} onChange={updateAccessory("stretch_film")} />
        <CheckField label="打包带" checked={form.constraints.accessories.packing_band} onChange={updateAccessory("packing_band")} />
        <CheckField label="护角" checked={form.constraints.accessories.corner_protector} onChange={updateAccessory("corner_protector")} help="默认显示并参与方案记录；价格配置后可纳入成本。" />
        <CheckField label="护边" checked={form.constraints.accessories.edge_protector} onChange={updateAccessory("edge_protector")} help="默认显示并参与方案记录；价格配置后可纳入成本。" />
      </fieldset>

      <fieldset>
        <legend>成本参数（可人工修改）</legend>
        <p className="field-hint">
          输入框留空时使用系统默认值（灰色占位显示）；填写后将按人工值计算，结果中会标注哪些字段被人工修改。置信度：A 高 / B 中 / C 低 / D 待校准。
        </p>
        {COST_FIELDS.map((field) => (
          <label className="field" key={field.key}>
            <span>
              {field.label}（{field.unit}·{field.grade} 级）
            </span>
            <input
              type="number"
              step="any"
              value={form.constraints.cost_overrides[field.key] ?? ""}
              placeholder={field.default === "" ? "待确认，留空不计成本" : String(field.default)}
              onChange={(e) => updateCostOverride(field.key)(e.target.value)}
            />
            {field.help && <small>{field.help}</small>}
          </label>
        ))}
      </fieldset>

      <button type="submit" disabled={submitting}>
        {submitting ? "计算中..." : "生成包装方案"}
      </button>
    </form>
  );
}
