import { useState } from "react";
import InputForm, { DEFAULT_FORM } from "./components/InputForm.jsx";
import ResultPanel from "./components/ResultPanel.jsx";
import QuoteHistoryPanel from "./components/QuoteHistoryPanel.jsx";
import CostConfigPanel from "./components/CostConfigPanel.jsx";
import { postEstimate } from "./api.js";
import "./styles.css";

export default function App() {
  const [form, setForm] = useState(DEFAULT_FORM);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [historyRefreshToken, setHistoryRefreshToken] = useState(0);

  const handleSubmit = async (payload) => {
    setSubmitting(true);
    setError(null);
    try {
      const data = await postEstimate(payload);
      setResult(data);
      setHistoryRefreshToken((token) => token + 1);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="app-layout">
      <header className="app-header">
        <h1>PCBA 包装方案模拟与成本预估系统</h1>
      </header>
      <div className="left-column">
        <InputForm form={form} setForm={setForm} onSubmit={handleSubmit} submitting={submitting} />
        <CostConfigPanel form={form} />
      </div>
      <div className="right-column">
        <ResultPanel result={result} error={error} />
        <QuoteHistoryPanel refreshToken={historyRefreshToken} onRestoreResult={setResult} />
      </div>
    </div>
  );
}
