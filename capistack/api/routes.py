# capistack/api/routes.py
from flask import Blueprint, jsonify, request

api_bp = Blueprint("api", __name__)

@api_bp.get("/refs/branches")
def list_branches():
    # TODO: call your provider or git ls-remote
    return jsonify(["main", "testing"])

@api_bp.get("/refs/tags")
def list_tags():
    return jsonify(["v1.0.0"])

@api_bp.post("/deploy")
def api_start_deploy():
    data = request.get_json() or {}
    # TODO: enqueue deployment job with data["ref_type"], data["ref_name"]
    return jsonify({"status": "queued"}), 202
