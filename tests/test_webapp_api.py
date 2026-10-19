from webapp.api_server import create_app


def _payload():
    return {
        "product": {
            "name": "API-TEST-PCBA",
            "product_class": "pcba",
            "length_mm": 120,
            "width_mm": 85,
            "height_mm": 40,
            "weight_kg": 0.1,
            "fragility": "medium",
            "esd_sensitive": True,
        },
        "business": {"annual_qty": 5000, "design_frozen": True, "allow_mold": True},
        "logistics": {
            "ship_mode": "pallet",
            "origin": "青岛市",
            "destination": "上海市",
            "logistics_product": "特惠普运",
            "pallet_size": "auto",
            "pallet_material": "wood",
            "pallet_reusable": False,
            "pallet_height_mm": 120,
            "max_pallet_height_mm": 1500,
            "max_pallet_weight_kg": 700,
        },
        "constraints": {
            "auto_units_per_box": True,
            "auto_design_carton": True,
            "units_per_box_candidates": [1, 2, 4, 6, 8, 10],
            "max_box_weight_kg": 25,
            "packaging_mode": "auto",
            "carton": {"layers": 5, "flute": "BC", "thickness_mm": 7, "max_load_kg": 35, "stack_safety_factor": 1.5},
            "accessories": {"stretch_film": True, "packing_band": True, "corner_protector": True, "edge_protector": True},
            "cost_overrides": {},
        },
    }


def test_estimate_saves_quote_history_and_detail_can_restore_snapshot():
    client = create_app().test_client()

    response = client.post("/api/estimate", json=_payload())

    assert response.status_code == 200
    envelope = response.get_json()
    assert envelope["code"] == 0
    body = envelope["data"]
    assert body["quote_record_id"] > 0

    history = client.get("/api/quote-history?q=API-TEST-PCBA").get_json()["data"]
    assert history["records"]
    assert history["records"][0]["product_name"] == "API-TEST-PCBA"

    detail = client.get(f"/api/quote-history/{body['quote_record_id']}").get_json()["data"]
    assert detail["request"]["product"]["name"] == "API-TEST-PCBA"
    assert detail["response"]["recommended"]["total_cost_per_unit"] == body["recommended"]["total_cost_per_unit"]


def test_cost_override_fields_returns_config_defaults():
    client = create_app().test_client()

    response = client.get("/api/cost-overrides/fields")

    assert response.status_code == 200
    body = response.get_json()
    assert body["code"] == 0
    fields = body["data"]["fields"]
    by_key = {field["key"]: field for field in fields}
    assert by_key["corrugated_material_yuan_per_m2"]["default"] == 14.35
    assert by_key["pallet_purchase_price"]["default"] == 80
    assert by_key["mold_tooling_cost"]["unit"] == "元"
    assert by_key["mold_amortize_qty"]["unit"] == "台"
    assert by_key["mold_amortize_per_unit"]["default"] == 3.33


def test_health_uses_unified_response_envelope():
    client = create_app().test_client()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"code": 0, "data": {"status": "ok"}, "msg": "ok"}


def test_invalid_quote_history_limit_returns_400_envelope():
    client = create_app().test_client()

    response = client.get("/api/quote-history?limit=abc")

    assert response.status_code == 400
    body = response.get_json()
    assert body["code"] == 400
    assert body["data"] is None
    assert "limit" in body["msg"]


def test_invalid_boolean_type_returns_400_envelope():
    client = create_app().test_client()
    payload = _payload()
    payload["business"]["allow_mold"] = "false"

    response = client.post("/api/estimate", json=payload)

    assert response.status_code == 400
    body = response.get_json()
    assert body["code"] == 400
    assert body["data"] is None
    assert "allow_mold" in body["msg"]


def test_estimate_accepts_origin_and_freight_discount():
    client = create_app().test_client()
    payload = _payload()
    payload["logistics"]["origin"] = "上海市"
    payload["logistics"]["freight_discount"] = 0.9

    response = client.post("/api/estimate", json=payload)

    assert response.status_code == 200
    body = response.get_json()["data"]
    assert body["freight_rate"]["origin"] == "上海市"
    assert body["freight"]["discount"] == 0.9
    assert body["freight"]["freight_total"] == round(body["freight"]["original_freight_total"] * 0.9, 2)


def test_invalid_freight_discount_returns_400_envelope():
    client = create_app().test_client()
    payload = _payload()
    payload["logistics"]["freight_discount"] = 1.2

    response = client.post("/api/estimate", json=payload)

    assert response.status_code == 400
    body = response.get_json()
    assert body["code"] == 400
    assert body["data"] is None
    assert "freight_discount" in body["msg"]


def test_quote_history_correction_records_actuals_without_overwriting_snapshot():
    client = create_app().test_client()
    estimate_response = client.post("/api/estimate", json=_payload())
    quote_id = estimate_response.get_json()["data"]["quote_record_id"]
    original_total = estimate_response.get_json()["data"]["recommended"]["total_cost_per_unit"]

    response = client.post(
        f"/api/quote-history/{quote_id}/correction",
        json={
            "actual_carton_purchase_price": 4.8,
            "actual_packaging_cost_per_unit": 2.35,
            "actual_freight_per_unit": 1.72,
            "variance_reason": "供应商纸价上涨，实际运费按月结账单回填",
        },
    )

    assert response.status_code == 200
    correction = response.get_json()["data"]["correction"]
    assert correction["status"] == "已回填"
    assert correction["actual_carton_purchase_price"] == 4.8
    assert correction["actual_packaging_cost_per_unit"] == 2.35
    assert correction["actual_freight_per_unit"] == 1.72
    assert correction["variance_reason"] == "供应商纸价上涨，实际运费按月结账单回填"
    assert correction["actual_packaging_freight_per_unit"] == 4.07
    assert isinstance(correction["variance_rate"], float)

    detail = client.get(f"/api/quote-history/{quote_id}").get_json()["data"]
    assert detail["correction"]["status"] == "已回填"
    assert detail["response"]["recommended"]["total_cost_per_unit"] == original_total

    history = client.get("/api/quote-history?q=API-TEST-PCBA").get_json()["data"]
    assert history["records"][0]["correction_status"] == "已回填"


def test_quote_history_correction_rejects_negative_actuals():
    client = create_app().test_client()
    estimate_response = client.post("/api/estimate", json=_payload())
    quote_id = estimate_response.get_json()["data"]["quote_record_id"]

    response = client.post(
        f"/api/quote-history/{quote_id}/correction",
        json={
            "actual_packaging_cost_per_unit": -1,
            "actual_freight_per_unit": 1.72,
            "variance_reason": "异常负数",
        },
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["code"] == 400
    assert "actual_packaging_cost_per_unit" in body["msg"]


def test_missing_quote_history_detail_returns_404_envelope():
    client = create_app().test_client()

    response = client.get("/api/quote-history/999999999")

    assert response.status_code == 404
    body = response.get_json()
    assert body["code"] == 404
    assert body["data"] is None
    assert "quote history record" in body["msg"]


def test_404_and_405_use_json_envelope():
    client = create_app().test_client()

    not_found = client.get("/api/not-exists")
    method_not_allowed = client.get("/api/estimate")

    assert not_found.status_code == 404
    assert not_found.get_json()["code"] == 404
    assert method_not_allowed.status_code == 405
    assert method_not_allowed.get_json()["code"] == 405
