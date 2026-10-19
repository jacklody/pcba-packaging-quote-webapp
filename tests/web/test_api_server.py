import pytest

from webapp.api_server import create_app


VALID_PAYLOAD = {
    "product": {
        "name": "DRV-26P",
        "product_class": "assembly",
        "length_mm": 620,
        "width_mm": 360,
        "height_mm": 95,
        "weight_kg": 9.8,
        "fragility": "medium",
        "esd_sensitive": True,
    },
    "business": {"annual_qty": 5000, "design_frozen": True, "allow_mold": True},
    "logistics": {
        "ship_mode": "pallet",
        "destination": "深圳市",
        "logistics_product": "特惠普运",
        "pallet_size": "1100x1100",
        "max_pallet_height_mm": 1500,
        "max_pallet_weight_kg": 700,
    },
    "constraints": {"units_per_box_candidates": [1, 2, 4, 6], "max_box_weight_kg": 25},
}

EXTENDED_OPTIONS = {
    "logistics": {
        "origin": "青岛市",
        "destination": "深圳市",
        "logistics_product": "次日达",
        "pallet_size": "1200x1000",
        "pallet_material": "wood",
        "pallet_reusable": False,
        "pallet_height_mm": 140,
        "max_pallet_height_mm": 1500,
        "max_pallet_weight_kg": 900,
        "supported_logistics_products": ["特惠普运", "次日达"],
        "available_destinations": ["深圳市", "上海市"],
    },
    "constraints": {
        "auto_units_per_box": True,
        "override_units_per_box": 2,
        "units_per_box_candidates": [1, 2, 4],
        "max_box_weight_kg": 25,
        "carton": {
            "layers": 5,
            "flute": "BC",
            "thickness_mm": 7,
            "max_load_kg": 35,
            "stack_safety_factor": 1.5,
        },
        "accessories": {
            "stretch_film": True,
            "packing_band": True,
            "corner_protector": True,
            "edge_protector": True,
        },
    },
}


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _post_json(client, payload):
    return client.post("/api/estimate", json=payload)


def _data(resp):
    body = resp.get_json()
    assert body["code"] == 0
    return body["data"]


def _msg(resp):
    body = resp.get_json()
    return body["msg"]


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert _data(resp)["status"] == "ok"


def test_estimate_returns_standard_json(client):
    resp = _post_json(client, VALID_PAYLOAD)

    assert resp.status_code == 200
    body = _data(resp)
    assert set(body) >= {"recommended", "cost", "bom", "risks", "alternatives", "geometry"}
    assert body["recommended"]["summary"].startswith("EPS成型缓冲")
    assert body["recommended"]["units_per_box"] in VALID_PAYLOAD["constraints"]["units_per_box_candidates"]
    assert body["recommended"]["total_cost_per_unit"] > 0
    assert body["cost"]["freight_per_unit"] > 0
    assert body["bom"] and "confidence" in body["bom"][0]
    assert body["geometry"]["box_view"]["outer_box"]["l"] > 0
    assert body["geometry"]["pallet_view"]["total_height_mm"] <= 1500


def test_invalid_product_class_returns_400(client):
    payload = {**VALID_PAYLOAD, "product": {**VALID_PAYLOAD["product"], "product_class": "xyz"}}

    resp = _post_json(client, payload)

    assert resp.status_code == 400
    assert "product_class" in _msg(resp)


def test_non_positive_dimension_returns_400(client):
    payload = {**VALID_PAYLOAD, "product": {**VALID_PAYLOAD["product"], "length_mm": 0}}

    resp = _post_json(client, payload)

    assert resp.status_code == 400
    assert resp.get_json()["code"] == 400


def test_missing_field_returns_400(client):
    payload = {**VALID_PAYLOAD, "business": {"annual_qty": 5000, "design_frozen": True}}

    resp = _post_json(client, payload)

    assert resp.status_code == 400
    assert resp.get_json()["code"] == 400


def test_no_feasible_candidate_returns_400(client):
    payload = {**VALID_PAYLOAD, "constraints": {"units_per_box_candidates": [1], "max_box_weight_kg": 1.0}}

    resp = _post_json(client, payload)

    assert resp.status_code == 400
    assert "no feasible" in _msg(resp)


def test_non_json_body_returns_400(client):
    resp = client.post("/api/estimate", data="not json", content_type="application/json")

    assert resp.status_code == 400
    assert resp.get_json()["code"] == 400


def test_estimate_accepts_extended_frontend_options(client):
    payload = {
        **VALID_PAYLOAD,
        "logistics": {**VALID_PAYLOAD["logistics"], **EXTENDED_OPTIONS["logistics"]},
        "constraints": EXTENDED_OPTIONS["constraints"],
    }

    resp = _post_json(client, payload)

    assert resp.status_code == 200
    body = _data(resp)
    assert body["recommended"]["units_per_box"] in [1, 2, 4]
    assert body["geometry"]["pallet_view"]["pallet"]["h"] > 0
