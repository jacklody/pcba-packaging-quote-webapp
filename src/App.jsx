import "./styles.css";

const kpis = [
  ["含模具总价", "待计算", "元/台"],
  ["装箱效率", "待计算", "台/箱"],
  ["整托能力", "待计算", "台/托"],
  ["选中箱型", "待后端返回", ""],
  ["托盘规格", "待后端返回", "mm"],
  ["报价置信度", "待校准", ""],
];

export default function App() {
  return (
    <div className="app-layout">
      <header className="app-header">
        <h1>PCBA 包装方案模拟与成本预估系统</h1>
      </header>

      <section className="input-form">
        <fieldset>
          <legend>产品参数</legend>
          <label className="field"><span>产品名称</span><input defaultValue="DRV-26P" /></label>
          <label className="field"><span>产品类别</span><select defaultValue="assembly"><option value="pcba">PCBA</option><option value="assembly">组件/整机</option></select></label>
          <label className="field"><span>长度（mm）</span><input type="number" defaultValue="620" /></label>
          <label className="field"><span>宽度（mm）</span><input type="number" defaultValue="360" /></label>
          <label className="field"><span>高度（mm）</span><input type="number" defaultValue="95" /></label>
          <label className="field"><span>重量（kg/台）</span><input type="number" defaultValue="9.8" /></label>
        </fieldset>

        <fieldset>
          <legend>物流与包装</legend>
          <label className="field"><span>目的地</span><select defaultValue="深圳市"><option>深圳市</option><option>上海市</option><option>北京市</option><option>广州市</option></select></label>
          <label className="field"><span>物流产品</span><select defaultValue="特惠普运"><option>特惠普运</option><option>次日达</option></select></label>
          <label className="field"><span>托盘尺寸</span><select defaultValue="auto"><option value="auto">自动选托盘</option><option>1100×1100 木托盘</option><option>1200×1000 木托盘</option></select></label>
          <label className="field"><span>包装方式</span><select defaultValue="auto"><option value="auto">自动判断（推荐）</option><option>小板刀卡隔档包装</option><option>大板 EPE/EPS 成型缓冲包装</option></select></label>
          <p className="field-hint">当前为 GitHub Pages 静态前端预览版。后端 Flask 报价接口稍后接入云服务后，按钮将恢复在线计算。</p>
        </fieldset>

        <button type="button" disabled>生成包装方案（等待后端云服务）</button>
      </section>

      <main className="result-panel">
        <section className="card quote-hero">
          <div className="quote-hero-heading">
            <div>
              <p className="section-eyebrow">推荐报价方案</p>
              <h3>包装 BOM 与托盘运输报价</h3>
            </div>
            <span className="confidence-pill">静态预览</span>
          </div>
          <p className="scheme-summary">前端页面已部署到 GitHub Pages。后端云服务接入后，将实时返回包装 BOM、装箱方案、托盘码垛、成本拆解和运费报价。</p>
          <div className="quote-kpi-grid">
            {kpis.map(([label, value, unit], index) => (
              <div className={`quote-kpi ${index === 0 ? "primary" : ""}`} key={label}>
                <span className="kpi-label">{label}</span>
                <span className="kpi-value">{value}</span>
                {unit && <span className="kpi-unit">{unit}</span>}
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <h3>即将接入能力</h3>
          <table>
            <tbody>
              <tr><td>后端接口</td><td className="num">/api/estimate</td></tr>
              <tr><td>包装 BOM</td><td className="num">纸箱、内衬、防静电袋、托盘辅料</td></tr>
              <tr><td>装箱/码垛</td><td className="num">箱型、每箱数量、每托箱数、层数</td></tr>
              <tr><td>成本与运费</td><td className="num">包材、模具摊销、托盘辅料、跨越运费</td></tr>
            </tbody>
          </table>
        </section>
      </main>
    </div>
  );
}
