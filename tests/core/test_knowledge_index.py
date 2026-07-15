"""
Smoke + behaviour tests for ``core.knowledge_index``.

Covers the public surface:
- :class:`KnowledgeChunk` — text/source/category/metadata + ``to_dict`` and ``embed``.
- :class:`KnowledgeIndex` — ``build`` returns int chunk count; ``get_stats``
  reports categories; ``search`` returns scored dicts above the relevance
  threshold; ``search`` triggers lazy ``build`` when not yet built.
- Module-level convenience: :func:`get_knowledge_index` returns a singleton.

The default ``knowledge_dir`` points at the real ``knowledge/`` tree in
the project — these tests use the real JSON files to exercise the indexing
pipeline end-to-end (no I/O mocking required).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from core.knowledge_index import (
    KnowledgeChunk,
    KnowledgeIndex,
    get_knowledge_index,
    search_knowledge,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def real_knowledge_dir() -> Path:
    """Return the real ``knowledge/`` directory if it exists, else skip."""
    from core.knowledge_index import KNOWLEDGE_DIR

    if not KNOWLEDGE_DIR.exists():
        pytest.skip("knowledge/ directory not present in this environment")
    return KNOWLEDGE_DIR


# ---------------------------------------------------------------------------
# 1. Import smoke
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """Module imports cleanly; KnowledgeChunk, KnowledgeIndex, helpers exposed."""
    import core.knowledge_index as mod

    for name in (
        "KnowledgeChunk",
        "KnowledgeIndex",
        "get_knowledge_index",
        "search_knowledge",
    ):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. KnowledgeChunk — construction, embed, to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_knowledge_chunk_stores_text_and_metadata_and_to_dict():
    """KnowledgeChunk holds text/source/category/metadata and serialises cleanly."""
    chunk = KnowledgeChunk(
        text="Liver detox via 528 Hz",
        source="healing_knowledge.json",
        category="healing",
        metadata={"key": "liver"},
    )

    assert chunk.text == "Liver detox via 528 Hz"
    assert chunk.source == "healing_knowledge.json"
    assert chunk.category == "healing"
    assert chunk.metadata == {"key": "liver"}
    # No embedding until ``embed()`` is called
    assert chunk.embedding is None

    out = chunk.to_dict()
    assert out["text"] == chunk.text
    assert out["source"] == chunk.source
    assert out["category"] == chunk.category
    assert out["metadata"] == chunk.metadata


@pytest.mark.unit
def test_knowledge_chunk_embed_caches_unit_normalised_vector():
    """``embed()`` computes a fixed-dim float32 vector and normalises it."""
    chunk = KnowledgeChunk(text="hello world", source="x", category="y")
    vec = chunk.embed()

    assert isinstance(vec, np.ndarray)
    assert vec.dtype == np.float32
    assert vec.shape == (256,)
    # Same instance cached
    assert chunk.embedding is vec
    # Normalised (or zero if text is too short to have trigrams)
    norm = float(np.linalg.norm(chunk.embedding))
    assert 0.0 <= norm <= 1.0 + 1e-6


# ---------------------------------------------------------------------------
# 3. KnowledgeIndex.build() returns chunk count and embeds all chunks
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_knowledge_index_build_returns_chunk_count(real_knowledge_dir):
    """``build()`` indexes all JSON files and returns a positive chunk count."""
    idx = KnowledgeIndex(knowledge_dir=real_knowledge_dir)
    count = idx.build()

    assert isinstance(count, int)
    assert count > 0
    assert len(idx.chunks) == count
    # All chunks have been embedded
    for chunk in idx.chunks:
        assert chunk.embedding is not None
        assert chunk.embedding.shape == (256,)


# ---------------------------------------------------------------------------
# 4. get_stats() reports categories and built flag
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_knowledge_index_get_stats_after_build(real_knowledge_dir):
    """``get_stats()`` returns total_chunks, per-category counts, and built=True."""
    idx = KnowledgeIndex(knowledge_dir=real_knowledge_dir)
    idx.build()
    stats = idx.get_stats()

    assert stats["built"] is True
    assert stats["total_chunks"] == len(idx.chunks)
    # At least one known category is present
    cats = stats["categories"]
    assert isinstance(cats, dict)
    assert sum(cats.values()) == stats["total_chunks"]


# ---------------------------------------------------------------------------
# 5. search() returns scored dicts and triggers lazy build
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_knowledge_index_search_lazy_build(real_knowledge_dir):
    """``search()`` triggers ``build()`` if the index is not yet built, returns scored dicts."""
    idx = KnowledgeIndex(knowledge_dir=real_knowledge_dir)
    assert idx._built is False

    results = idx.search("healing", top_k=3)
    assert idx._built is True  # build was triggered

    assert isinstance(results, list)
    for r in results:
        assert set(r.keys()) >= {"score", "text", "source", "category", "metadata"}
        assert isinstance(r["score"], float)
        assert 0.0 < r["score"] <= 1.0 + 1e-6


@pytest.mark.unit
def test_knowledge_index_search_with_category_filter(real_knowledge_dir):
    """``search(category='frequency')`` returns only chunks in that category."""
    idx = KnowledgeIndex(knowledge_dir=real_knowledge_dir)
    idx.build()

    results = idx.search("frequency 528", top_k=10, category="frequency")
    # All returned chunks must match the category filter
    for r in results:
        assert r["category"] == "frequency"


# ---------------------------------------------------------------------------
# 6. Module-level convenience — singleton + search helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_knowledge_index_returns_singleton(real_knowledge_dir):
    """``get_knowledge_index`` returns the same instance on repeated calls."""
    a = get_knowledge_index()
    b = get_knowledge_index()
    assert a is b
    assert a._built is True  # first call built the index


@pytest.mark.unit
def test_search_knowledge_helper_returns_list(real_knowledge_dir):
    """``search_knowledge(query)`` is a thin wrapper and returns a list of result dicts."""
    results = search_knowledge("compassion mantra", top_k=2)
    assert isinstance(results, list)
    for r in results:
        assert "text" in r
        assert "score" in r
