async function parseEnvelope(resp) {
  const body = await resp.json();
  if (!resp.ok || body.code !== 0) {
    throw new Error(body.msg || body.error || `HTTP ${resp.status}`);
  }
  return body.data;
}

async function getJson(url) {
  const resp = await fetch(url);
  return parseEnvelope(resp);
}

export async function postEstimate(payload) {
  const resp = await fetch("/api/estimate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseEnvelope(resp);
}

export function fetchQuoteHistory(query = "") {
  const params = new URLSearchParams({ limit: "50" });
  if (query.trim()) params.set("q", query.trim());
  return getJson(`/api/quote-history?${params}`);
}

export function fetchQuoteHistoryDetail(id) {
  return getJson(`/api/quote-history/${id}`);
}

export async function postQuoteCorrection(id, payload) {
  const resp = await fetch(`/api/quote-history/${id}/correction`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseEnvelope(resp);
}

export function fetchCostOverrideFields() {
  return getJson("/api/cost-overrides/fields");
}
