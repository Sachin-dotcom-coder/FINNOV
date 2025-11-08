from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from .services.extractor_adapter import ExtractorNotConfigured, extract as run_extract
from .services.logic_adapter import LogicNotConfigured, analyze as run_analyze

bp = Blueprint("api", __name__)


def _allowed_file(filename: str) -> bool:
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", set())
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


@bp.get("/health")
def health() -> Any:
    return jsonify({
        "status": "ok",
        "time": datetime.utcnow().isoformat() + "Z",
        "debug": bool(current_app.config.get("DEBUG", False)),
    })


@bp.post("/extract")
def extract_endpoint() -> Any:
    try:
        payload: Dict[str, Any] = {}
        if request.content_type and request.content_type.startswith("multipart/form-data"):
            if "file" not in request.files:
                return jsonify({"error": "file field missing"}), 400
            file = request.files["file"]
            if file.filename == "":
                return jsonify({"error": "empty filename"}), 400
            if not _allowed_file(file.filename):
                return jsonify({"error": "file type not allowed"}), 400

            upload_dir = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)
            filename = secure_filename(file.filename)
            save_path = os.path.join(upload_dir, filename)
            file.save(save_path)
            payload["file_path"] = save_path
            # optional JSON options in a separate field
            if request.form.get("options"):
                try:
                    import json as _json
                    payload["options"] = _json.loads(request.form["options"])
                except Exception:
                    return jsonify({"error": "options must be valid JSON"}), 400
        else:
            data = request.get_json(silent=True) or {}
            if not any(k in data for k in ("text", "url", "file_path")):
                return jsonify({"error": "provide one of: text, url, file_path"}), 400
            payload.update({k: v for k, v in data.items() if k in ("text", "url", "file_path", "options")})

        extracted = run_extract(payload)
        return jsonify({"extracted": extracted}), 200
    except ExtractorNotConfigured as e:
        return jsonify({"error": str(e)}), 501
    except Exception as e:  # pragma: no cover
        current_app.logger.exception("/extract failed")
        return jsonify({"error": "internal_error", "detail": str(e)}), 500


@bp.post("/analyze")
def analyze_endpoint() -> Any:
    try:
        data = request.get_json(force=True)
        if "extracted" not in data:
            return jsonify({"error": "missing 'extracted' in body"}), 400
        options = data.get("options")
        result = run_analyze(data["extracted"], options)
        return jsonify({"result": result}), 200
    except LogicNotConfigured as e:
        return jsonify({"error": str(e)}), 501
    except Exception as e:  # pragma: no cover
        current_app.logger.exception("/analyze failed")
        return jsonify({"error": "internal_error", "detail": str(e)}), 500


@bp.post("/process")
def process_endpoint() -> Any:
    try:
        # Reuse extract handler logic for payload shaping
        if request.content_type and request.content_type.startswith("multipart/form-data"):
            # create a fake request dict like extract_endpoint does
            if "file" not in request.files:
                return jsonify({"error": "file field missing"}), 400
            file = request.files["file"]
            if file.filename == "":
                return jsonify({"error": "empty filename"}), 400
            if not _allowed_file(file.filename):
                return jsonify({"error": "file type not allowed"}), 400
            upload_dir = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)
            filename = secure_filename(file.filename)
            save_path = os.path.join(upload_dir, filename)
            file.save(save_path)
            payload = {"file_path": save_path}
            if request.form.get("options"):
                try:
                    import json as _json
                    payload["options"] = _json.loads(request.form["options"])
                except Exception:
                    return jsonify({"error": "options must be valid JSON"}), 400
            return_intermediate = request.form.get("return_intermediate", "false").lower() == "true"
        else:
            data = request.get_json(force=True)
            payload = {k: v for k, v in data.items() if k in ("text", "url", "file_path", "options")}
            if not any(k in payload for k in ("text", "url", "file_path")):
                return jsonify({"error": "provide one of: text, url, file_path"}), 400
            return_intermediate = bool(data.get("return_intermediate", False))

        extracted = run_extract(payload)
        result = run_analyze(extracted, payload.get("options"))
        out: Dict[str, Any] = {"result": result}
        if return_intermediate:
            out["extracted"] = extracted
        return jsonify(out), 200
    except (ExtractorNotConfigured, LogicNotConfigured) as e:
        return jsonify({"error": str(e)}), 501
    except Exception as e:  # pragma: no cover
        current_app.logger.exception("/process failed")
        return jsonify({"error": "internal_error", "detail": str(e)}), 500
