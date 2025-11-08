from __future__ import annotations

import importlib
from typing import Any, Dict, Optional


class LogicNotConfigured(Exception):
    pass


def analyze(extracted: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Bridge to user-provided business logic.

    Expects a module at app.integrations.logic with a function:
        def analyze(extracted: dict, options: dict | None = None) -> dict
    """
    try:
        module = importlib.import_module("app.integrations.logic")
    except ModuleNotFoundError as e:
        raise LogicNotConfigured(
            "Logic module not found. Add backend/app/integrations/logic.py"
        ) from e

    if not hasattr(module, "analyze"):
        raise LogicNotConfigured("'analyze' function missing in app/integrations/logic.py")

    return module.analyze(extracted, options)
