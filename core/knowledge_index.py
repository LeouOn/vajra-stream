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
        for rate_file in sorted((self.knowledge_dir / "radionics_rates").glob("*.json")):
            self._index_json(
                f"radionics_rates/{rate_file.name}",
                "rate",
                self._chunk_rates,
            )

        # Healing knowledge
        self._index_json("healing_knowledge.json", "healing", self._chunk_healing)

        # Historical events
        self._index_json("historical_suffering_events.json", "history", self._chunk_events)

        # Tarot deck (one chunk per card)
        self._index_json("tarot_deck.json", "tarot", self._chunk_tarot)

        # Sacred entities (buddhas, yidams, sutras, taras)
        self._index_json("sacred_entities.json", "sacred_entity", self._chunk_sacred_entities)

        # Dharanis
        self._index_json("dharanis.json", "dharani", self._chunk_dharanis)

        # 88 Buddhas
        self._index_json("eighty_eight_buddhas.json", "buddha_88", self._chunk_88_buddhas)

        # Practice definitions (one JSON per practice)
        for practice_file in sorted((self.knowledge_dir / "practices").glob("*.json")):
            self._index_json(
                f"practices/{practice_file.name}",
                "practice",
                self._chunk_practice,
            )

        # Example stories (markdown)
        for story_file in sorted((self.knowledge_dir / "example_stories").glob("*.md")):
            rel = f"example_stories/{story_file.name}"
            path = self.knowledge_dir / rel
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for chunk in self._chunk_markdown(text, rel, "story"):
                self.chunks.append(chunk)

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

    def _chunk_tarot(self, data: dict, source: str, category: str) -> list[KnowledgeChunk]:
        chunks = []
        cards = data.get("cards", []) if isinstance(data, dict) else []
        for card in cards:
            if not isinstance(card, dict):
                continue
            name = card.get("name", "")
            arcana = card.get("arcana", "")
            keywords = card.get("keywords", [])
            keywords_str = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)
            text = (
                f"Tarot card: {name} ({arcana} arcana, number {card.get('number', '')}). "
                f"Element: {card.get('element', '')}. Ruler: {card.get('ruler', '')}. "
                f"Zodiac: {card.get('zodiac', '')}. "
                f"Keywords: {keywords_str}. "
                f"Upright meaning: {card.get('upright', '')}. "
                f"Reversed meaning: {card.get('reversed', '')}. "
                f"Description: {card.get('desc', '')}."
            )
            meta = {k: v for k, v in card.items() if k not in ("upright", "reversed", "desc")}
            chunks.append(KnowledgeChunk(text, source, category, meta))
        return chunks

    def _chunk_sacred_entities(self, data: dict, source: str, category: str) -> list[KnowledgeChunk]:
        chunks = []
        if not isinstance(data, dict):
            return chunks
        for group_name, group_val in data.items():
            if isinstance(group_val, list):
                for entry in group_val:
                    if not isinstance(entry, dict):
                        continue
                    name = entry.get("name", entry.get("id", ""))
                    desc = entry.get("description", entry.get("qualities", ""))
                    mantra = entry.get("dharani_mantra", entry.get("mantra", ""))
                    purpose = entry.get("purpose", "")
                    parts = [f"Sacred entity [{group_name}]: {name}."]
                    if desc:
                        parts.append(desc)
                    if mantra:
                        parts.append(f"Mantra: {mantra}")
                    if purpose:
                        parts.append(f"Purpose: {purpose}")
                    if entry.get("element"):
                        parts.append(f"Element: {entry['element']}")
                    text = " ".join(parts)
                    chunks.append(KnowledgeChunk(text, source, category, {"group": group_name, **entry}))
            elif isinstance(group_val, dict):
                desc = group_val.get("description", "")
                figures = group_val.get("key_figures", [])
                themes = group_val.get("themes", [])
                figures_str = (
                    ", ".join(
                        f if isinstance(f, str) else f"{f.get('name', '')} ({f.get('role', '')})" for f in figures
                    )
                    if figures
                    else ""
                )
                themes_str = ", ".join(str(t) for t in themes) if themes else ""
                text = f"Sacred text [{group_name}]: {desc}"
                if figures_str:
                    text += f" Key figures: {figures_str}."
                if themes_str:
                    text += f" Themes: {themes_str}."
                chunks.append(KnowledgeChunk(text, source, category, {"group": group_name, **group_val}))
        return chunks

    def _chunk_dharanis(self, data, source: str, category: str) -> list[KnowledgeChunk]:
        chunks = []
        entries = data if isinstance(data, list) else list(data.values()) if isinstance(data, dict) else []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name", entry.get("id", ""))
            deity = entry.get("deity", "")
            purpose = entry.get("purpose", "")
            text = (
                f"Dharani: {name}. Deity: {deity}. Tradition: {entry.get('tradition', '')}. "
                f"Purpose: {purpose}. Recommended times: {entry.get('times', '')}. "
                f"Frequency: {entry.get('frequency_hz', '')} Hz. Chakra: {entry.get('chakra', '')}."
            )
            meta = {k: v for k, v in entry.items() if not k.startswith("text_")}
            chunks.append(KnowledgeChunk(text, source, category, meta))
        return chunks

    def _chunk_88_buddhas(self, data, source: str, category: str) -> list[KnowledgeChunk]:
        chunks = []
        entries = data if isinstance(data, list) else list(data.values()) if isinstance(data, dict) else []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            translation = entry.get("translation", "")
            meaning = entry.get("meaning", "")
            text = (
                f"88 Buddhas confession: {translation}. "
                f"Sanskrit: {entry.get('sanskrit', '')}. "
                f"Pinyin: {entry.get('pinyin', '')}. "
                f"Meaning: {meaning}. "
                f"Quality: {entry.get('quality', '')}. Element: {entry.get('element', '')}. "
                f"Chakra: {entry.get('chakra', '')}."
            )
            chunks.append(KnowledgeChunk(text, source, category, entry))
        return chunks

    def _chunk_practice(self, data: dict, source: str, category: str) -> list[KnowledgeChunk]:
        chunks = []
        if not isinstance(data, dict):
            return chunks
        name = data.get("name", data.get("practice_id", ""))
        tradition = data.get("tradition", "")
        cat = data.get("category", "")
        purpose = data.get("primary_purpose", "")
        benefits = data.get("benefits", [])
        benefits_str = "; ".join(benefits) if isinstance(benefits, list) else str(benefits)
        visualizations = data.get("visualizations", [])
        vis_str = " ".join(visualizations) if isinstance(visualizations, list) else ""
        text = (
            f"Practice: {name} ({tradition}, category: {cat}). "
            f"Purpose: {purpose}. "
            f"Frequency: {data.get('frequency_hz', '')} Hz ({data.get('frequency_purpose', '')}). "
            f"Color: {data.get('color_name', data.get('color', ''))}. "
            f"Element: {data.get('element', '')}. Chakra: {data.get('chakra', '')}. "
            f"Benefits: {benefits_str}."
        )
        chunks.append(KnowledgeChunk(text, source, category, {"practice_id": data.get("practice_id"), "name": name}))
        if vis_str:
            chunks.append(
                KnowledgeChunk(
                    f"Practice visualization [{name}]: {vis_str}",
                    source,
                    category,
                    {"practice_id": data.get("practice_id"), "name": name, "section": "visualization"},
                )
            )
        return chunks

    def _chunk_markdown(self, text: str, source: str, category: str) -> list[KnowledgeChunk]:
        """Split a markdown document into paragraph-based chunks.

        Splits on blank-line boundaries and on markdown heading lines so each
        section becomes its own searchable chunk. Chunks shorter than ~80 chars
        are merged into the next one.
        """
        import re

        if not text.strip():
            return []
        lines = text.splitlines()
        sections: list[str] = []
        current: list[str] = []
        for line in lines:
            if re.match(r"^#{1,6}\s", line):
                if current:
                    sections.append("\n".join(current).strip())
                    current = []
            current.append(line)
            if not line.strip() and current:
                joined = "\n".join(current).strip()
                if joined:
                    sections.append(joined)
                    current = []
        if current:
            tail = "\n".join(current).strip()
            if tail:
                sections.append(tail)

        chunks: list[KnowledgeChunk] = []
        buffer = ""
        for section in sections:
            if len(buffer) < 80:
                buffer = (buffer + "\n\n" + section).strip() if buffer else section
            else:
                chunks.append(self._make_md_chunk(buffer, source, category))
                buffer = section
        if buffer.strip():
            chunks.append(self._make_md_chunk(buffer, source, category))
        return chunks

    def _make_md_chunk(self, text: str, source: str, category: str) -> KnowledgeChunk:
        first_line = text.splitlines()[0].lstrip("# ").strip()[:80]
        return KnowledgeChunk(
            text,
            source,
            category,
            {"title": first_line} if first_line else None,
        )

    # ------------------------------------------------------------------
    # Runtime document upload
    # ------------------------------------------------------------------

    def add_document(
        self,
        text: str,
        source: str,
        category: str = "document",
        metadata: dict[str, Any] | None = None,
        chunk_strategy: str = "auto",
    ) -> int:
        """Index an arbitrary text document at runtime (e.g. from upload).

        Returns the number of chunks added. ``chunk_strategy`` may be:
        ``"auto"`` (markdown-aware when source ends in .md, else paragraph),
        ``"markdown"``, or ``"paragraph"``.
        """
        if not text or not text.strip():
            return 0
        if chunk_strategy == "auto":
            chunk_strategy = "markdown" if source.lower().endswith(".md") else "paragraph"

        if chunk_strategy == "markdown":
            new_chunks = self._chunk_markdown(text, source, category)
        else:
            new_chunks = self._chunk_paragraphs(text, source, category)

        for meta_key, meta_val in (metadata or {}).items():
            for c in new_chunks:
                c.metadata.setdefault(meta_key, meta_val)

        for chunk in new_chunks:
            chunk.embed()
            self.chunks.append(chunk)
        return len(new_chunks)

    def _chunk_paragraphs(self, text: str, source: str, category: str) -> list[KnowledgeChunk]:
        """Paragraph splitter for plain-text uploads.

        Splits on blank lines; falls back to sentence-ish boundaries if no
        blank lines exist, with a soft target of ~800 chars per chunk.
        """
        import re

        if not text.strip():
            return []
        target = 800
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
        if len(paragraphs) <= 1:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            paragraphs = []
            buf = ""
            for s in sentences:
                buf = (buf + " " + s).strip() if buf else s
                if len(buf) >= target:
                    paragraphs.append(buf)
                    buf = ""
            if buf:
                paragraphs.append(buf)

        chunks: list[KnowledgeChunk] = []
        buffer = ""
        for para in paragraphs:
            if len(buffer) + len(para) > target and buffer:
                chunks.append(KnowledgeChunk(buffer, source, category))
                buffer = para
            else:
                buffer = (buffer + "\n\n" + para).strip() if buffer else para
        if buffer.strip():
            chunks.append(KnowledgeChunk(buffer, source, category))
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
