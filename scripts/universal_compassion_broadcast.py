#!/usr/bin/env python3
"""
Universal Compassion Broadcast
For all beings suffering, hurt, and departed in this world.

Creates blessing targets for all categories of suffering,
records 1080 mantras (10 mala rounds), generates 6 Solfeggio
carrier frequencies, and triggers crystal bowl prayer bowl broadcast.

Om Mani Padme Hum.
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.compassionate_blessings import BlessingCategory, BlessingDatabase, BlessingTarget
from core.rate_to_audio import map_rate_to_carriers


def main():
    db = BlessingDatabase()

    print("=" * 70)
    print("  UNIVERSAL COMPASSION BROADCAST")
    print("  For all beings suffering, hurt, and departed in this world")
    print("  " + datetime.now().strftime("%B %d, %Y at %I:%M %p"))
    print("=" * 70)
    print()

    # --- 1. Create universal targets ---
    print("Step 1: Creating universal compassion targets...")

    targets_data = [
        (
            "all_suffering_living",
            "All Living Beings Suffering Now",
            BlessingCategory.ALL_SENTIENT_BEINGS,
            "Every being across all realms currently experiencing physical pain, "
            "emotional anguish, fear, hunger, loneliness, war, displacement, "
            "illness, or despair",
            "May all suffering cease. May all beings find healing, shelter, love, and liberation.",
            10,
        ),
        (
            "all_recently_deceased",
            "All Beings Who Have Recently Passed",
            BlessingCategory.DECEASED,
            "Every being who has transitioned in recent days and weeks, from "
            "all causes: war, disaster, illness, accident, age, violence. "
            "May they not wander in darkness.",
            "May all who have passed find clear light, swift guidance, and liberation through the bardo.",
            10,
        ),
        (
            "war_victims_global",
            "Victims of All Active Conflicts",
            BlessingCategory.REFUGEE,
            "Civilians, soldiers, children, elderly, and all beings caught "
            "in active conflict zones, displacement camps, and war-torn "
            "regions across the world",
            "May peace dawn where there is war. May safety reach where there "
            "is danger. May reconciliation heal what violence has broken.",
            9,
        ),
        (
            "disaster_victims_global",
            "Victims of Natural Disasters",
            BlessingCategory.HOMELESS,
            "All beings affected by earthquakes, floods, fires, storms, "
            "famines, and displacement from natural causes across the world",
            "May the earth find stability. May shelter reach the displaced. May healing reach the injured.",
            9,
        ),
        (
            "venezuela_earthquake",
            "Venezuela Earthquake Victims",
            BlessingCategory.SUFFERING_UNKNOWN,
            "All beings affected by the earthquake in Venezuela: the injured, "
            "displaced, grieving, rescuers, and those who have transitioned",
            "Liberation, healing, and peace for all beings affected by the Venezuela earthquake.",
            10,
        ),
    ]

    created = 0
    for identifier, name, category, desc, intention, priority in targets_data:
        existing = db.get_target(identifier)
        if existing:
            print(f"  [exists] {name}")
            continue
        target = BlessingTarget(
            identifier=identifier,
            name=name,
            category=category,
            description=desc,
            intention=intention,
            priority=priority,
        )
        db.add_target(target)
        created += 1
        print(f"  [created] {name}")

    all_targets = db.get_all_targets()
    print(f"  Total targets: {len(all_targets)}")
    print()

    # --- 2. Record mass blessing session ---
    print("Step 2: Recording universal blessing session...")

    session_id = db.record_session(
        mantra_type="Om Mani Padme Hum",
        total_mantras=1080,
        total_rotations=10,
        targets_blessed=len(all_targets),
        allocation_method="Universal Compassion - Equitable Distribution",
        notes="Universal compassion broadcast for all suffering beings. "
        "1080 mantras (10 x 108) distributed across all targets. "
        "Combined with 6-frequency Solfeggio crystal bowl broadcast.",
    )
    print(f"  Session: {session_id}")
    print("  Mantras: 1080 (10 mala rounds x 108)")
    print()

    # Distribute mantras equitably across targets
    mantras_per_target = 1080 // len(all_targets)
    remainder = 1080 % len(all_targets)
    for i, target in enumerate(all_targets):
        count = mantras_per_target + (1 if i < remainder else 0)
        db.record_dedication(
            target_identifier=target.identifier,
            session_id=session_id,
            mantra_type="Om Mani Padme Hum",
            mantras_count=count,
            notes=f"Universal compassion broadcast - {count} mantras to {target.name}",
        )
        print(f"  {count:>4} mantras -> {target.name}")
    print()

    # --- 3. Generate carrier frequencies ---
    print("Step 3: Generating crystal bowl carrier frequencies...")

    # Universal compassion set spanning all Solfeggio tones
    rate_values = [7, 35, 50, 64, 92]  # Ut + Mi + La + Sol + Divine
    carriers = map_rate_to_carriers(rate_values, potency=1.0)

    print(f"  Dial values: {rate_values}")
    print(f"  Amplitude: {carriers.amplitude:.4f} (maximum)")
    print(f"  Overtone richness: {carriers.overtone_richness:.4f} (full harmonics)")
    print("  Carrier frequencies:")
    for i, (freq, name) in enumerate(zip(carriers.frequencies, carriers.solfeggio_names)):
        print(f"    [{i + 1}] {freq:>7.2f} Hz - {name}")
    print()

    # --- 4. Crystal bowl broadcast ---
    print("Step 4: Starting crystal bowl broadcast (5 minutes)...")
    print("  6 prayer bowl tones with full harmonic synthesis")
    print("  6 harmonic partials + 3 metallic partials per carrier")
    print("  ADSR envelope + tremolo + vibrato")
    print()

    try:
        from modules.crystal import CrystalService

        crystal = CrystalService()
        result = crystal.broadcast_intention(
            intention="Universal Compassion: Liberation, Healing, and Peace "
            "for all suffering beings across all realms. "
            "Om Mani Padme Hum.",
            frequencies=carriers.frequencies,
            duration=300,  # 5 minutes
            hardware_level=2,
            prayer_bowl_mode=True,
            amplitude=carriers.amplitude,
        )
        status = result.get("status", "unknown")
        print(f"  Crystal broadcast: {status}")
        if result.get("error"):
            print(f"  Note: {result['error']}")
    except Exception as e:
        print(f"  Broadcast note: {e}")
    print()

    # --- 5. Dedication of merit ---
    print("Step 5: Dedication of merit")
    print()
    print("  May the merit of this practice flow to:")
    for t in all_targets:
        print(f"    - {t.name}")
    print()
    print("  May all beings without exception")
    print("  be free from suffering and the root of suffering.")
    print("  May all beings without exception")
    print("  know happiness and the root of happiness.")
    print()
    print("  Gate gate paragate parasamgate bodhi svaha.")
    print()

    # --- 6. Summary ---
    stats = db.get_statistics()
    print("PROTOCOL SUMMARY")
    print("-" * 50)
    print(f"  Blessing targets: {len(all_targets)}")
    print(f"  Mantras dedicated: {stats['total_mantras_dedicated']}")
    print(f"  Crystal frequencies: {len(carriers.frequencies)} carriers")
    print("  Broadcast duration: 5 minutes")
    print(f"  Session: #{session_id}")
    print()
    print("  Om Mani Padme Hum.")
    print("=" * 70)


if __name__ == "__main__":
    main()
