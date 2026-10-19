from flask import jsonify


def ok(data=None, msg: str = "ok", status_code: int = 200):
    return jsonify({"code": 0, "data": data, "msg": msg}), status_code


def fail(code: int, msg: str, status_code: int | None = None):
    return jsonify({"code": code, "data": None, "msg": msg}), status_code or code
