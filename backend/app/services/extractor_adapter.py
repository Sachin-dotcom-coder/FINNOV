from __future__ import annotations

import importlib
from typing import Any, Dict, Optional


class ExtractorNotConfigured(Exception):
    pass


def extract(input_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bridge to user-provided extractor.

    Expects a module at app.integrations.extractor with a function:
        def extract(input: dict) -> dict

    input_payload keys may include: text, file_path, url, options
    """
    try:
        module = importlib.import_module("app.integrations.extractor")
    except ModuleNotFoundError as e:
        raise ExtractorNotConfigured(
            "Extractor module not found. Add backend/app/integrations/extractor.py"
        ) from e

    if not hasattr(module, "extract"):
        raise ExtractorNotConfigured(
            "'extract' function missing in app/integrations/extractor.py"
        )

    return module.extract(input_payload)
