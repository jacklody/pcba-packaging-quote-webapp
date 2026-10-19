import { COST_FIELDS } from "../formOptions.js";
import {
  buildAccessorySummary,
  buildBoxAnalysisRows,
  buildCartonSelectionRows,
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
} from "../resultViewModel.js";
import Box3DView from "./Box3DView.jsx";
import Pallet3DView from "./Pallet3DView.jsx";

const CONFIDENCE_LABEL = { A: "A 高", B: "B 中", C: "C 低", D: "D 待校准" };

function overrideLabel(key) {
  const field = COST_FIELDS.find((f) => f.key === key);
  return field ? field.label : key;
}

function CostBreakdown({ cost, recommended, appliedOverrides, freightSourceNote, moldAmortization }) {
  const rows = [
    ["包材小计/台", cost.packaging_material_per_unit],
    ["模具摊销/台", cost.mold_amortize_per_unit],
    ["托盘辅料/台", cost.pallet_accessory_per_unit],
    ["运费/台", cost.freight_per_unit],
  ];
  return (
    <div className="card">
      <h3>成本拆解（元/台）</h3>
      {appliedOverrides.length > 0 && (
        <p className="muted detail-note">人工修改的成本参数：{appliedOverrides.map(overrideLabel).join("、")}</p>
      )}
      {freightSourceNote && <p className="muted detail-note">{freightSourceNote}</p>}
      {moldAmortization && (
        <p className="muted detail-note">
          模具费：{moldAmortization.reason} {moldAmortization.formula}；当前输入值 {moldAmortization.input_per_unit} 元/台，实际计入 {moldAmortization.cost_per_unit} 元/台。
        </p>
      )}
      <table>
        <tbody>
          {rows.map(([label, value]) => (
            <tr key={label}>
              <td>{label}</td>
              <td className="num">{value}</td>
            </tr>
          ))}
          <tr className="total">
            <td>合计/台</td>
            <td className="num">{recommended.total_cost_per_unit}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function DetailTable({ title, rows, note }) {
  if (!rows.length) return null;
  return (
    <div className="card">
      <h3>{title}</h3>
      {note && <p className="muted detail-note">{note}</p>}
      <table>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <td>{row.label}</td>
              <td className={`num ${row.status === "warning" ? "status-warning" : ""}`}>{row.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AccessorySummary({ result }) {
  return (
    <div className="card">
      <h3>辅料计入状态</h3>
      <ul className="plain-list">
        {buildAccessorySummary(result).map((text) => (
          <li key={text}>{text}</li>
        ))}
      </ul>
    </div>
  );
}

function BomTable({ bom }) {
  return (
    <div className="card">
      <h3>包材 BOM</h3>
      <table>
        <thead>
          <tr>
            <th>项目</th>
            <th>规格</th>
            <th>数量/台</th>
            <th>单价(元)</th>
            <th>成本/台</th>
            <th>置信度</th>
          </tr>
        </thead>
        <tbody>
          {bom.map((row) => (
            <tr key={row.item}>
              <td>{row.item}</td>
              <td>{row.spec}</td>
              <td className="num">{row.qty}</td>
              <td className="num">{row.unit_price}</td>
              <td className="num">{row.cost_per_unit}</td>
              <td>{CONFIDENCE_LABEL[row.confidence] || row.confidence}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ResultPanel({ result, error }) {
  if (error) {
    return (
      <div className="result-panel">
        <div className="card error-card">计算失败：{error}</div>
      </div>
    );
  }
  if (!result) {
    return (
      <div className="result-panel">
        <div className="card placeholder-card">填写左侧参数后点击「生成包装方案」</div>
      </div>
    );
  }

  const { recommended, cost, bom, risks, alternatives, geometry } = result;
  const packagingDecisionRows = buildPackagingDecisionRows(result);
  const cartonSelectionRows = buildCartonSelectionRows(result);
  const packagingDesignRows = buildPackagingDesignRows(result);
  const effectiveDimensionRows = buildEffectiveDimensionRows(result);
  const utilizationRows = buildUtilizationRows(result);
  const boxAnalysisRows = buildBoxAnalysisRows(result);
  const stackingRows = buildStackingRows(result);
  const innerLayoutSummary = buildInnerLayoutSummary(geometry.box_view);
  const recommendedKpis = buildRecommendedKpiCards(result);

  return (
    <div className="result-panel">
      <div className="card recommended-card quote-hero">
        <div className="quote-hero-heading">
          <div>
            <p className="section-eyebrow">推荐报价方案</p>
            <h3>包装 BOM 与托盘运输报价</h3>
          </div>
          <span className="confidence-pill">{CONFIDENCE_LABEL[recommended.confidence] || recommended.confidence}</span>
        </div>
        <p className="scheme-summary">{recommended.summary}</p>
        <div className="kpi-row quote-kpi-grid">
          {recommendedKpis.map((kpi) => (
            <div className={`kpi quote-kpi ${kpi.tone === "primary" ? "primary" : ""}`} key={kpi.label}>
              <span className="kpi-label">{kpi.label}</span>
              <span className="kpi-value">{kpi.value}</span>
              {kpi.unit && <span className="kpi-unit">{kpi.unit}</span>}
            </div>
          ))}
        </div>
      </div>

      <CostBreakdown
        cost={cost}
        recommended={recommended}
        appliedOverrides={result.cost_overrides_applied || []}
        freightSourceNote={buildFreightSourceNote(result.freight_rate, result.freight)}
        moldAmortization={result.mold_amortization}
      />

      <DetailTable
        title="成本区间估算"
        rows={buildCostRangeRows(result)}
        note="低位/常用/高位用于表达近年包装材料行情波动和采购价不确定性；最终以供应商报价与实际账单回填纠偏。"
      />

      <DetailTable
        title="包装验证等级"
        rows={buildValidationRows(result)}
        note="V0 表示仅系统估算；进入量产前建议至少完成包装工程确认，并按产品风险补充跌落、振动、堆码和 ESD 验证。"
      />

      <DetailTable
        title="包装方式判断"
        rows={packagingDecisionRows}
        note="刀卡隔档适合小尺寸、低矮、轻量且无突出结构件的 PCBA；当板长接近/超过箱高、重量或结构风险较高时，系统会建议 EPE/EPS 成型缓冲。"
      />

      <DetailTable
        title="计算采用尺寸"
        rows={effectiveDimensionRows}
        note="基础尺寸来自产品长宽高；结构外扩来自人工录入或后续3D图纸解析，系统只用计算采用尺寸参与装箱。"
      />

      <DetailTable
        title="纸箱选择与利用率"
        rows={[...cartonSelectionRows, ...utilizationRows]}
        note="系统优先在启用的标准箱和人工新增箱中选型，评分同时考虑包装占位利用率、托盘平面利用率、成本和运费。"
      />

      <DetailTable
        title="自动设计箱型"
        rows={packagingDesignRows}
        note="启用后系统按实物尺寸与每箱数量自动生成定制箱（内/外尺寸与内衬布局），与标准箱、人工新增箱同台竞争；托盘选「自动」时枚举标准托盘并按平面利用率选型。"
      />

      <DetailTable
        title="装箱与纸箱校验"
        rows={boxAnalysisRows}
        note="单箱毛重 = 产品单重 × 当前采用数量 + 空箱自重（纸箱面积×面密度）；纸箱厚度只是结构线索，堆码承重还取决于层数、楞型、承重上限和安全系数。"
      />

      <DetailTable
        title="整托堆叠解释"
        rows={stackingRows}
        note="理论层数由托盘限高、托盘高度和单箱高度计算；实际层数由引擎在托盘限高、限重和排布约束下选取。"
      />

      <AccessorySummary result={result} />

      <div className="card" id="view3d-box">
        <h3>单箱预览</h3>
        <p className="muted">外箱 {geometry.box_view.outer_box.l}×{geometry.box_view.outer_box.w}×{geometry.box_view.outer_box.h} mm，可拖拽旋转</p>
        {innerLayoutSummary.length > 0 && (
          <ul className="plain-list detail-note">
            {innerLayoutSummary.map((text) => (
              <li key={text}>{text}</li>
            ))}
          </ul>
        )}
        <Box3DView boxView={geometry.box_view} />
      </div>

      <div className="card" id="view3d-pallet">
        <h3>整托预览</h3>
        <p className="muted">
          {geometry.pallet_view.pallet.l}×{geometry.pallet_view.pallet.w} 托盘，{geometry.pallet_view.layout.boxes_per_layer} 箱/层 × {geometry.pallet_view.layout.layers} 层，总高 {geometry.pallet_view.total_height_mm} mm；{geometry.pallet_view.layout.stacking_pattern === "rotate_90_interlock" ? "奇偶层旋转90°互锁示意" : geometry.pallet_view.layout.stacking_pattern === "offset_interlock" ? "奇偶层错缝互锁示意" : "直码示意"}，可拖拽旋转
        </p>
        <Pallet3DView palletView={geometry.pallet_view} />
      </div>

      <BomTable bom={bom} />

      {risks.length > 0 && (
        <div className="card">
          <h3>风险提示</h3>
          <ul className="risk-list">
            {risks.map((r, i) => (
              <li key={i} className={`risk-${r.level}`}>{r.message}</li>
            ))}
          </ul>
        </div>
      )}

      {alternatives.length > 0 && (
        <div className="card">
          <h3>备选方案</h3>
          <table>
            <thead>
              <tr>
                <th>方案</th>
                <th>说明</th>
                <th>元/台</th>
                <th>置信度</th>
              </tr>
            </thead>
            <tbody>
              {alternatives.map((alt) => (
                <tr key={alt.scheme_id}>
                  <td>{alt.scheme_id}</td>
                  <td>{alt.summary}</td>
                  <td className="num">{alt.total_cost_per_unit}</td>
                  <td>{CONFIDENCE_LABEL[alt.confidence] || alt.confidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
