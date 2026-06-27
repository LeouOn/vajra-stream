#!/usr/bin/env python3
"""
Full Ritual Broadcast — generates sacred texts + crystal bowl + mantras.

Creates a complete ritual document with invocation, LLM-generated prayer,
dharma teaching, divination correspondences (astrology + tarot + I Ching),
hero journey narrative, and dedication of merit. Then triggers the crystal
bowl broadcast with Solfeggio carrier frequencies.
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.compassionate_blessings import BlessingDatabase, BlessingTarget, BlessingCategory
from core.rate_to_audio import map_rate_to_carriers
from core.ritual_generator import RitualGenerator


def main():
    db = BlessingDatabase()
    ritual_gen = RitualGenerator()

    # Try to get the LLM from the container
    llm = None
    try:
        from container import Container
        container = Container()
        llm = container.llm
    except Exception:
        pass

    # Get current astrology data
    astrology_data = None
    try:
        from backend.core.services.vajra_service import vajra_service
        import asyncio
        loop = asyncio.new_event_loop()
        astrology_data = loop.run_until_complete(vajra_service._get_astrology_data())
        loop.close()
    except Exception:
        pass

    # Get all targets
    all_targets = db.get_all_targets()
    target_names = [t.name for t in all_targets]

    # Generate carrier frequencies
    rate_values = [7, 35, 50, 64, 92]
    carriers = map_rate_to_carriers(rate_values, potency=1.0)

    intention = "Universal compassion for all beings suffering, hurt, and departed in this world"

    print("=" * 70)
    print("  SACRED RITUAL GENERATION")
    print("  " + datetime.now().strftime("%B %d, %Y at %I:%M %p"))
    print("=" * 70)
    print()

    # Generate the full ritual
    print("Generating ritual text with LLM + divination...")
    if llm:
        print("  LLM: available")
    else:
        print("  LLM: not available (using fallback templates)")
    if astrology_data:
        western = astrology_data.get("western", {}).get("positions", {})
        sun = western.get("sun", {})
        moon = western.get("moon", {})
        print(f"  Astrology: Sun in {sun.get('sign','?')}, Moon in {moon.get('sign','?')}")
    else:
        print("  Astrology: unavailable")
    print()

    ritual = ritual_gen.generate_full_ritual(
        intention=intention,
        targets=target_names,
        carrier_frequencies=carriers.frequencies,
        solfeggio_names=carriers.solfeggio_names,
        mantras_dedicated=1080,
        astrology_data=astrology_data,
        tradition="vajrayana",
        llm=llm,
    )

    # Print the full ritual
    print(ritual.to_markdown())
    print()
    print("=" * 70)

    # Save to file
    output_path = Path(__file__).parent.parent / "ritual_output.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ritual.to_markdown())
    print(f"Ritual saved to: {output_path}")
    print()

    # Crystal bowl broadcast
    print("Starting crystal bowl broadcast (3 minutes)...")
    try:
        from modules.crystal import CrystalService
        crystal = CrystalService()
        result = crystal.broadcast_intention(
            intention=intention,
            frequencies=carriers.frequencies,
            duration=180,
            hardware_level=2,
            prayer_bowl_mode=True,
            amplitude=carriers.amplitude,
        )
        print(f"Crystal broadcast: {result.get('status', 'unknown')}")
    except Exception as e:
        print(f"Crystal broadcast note: {e}")
    print()
    print("Om Mani Padme Hum.")
    print("=" * 70)


if __name__ == "__main__":
    main()
