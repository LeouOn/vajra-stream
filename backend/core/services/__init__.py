"""
Core services package.

Import services by their module path (``from backend.core.services.vajra_service
import vajra_service``). Nothing is imported eagerly here: a leaf service must be
importable without constructing the ``VajraStreamService`` singleton (Phase 3
layering).
"""
