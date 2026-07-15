#!/usr/bin/env python3
"""
July 4th Ritual â€Ea dedication for the nation and all beings in it.

Uses the freshly-audited knowledge base (real Sanghata text, canonical
Diamond Sutra, paraphrased Golden Light protection) to generate a ritual
for the day. Runs the full pipeline:
  1. Detect suffering type from the intention
  2. Generate full ritual (invocation + dharani + prayer + teaching + sutra)
  3. Print it
  4. Start a short crystal bowl broadcast

The intention is specific: wisdom and protection for the nation, all who
dwell in it, and all who suffer in this season.
"""

import io
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from core.rate_to_audio import map_rate_to_carriers  # noqa: E402
from core.ritual_generator import RitualGenerator  # noqa: E402


def main():
    # July 4th intention â€Ebroad enough to cover the nation, personal loss,
    # and all beings caught in this season's suffering.
    intention = (
        "On this Independence Day, may wisdom and compassion illuminate this "
        "nation and all who dwell within it. May those who have lost â€” of "
        "wealth, of health, of loved ones, of hope â€” find their loss become "
        "the path. May the merit of this practice reach every being in every "
        "realm, without exception."
    )

    ritual_gen = RitualGenerator()

    # Detect suffering type to verify the routing
    suffering_type = ritual_gen.detect_suffering_type(intention)
    print("=" * 70)
    print("  JULY 4TH RITUAL â€EDEDICATION FOR THE NATION")
    print(f"  {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    print(f"  Detected suffering type: {suffering_type}")
    print("=" * 70)
    print()

    # Carrier frequencies â€Ea calming set for a difficult day.
    # D1=42 (physical grounding), D2=60 (astral), D3=77.3 (mental clarity),
    # D4=50 (causal balance), D5=88 (spiritual).
    rate_values = [42, 60, 77, 50, 88]
    carriers = map_rate_to_carriers(rate_values, potency=1.0)

    print(f"Carrier frequencies: {carriers.frequencies}")
    print(f"Solfeggio names:     {carriers.solfeggio_names}")
    print()

    # Try LLM for richer text, fall back to canonical templates
    llm = None
    try:
        from container import Container

        llm = Container().llm
        if llm and getattr(llm, "client", None) or getattr(llm, "local_model", None):
            print("LLM: available")
        else:
            llm = None
            print("LLM: not configured (using canonical templates)")
    except Exception as e:
        print(f"LLM: unavailable ({e})")
    print()

    # Generate the full ritual
    ritual = ritual_gen.generate_full_ritual(
        intention=intention,
        targets=["this nation", "all who dwell in it", "all beings suffering in this season"],
        carrier_frequencies=carriers.frequencies,
        solfeggio_names=carriers.solfeggio_names,
        mantras_dedicated=1080,
        astrology_data=None,  # would need the backend running; this still works
        tradition="vajrayana",
        llm=llm,
    )

    md = ritual.to_markdown()
    print(md)

    # Save to file (gitignored â€Eprivate ritual output)
    output_path = Path(__file__).parent.parent / "ritual_output.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
    print()
    print(f"Ritual saved to: {output_path}")
    print()

    # Short crystal bowl broadcast (90 seconds â€Eshort to keep this script quick)
    print("=" * 70)
    print("  Crystal bowl broadcast (90 seconds)")
    print("=" * 70)
    try:
        from container import Container

        crystal = Container().crystal
        result = crystal.broadcast_intention(
            intention=intention,
            frequencies=carriers.frequencies,
            duration=90,
            hardware_level=2,
            prayer_bowl_mode=True,
            amplitude=carriers.amplitude,
        )
        print(f"Crystal broadcast: {result.get('status', 'unknown')}")
    except Exception as e:
        print(f"Crystal broadcast note: {e}")

    print()
    print("Om Mani Padme Hum.")
    print("May all beings be free. May all beings be at peace.")
    print("=" * 70)


if __name__ == "__main__":
    main()
