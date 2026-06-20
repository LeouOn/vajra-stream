"""
Synchronizes endpoints/__init__.py with api.py router registration.

Catches drift when a new endpoint is added to api.py but the
__init__.py exports are not updated (or vice versa). The
__init__.py is unused for routing but provides `from .endpoints
import X` access for tests and tooling.
"""

import importlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_FILE = PROJECT_ROOT / "backend" / "app" / "api" / "v1" / "api.py"


def _read_api_registrations() -> set[str]:
    """Parse api.py to extract every endpoint module name registered."""
    text = API_FILE.read_text(encoding="utf-8")
    names: set[str] = set()
    for line in text.splitlines():
        if "from .endpoints import" not in line and "from backend.app.api.v1.endpoints import" not in line:
            continue
        # Capture: import X as Y_endpoint
        rest = line.split("import", 1)[1]
        for token in rest.split(" as ")[0].split(","):
            n = token.strip()
            if n:
                names.add(n)
    return names


def test_init_exports_match_api_registrations():
    from backend.app.api.v1.endpoints import __all__ as exports

    registered = _read_api_registrations()

    missing = registered - set(exports)
    extra = set(exports) - registered
    assert not missing, (
        f"endpoints/__init__.py missing exports for: {sorted(missing)}. "
        f"Add them so `from .endpoints import {sorted(missing)[0]}` works."
    )
    assert not extra, (
        f"endpoints/__init__.py has stale exports no longer in api.py: {sorted(extra)}. "
        f"Remove them or re-add the import to api.py."
    )


def test_all_endpoint_modules_importable():
    """Every module in __all__ must be importable without error."""
    from backend.app.api.v1.endpoints import __all__ as exports

    for name in exports:
        mod = importlib.import_module(f"backend.app.api.v1.endpoints.{name}")
        assert hasattr(mod, "router"), f"{name} has no `router` attribute"
