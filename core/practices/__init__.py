"""
core/practices — Practice catalog consumed by core/ engines.

Kept separate from `core/` engines themselves to avoid circular imports
between ritual_engine and the catalog of practices it consumes.

(Named `practices/` rather than `models/` because `.gitignore` excludes
any directory named `models/` anywhere in the tree.)
"""
