"""
Backend core package (services, LLM agent, orchestrator bridge).

Subpackages are imported explicitly by their consumers; this ``__init__`` does
not import them eagerly, so importing one leaf service (e.g.
``backend.core.services.location_manager``) does not drag in
``vajra_service`` and its whole engine stack (Phase 3 layering).
"""
