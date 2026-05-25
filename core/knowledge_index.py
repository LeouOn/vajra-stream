"""
Knowledge Index
Lightweight RAG (Retrieval-Augmented Generation) pipeline for the Vajra.Stream
knowledge base. No external vector database needed — uses numpy cosine similarity.

Indexes all knowledge/ JSON files into searchable chunks so the LLM can query
frequencies, mantras, rates, chakras, and healing correspondences at runtime.
"""

import json
from pathlib import Path
from typing import Any

import numpy as np

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


def _simple_embed(text: str, dim: int = 256) -> np.ndarray:
    """
    Simple character-ngram embedding for lightweight similarity search.

    Uses overlapping character trigrams hashed into a fixed-dimension vector.
    This is deterministic, fast, and requires no external dependencies.
    Works well for keyword/concept matching in a domain-specific knowledge base.
    """
    vec = np.zeros(dim, dtype=np.float32)
    text = text.lower()
    # Character trigrams
    for i in range(len(text) - 2):
        trigram = text[i : i + 3]
        h = hash(trigram) % dim
        vec[h] += 1.0
    # Character bigrams
    for i in range(len(text) - 1):
        bigram = text[i : i + 2]
        h = hash(bigram) % dim
        vec[h] += 0.5
    # Normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    return float(np.dot(a, b))


class KnowledgeChunk:
    """A searchable chunk of knowledge."""

    def __init__(self, text: str, source: str, category: str, metadata: dict[str, Any] | None = None):
        self.text = text
        self.source = source
        self.category = category
        self.metadata = metadata or {}
        self.embedding: np.ndarray | None = None

    def embed(self):
        """Compute and cache the embedding vector."""
        self.embedding = _simple_embed(self.text)
        return self.embedding

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "category": self.category,
            "metadata": self.metadata,
        }


