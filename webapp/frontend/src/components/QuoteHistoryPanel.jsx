import { useEffect, useMemo, useState } from "react";
import { fetchQuoteHistory, fetchQuoteHistoryDetail, postQuoteCorrection } from "../api.js";
import { buildCorrectionRows } from "../resultViewModel.js";

const CONFIDENCE_LABEL = { A: "A 高", B: "B 中", C: "C 低", D: "D 待校准" };

function formatCost(value) {
  return value == null ? "-" : `${Number(value).toFixed(2)} 元/台`;
}

function costRows(response) {
  const cost = response?.cost || {};
  return [
    ["包装费/台", cost.packaging_material_per_unit],
    ["模具摊销/台", cost.mold_amortize_per_unit],
    ["托盘辅料/台", cost.pallet_accessory_per_unit],
    ["运费/台", cost.freight_per_unit],
    ["合计/台", response?.recommended?.total_cost_per_unit],
  ];
}

export default function QuoteHistoryPanel({ refreshToken, onRestoreResult }) {
  const [query, setQuery] = useState("");
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [correctionForm, setCorrectionForm] = useState({ actual_carton_purchase_price: "", actual_packaging_cost_per_unit: "", actual_freight_per_unit: "", variance_reason: "" });

  async function load(q = query) {
    setLoading(true);
    setError("");
    try {
      const data = await fetchQuoteHistory(q);
      setRecords(data.records || []);
    } catch (err) {
      setError(err.message || "历史记录加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function openRecord(id) {
    try {
      const data = await fetchQuoteHistoryDetail(id);
      setSelected(data);
      setCorrectionForm({
        actual_carton_purchase_price: data.correction?.actual_carton_purchase_price ?? "",
        actual_packaging_cost_per_unit: data.correction?.actual_packaging_cost_per_unit ?? "",
        actual_freight_per_unit: data.correction?.actual_freight_per_unit ?? "",
        variance_reason: data.correction?.variance_reason ?? "",
      });
      onRestoreResult(data.response);
    } catch (err) {
      setError(err.message || "记录读取失败");
    }
  }

  async function submitCorrection(event) {
    event.preventDefault();
    if (!selected) return;
    try {
      const data = await postQuoteCorrection(selected.id, correctionForm);
      const next = { ...selected, correction: data.correction };
      setSelected(next);
      await load(query);
    } catch (err) {
      setError(err.message || "纠偏回填失败");
    }
  }

  useEffect(() => {
    load("");
  }, [refreshToken]);

  const selectedCostRows = useMemo(() => costRows(selected?.response), [selected]);
  const correctionRows = useMemo(() => buildCorrectionRows(selected || {}), [selected]);
  const selectedBom = selected?.response?.bom || [];

  return (
    <div className="card history-card">
      <div className="card-heading-row">
        <div>
          <p className="section-eyebrow">报价经验库</p>
          <h3>历史报价记录</h3>
        </div>
        <button type="button" className="ghost-button" onClick={() => load(query)} disabled={loading}>
          {loading ? "刷新中" : "刷新"}
        </button>
      </div>
      <div className="history-search-row">
        <input value={query} placeholder="按产品、目的地、物流产品搜索" onChange={(e) => setQuery(e.target.value)} />
        <button type="button" className="secondary-button" onClick={() => load(query)}>查询</button>
      </div>
      {error && <p className="error-inline">{error}</p>}
      {records.length === 0 ? (
        <p className="muted detail-note">暂无历史报价；每次成功生成方案后会自动保存输入与输出快照。</p>
      ) : (
        <div className="history-list">
          {records.map((record) => {
                    const isSelected = selected?.id === record.id;
                    return (
                      <button type="button" className={`history-item ${isSelected ? "active" : ""}`} key={record.id} onClick={() => openRecord(record.id)}>
                        <span className="history-title">#{record.id} {record.product_name}</span>
                        <span>{record.product_size}</span>
                        <span>{record.destination} · {record.logistics_product}</span>
                        <span className={`correction-status ${record.correction_status === "已回填" ? "ok" : "pending"}`}>{record.correction_status || "未回填"}</span>
                        <strong>{formatCost(record.total_cost_per_unit)}</strong>
                        {isSelected && (
                          <span className="history-cost-pills">
                            <span>包装费 {formatCost(selected.response.cost?.packaging_material_per_unit)}</span>
                            <span>运费 {formatCost(selected.response.cost?.freight_per_unit)}</span>
                          </span>
                        )}
                        <small>{record.created_at} · {record.units_per_box || "-"}台/箱 · {record.units_per_pallet || "-"}台/托</small>
                      </button>
                    );
                  })}
        </div>
      )}
      {selected && (
        <div className="history-detail-panel">
          <div className="history-detail-heading">
            <div>
              <p className="section-eyebrow">历史明细</p>
              <h4>#{selected.id} {selected.product_name}</h4>
            </div>
            <span className="confidence-pill">{CONFIDENCE_LABEL[selected.confidence] || selected.confidence}</span>
          </div>

          <div className="history-cost-summary">
            {selectedCostRows.map(([label, value]) => (
              <div className="history-cost-cell" key={label}>
                <span>{label}</span>
                <strong>{formatCost(value)}</strong>
              </div>
            ))}
          </div>

          <form className="correction-form" onSubmit={submitCorrection}>
            <h4>实际价回填与偏差纠偏</h4>
            <div className="correction-grid">
              <label>实际纸箱采购价<input value={correctionForm.actual_carton_purchase_price} onChange={(e) => setCorrectionForm({ ...correctionForm, actual_carton_purchase_price: e.target.value })} placeholder="元/箱，可选" /></label>
              <label>实际包装费/台<input required value={correctionForm.actual_packaging_cost_per_unit} onChange={(e) => setCorrectionForm({ ...correctionForm, actual_packaging_cost_per_unit: e.target.value })} placeholder="元/台" /></label>
              <label>实际运费/台<input required value={correctionForm.actual_freight_per_unit} onChange={(e) => setCorrectionForm({ ...correctionForm, actual_freight_per_unit: e.target.value })} placeholder="元/台" /></label>
              <label>偏差原因<input required value={correctionForm.variance_reason} onChange={(e) => setCorrectionForm({ ...correctionForm, variance_reason: e.target.value })} placeholder="如纸价上涨、月结运费回填" /></label>
            </div>
            <button type="submit" className="secondary-button">保存纠偏</button>
          </form>

          {correctionRows.length > 0 && (
            <div className="correction-summary">
              {correctionRows.map((row) => (
                <div className={`history-cost-cell ${row.status || ""}`} key={row.label}>
                  <span>{row.label}</span>
                  <strong>{row.value}</strong>
                </div>
              ))}
            </div>
          )}

          <h4>包装成本 BOM</h4>
          <div className="table-scroll history-bom-table">
            <table>
              <thead>
                <tr>
                  <th>项目</th>
                  <th>规格</th>
                  <th>数量/台</th>
                  <th>单价</th>
                  <th>成本/台</th>
                  <th>置信度</th>
                </tr>
              </thead>
              <tbody>
                {selectedBom.map((row) => (
                  <tr key={`${row.item}-${row.spec}`}>
                    <td>{row.item}</td>
                    <td>{row.spec}</td>
                    <td className="num">{row.qty}</td>
                    <td className="num">{row.unit_price}</td>
                    <td className="num strong-num">{row.cost_per_unit}</td>
                    <td>{CONFIDENCE_LABEL[row.confidence] || row.confidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <details className="history-snapshot-panel">
            <summary>输入/输出 JSON 快照</summary>
            <div className="history-json-grid">
              <div>
                <h4>输入</h4>
                <pre>{JSON.stringify(selected.request, null, 2)}</pre>
              </div>
              <div>
                <h4>输出</h4>
                <pre>{JSON.stringify(selected.response, null, 2)}</pre>
              </div>
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
