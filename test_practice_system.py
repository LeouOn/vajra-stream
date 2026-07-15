"""End-to-end test of the Vajra Stream practice system.
Runs without any LLM API call (just exercises the knowledge base, TTS, and practice engine scaffolding).
"""
import asyncio
import json
import os
import sys


def test_knowledge_base():
    print("\n=== Knowledge Base ===")
    practices_dir = "knowledge/practices"
    files = [f for f in os.listdir(practices_dir) if f.endswith(".json")]
    print(f"  Total practices: {len(files)}")
    for f in sorted(files):
        with open(os.path.join(practices_dir, f), encoding="utf-8") as fh:
            d = json.load(fh)
        name = d.get("name", d.get("id", "?"))
        mantra = d.get("mantra_short") or d.get("mantra_sanskrit") or d.get("mantra", "?")
        reps = d.get("mantra_count", "?")
        benefits = d.get("benefits", [])
        print(f"    - {f.replace('.json', '')}")
        print(f"        Name: {name}")
        print(f"        Mantra: {str(mantra)[:60]}")
        print(f"        Repetitions: {reps}")
        print(f"        Benefits: {', '.join(str(b)[:40] for b in benefits[:2])}")
    return files


async def test_tts_provider():
    print("\n=== TTS Provider ===")
    try:
        from core.tts_provider import get_tts_provider
        provider = get_tts_provider()
        print(f"  Type: {type(provider).__name__}")
        if provider and hasattr(provider, "speak"):
            print("  speak() method: available")
        if provider and hasattr(provider, "list_speakers"):
            try:
                speakers = await provider.list_speakers()
                print(f"  Speakers: {speakers[:5] if speakers else 'none'}")
            except Exception as e:
                print(f"  list_speakers error: {e}")
    except Exception as e:
        print(f"  Error: {e}")


def test_practice_engine():
    print("\n=== Practice Engine ===")
    try:
        from core.practice_engine import PracticeEngine
        engine = PracticeEngine.get_instance()
        if hasattr(engine, "list_practices"):
            practices = engine.list_practices()
            print(f"  Total practices loaded: {len(practices)}")
            for p in practices[:3]:
                pid = p.get("id", "?")
                name = p.get("name", "?")
                mantra = str(p.get("mantra", "?"))[:60]
                print(f"    - {pid}: {name}")
                print(f"        Mantra: {mantra}")
    except Exception as e:
        print(f"  Error: {e}")


async def test_knowledge_search():
    print("\n=== Knowledge Search (RAG) ===")
    try:
        from core.knowledge_index import get_knowledge_index
        idx = get_knowledge_index()
        for query in ["compassion", "Tara", "medicine Buddha", "Mantra"]:
            try:
                results = idx.search(query, top_k=3)
                print(f"  '{query}': {len(results)} results")
                for r in results[:2]:
                    text = str(r.get("text", r.get("content", "?")))[:60]
                    src = r.get("source", r.get("category", "?"))
                    print(f"    - {text} (src: {src})")
            except Exception as e:
                print(f"  '{query}' error: {e}")
    except Exception as e:
        print(f"  Error: {e}")


def test_dharma_lookup():
    print("\n=== Dharma Lookup ===")
    try:
        from core.knowledge_index import get_knowledge_index
        idx = get_knowledge_index()
        entities = idx._chunks if hasattr(idx, "_chunks") else []
        sources = sorted({c.get("source", "?") for c in entities})
        print(f"  Total chunks: {len(entities)}")
        for s in sources:
            count = sum(1 for c in entities if c.get("source") == s)
            print(f"  - {s}: {count} chunks")
    except Exception as e:
        print(f"  Error: {e}")


async def main():
    test_knowledge_base()
    await test_tts_provider()
    test_practice_engine()
    await test_knowledge_search()
    test_dharma_lookup()
    print("\n=== All tests complete ===")


if __name__ == "__main__":
    asyncio.run(main())