class KnowledgeIndex:
    """
    Lightweight RAG index over the Vajra.Stream knowledge base.

    Usage:
        idx = KnowledgeIndex()
        idx.build()
        results = idx.search("liver detox", top_k=5)
    """

    def __init__(self, knowledge_dir: Path | None = None):
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        self.chunks: list[KnowledgeChunk] = []
        self._built = False

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> int:
        """Build the index from all knowledge files. Returns chunk count."""
        self.chunks = []

        # Frequencies
        self._index_json("frequencies.json", "frequency", self._chunk_frequencies)

        # Mantras
        self._index_json("mantras.json", "mantra", self._chunk_mantras)

        # Radionics rates
        for rate_file in (self.knowledge_dir / "radionics_rates").glob("*.json"):
            self._index_json(
                f"radionics_rates/{rate_file.name}",
                "rate",
                self._chunk_rates,
            )

        # Healing knowledge
        self._index_json("healing_knowledge.json", "healing", self._chunk_healing)

        # Historical events
        self._index_json("historical_suffering_events.json", "history", self._chunk_events)

        # Embed all chunks
        for chunk in self.chunks:
            chunk.embed()

        self._built = True
        return len(self.chunks)

    def _index_json(self, rel_path: str, category: str, chunker):
        """Load a JSON knowledge file and chunk it."""
        path = self.knowledge_dir / rel_path
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        for chunk in chunker(data, rel_path, category):
            self.chunks.append(chunk)

    # ------------------------------------------------------------------
    # Chunkers
    # ------------------------------------------------------------------

    def _chunk_frequencies(self, data: dict, source: str, category: str) -> list[KnowledgeChunk]:
        chunks = []
        for freq_type, entries in data.items():
            if not isinstance(entries, dict):
                continue
            for hz, info in entries.items():
                if isinstance(info, dict):
                    text = f"{freq_type} frequency {hz} Hz: {info.get('name', '')} — {info.get('purpose', '')}. Chakra: {info.get('chakra', '')}. Planet: {info.get('planet', '')}. State: {info.get('state', '')}."
                    chunks.append(KnowledgeChunk(text, source, category, {"hz": hz, "type": freq_type, **info}))
        return chunks

    def _chunk_mantras(self, data: dict, source: str, category: str) -> list[KnowledgeChunk]:
        chunks = []
        for tradition, mantras in data.items():
            if tradition == "aspirations" or not isinstance(mantras, dict):
                continue
            for key, info in mantras.items():
                if isinstance(info, dict):
                    text = f"Mantra from {tradition}: {info.get('name', key)} — {info.get('meaning', '')}. Purpose: {info.get('purpose', '')}. Chakra: {info.get('chakra', '')}."
                    chunks.append(KnowledgeChunk(text, source, category, {"tradition": tradition, "key": key, **info}))
        return chunks

    def _chunk_rates(self, data: dict, source: str, category: str) -> list[KnowledgeChunk]:
        chunks = []
        entries = data if isinstance(data, list) else list(data.values()) if isinstance(data, dict) else []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name", entry.get("id", ""))
            values = entry.get("values", entry.get("rate", ""))
            desc = entry.get("description", entry.get("condition", ""))
            text = f"Radionics rate: {name} — values {values}. {desc}"
            chunks.append(KnowledgeChunk(text, source, category, entry))
        return chunks

    def _chunk_healing(self, data: dict, source: str, category: str) -> list[KnowledgeChunk]:
        chunks = []
        if isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, dict):
                    text = f"Healing: {key} — {json.dumps(val)}"
                    chunks.append(KnowledgeChunk(text, source, category, {"key": key, **val}))
                elif isinstance(val, list):
                    text = f"Healing: {key} — {', '.join(str(v) for v in val)}"
                    chunks.append(KnowledgeChunk(text, source, category, {"key": key}))
        return chunks

    def _chunk_events(self, data: dict, source: str, category: str) -> list[KnowledgeChunk]:
        chunks = []
        entries = data if isinstance(data, list) else list(data.values()) if isinstance(data, dict) else []
        for entry in entries:
            if isinstance(entry, dict):
                name = entry.get("name", entry.get("event", ""))
                desc = entry.get("description", "")
                text = f"Historical event: {name}. {desc}"
                chunks.append(KnowledgeChunk(text, source, category, entry))
        return chunks

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 5, category: str | None = None) -> list[dict[str, Any]]:
        """
        Search the knowledge base for chunks relevant to the query.

        Args:
            query: Natural language query
            top_k: Number of results to return
            category: Optional category filter (frequency, mantra, rate, healing, history)

        Returns:
            List of matching chunks with similarity scores
        """
        if not self._built:
            self.build()

        query_vec = _simple_embed(query)

        scored = []
        for chunk in self.chunks:
            if category and chunk.category != category:
                continue
            if chunk.embedding is None:
                chunk.embed()
            score = _cosine_similarity(query_vec, chunk.embedding)
            scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "score": round(float(score), 4),
                "text": chunk.text,
                "source": chunk.source,
                "category": chunk.category,
                "metadata": chunk.metadata,
            }
            for score, chunk in scored[:top_k]
            if score > 0.05  # Minimum relevance threshold
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get index statistics."""
        cats = {}
        for chunk in self.chunks:
            cats[chunk.category] = cats.get(chunk.category, 0) + 1
        return {
            "total_chunks": len(self.chunks),
            "categories": cats,
            "built": self._built,
        }


# Singleton
_knowledge_index: KnowledgeIndex | None = None


def get_knowledge_index() -> KnowledgeIndex:
    """Get or build the global knowledge index."""
    global _knowledge_index
    if _knowledge_index is None:
        _knowledge_index = KnowledgeIndex()
        _knowledge_index.build()
    return _knowledge_index


def search_knowledge(query: str, top_k: int = 5, category: str | None = None) -> list[dict[str, Any]]:
    """Convenience function: search the knowledge base."""
    return get_knowledge_index().search(query, top_k, category)
