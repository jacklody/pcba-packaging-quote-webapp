import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import current_app, has_app_context

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "quote_history.sqlite3"


def _db_path() -> Path:
    if has_app_context():
        return Path(current_app.config.get("QUOTE_HISTORY_DB", DEFAULT_DB_PATH))
    return DEFAULT_DB_PATH


def _connect() -> sqlite3.Connection:
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS quote_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            product_name TEXT NOT NULL,
            product_size TEXT NOT NULL,
            destination TEXT NOT NULL,
            logistics_product TEXT NOT NULL,
            total_cost_per_unit REAL,
            units_per_box INTEGER,
            units_per_pallet INTEGER,
            confidence TEXT,
            request_json TEXT NOT NULL,
            response_json TEXT NOT NULL
        )
        """
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(quote_history)").fetchall()}
    if "correction_json" not in columns:
        conn.execute("ALTER TABLE quote_history ADD COLUMN correction_json TEXT")
    conn.commit()
    return conn


def _empty_correction() -> dict[str, Any]:
    return {"status": "未回填"}


def _build_correction(row: sqlite3.Row, actuals: dict[str, Any]) -> dict[str, Any]:
    response = json.loads(row["response_json"])
    estimated = response.get("recommended", {}).get("total_cost_per_unit")
    actual_packaging = actuals.get("actual_packaging_cost_per_unit")
    actual_freight = actuals.get("actual_freight_per_unit")
    actual_total = round(float(actual_packaging or 0) + float(actual_freight or 0), 2)
    variance = round(actual_total - float(estimated), 2) if estimated is not None else None
    variance_rate = round(variance / float(estimated), 4) if estimated else None
    return {
        "status": "已回填",
        "actual_carton_purchase_price": actuals.get("actual_carton_purchase_price"),
        "actual_packaging_cost_per_unit": actual_packaging,
        "actual_freight_per_unit": actual_freight,
        "actual_packaging_freight_per_unit": actual_total,
        "estimated_total_cost_per_unit": estimated,
        "variance_per_unit": variance,
        "variance_rate": variance_rate,
        "variance_reason": actuals.get("variance_reason", ""),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def save_quote(payload: dict[str, Any], result: dict[str, Any]) -> int:
    product = payload.get("product", {})
    logistics = payload.get("logistics", {})
    recommended = result.get("recommended", {})
    product_size = "{}×{}×{} mm / {} kg".format(
        product.get("length_mm", "-"),
        product.get("width_mm", "-"),
        product.get("height_mm", "-"),
        product.get("weight_kg", "-"),
    )
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO quote_history (
                created_at, product_name, product_size, destination, logistics_product,
                total_cost_per_unit, units_per_box, units_per_pallet, confidence,
                request_json, response_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                str(product.get("name", "未命名产品")),
                product_size,
                str(logistics.get("destination", "")),
                str(logistics.get("logistics_product", "")),
                recommended.get("total_cost_per_unit"),
                recommended.get("units_per_box"),
                recommended.get("units_per_pallet"),
                recommended.get("confidence"),
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                json.dumps(result, ensure_ascii=False, separators=(",", ":")),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_quotes(limit: int = 50, query: str = "") -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    params: list[Any] = []
    where = ""
    if query:
        like = f"%{query}%"
        where = "WHERE product_name LIKE ? OR destination LIKE ? OR logistics_product LIKE ? OR product_size LIKE ?"
        params.extend([like, like, like, like])
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT id, created_at, product_name, product_size, destination, logistics_product,
                   total_cost_per_unit, units_per_box, units_per_pallet, confidence,
                   CASE WHEN correction_json IS NULL OR correction_json = '' THEN '未回填' ELSE '已回填' END AS correction_status
            FROM quote_history
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
    return [dict(row) for row in rows]


def get_quote(quote_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM quote_history WHERE id = ?", (quote_id,)).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["request"] = json.loads(data.pop("request_json"))
    data["response"] = json.loads(data.pop("response_json"))
    correction_json = data.pop("correction_json", None)
    data["correction"] = json.loads(correction_json) if correction_json else _empty_correction()
    return data


def save_quote_correction(quote_id: int, actuals: dict[str, Any]) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM quote_history WHERE id = ?", (quote_id,)).fetchone()
        if row is None:
            return None
        correction = _build_correction(row, actuals)
        conn.execute(
            "UPDATE quote_history SET correction_json = ? WHERE id = ?",
            (json.dumps(correction, ensure_ascii=False, separators=(",", ":")), quote_id),
        )
        conn.commit()
    return correction
