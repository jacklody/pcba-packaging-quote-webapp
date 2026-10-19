import { useEffect, useMemo, useState } from "react";
import { COST_FIELDS } from "../formOptions.js";
import { fetchCostOverrideFields } from "../api.js";

function fmt(value) {
  return value === null || value === undefined || value === "" ? "待确认/未计入" : String(value);
}

function fmtRange(field) {
  if (field.low === undefined || field.typical === undefined || field.high === undefined) return "未配置";
  return `${field.low} / ${field.typical} / ${field.high}`;
}

export default function CostConfigPanel({ form }) {
  const [backendFields, setBackendFields] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchCostOverrideFields()
      .then((data) => setBackendFields(data.fields || []))
      .catch((err) => setError(err.message || "成本配置读取失败"));
  }, []);

  const rows = useMemo(() => {
    const backendByKey = new Map(backendFields.map((field) => [field.key, field]));
    return COST_FIELDS.map((field) => {
      const backend = backendByKey.get(field.key) || {};
      const override = form.constraints.cost_overrides[field.key];
      return {
        key: field.key,
        label: field.label,
        unit: field.unit,
        frontendDefault: field.default,
        backendDefault: backend.default,
        selected: override === undefined || override === "" || override === null ? backend.default ?? field.default : override,
        source: override === undefined || override === "" || override === null ? backend.source || "前端默认" : "前端人工输入",
        range: fmtRange(field),
        grade: field.grade,
      };
    });
  }, [backendFields, form.constraints.cost_overrides]);

  return (
    <div className="card cost-config-card">
      <div className="card-heading-row">
        <div>
          <p className="section-eyebrow">成本参数</p>
          <h3>配置与前端选中单价清单</h3>
        </div>
      </div>
      {error && <p className="error-inline">{error}</p>}
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>字段</th>
              <th>单位</th>
              <th>前端默认</th>
              <th>后端配置</th>
              <th>当前采用</th>
              <th>低/常用/高</th>
              <th>来源</th>
              <th>置信度</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key}>
                <td>{row.label}<small>{row.key}</small></td>
                <td>{row.unit}</td>
                <td className="num">{fmt(row.frontendDefault)}</td>
                <td className="num">{fmt(row.backendDefault)}</td>
                <td className="num strong-num">{fmt(row.selected)}</td>
                <td className="num">{row.range}</td>
                <td>{row.source}</td>
                <td>{row.grade}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
