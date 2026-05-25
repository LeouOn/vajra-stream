#!/usr/bin/env python3
"""
Holistic blessing run simulation
Demonstrates the integration of:
- TargetPopulation manager (loads seeded global populations)
- Esoteric mappings (astrology, geomancy, archetypes)
- Radionics engine (General Vitality, signature rates, balancing rates)
- Blessing generator (mantras and dedication text)
- Crystal grid broadcaster (Schumann and alchemical frequencies)
- Unified Event Bus (routes and completes sessions)
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("HolisticBlessing")

# Configure console encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Core imports
from backend.core.services.population_manager import get_population_manager
from core.radionics_engine import RadionicsAnalyzer, RadionicsRate
from core.compassionate_blessings import BlessingDatabase
from infrastructure.event_bus import DomainEvent
from modules.blessing_router import BlessingRouted, TargetSpecification, TargetType
from modules.interfaces import BlessingGenerated
from modules.crystal import CrystalBroadcastCompleted, CrystalBroadcastStarted
from scripts.unified_orchestrator import UnifiedOrchestrator


def print_title(title):
    print("\n" + "=" * 80)
    print(f" {title.upper()}")
    print("=" * 80)


def print_event(event: DomainEvent):
    """Listener to log system events"""
    print(f"\n⚡ [SYSTEM EVENT] {event.__class__.__name__}")
    print(f"   Event ID:  {event.event_id}")
    data = {k: v for k, v in event.__dict__.items() if not k.startswith("_")}
    for key, val in data.items():
        if key == "blessing_text":
            # Print first few lines of blessing text
            lines = val.split("\n")
            print(f"   blessing_text: {lines[0]} ... ({len(lines)} lines)")
        elif key == "target_spec":
            print(f"   target_spec: {val.identifier} (Type: {val.target_type.value})")
        else:
            print(f"   {key}: {val}")


def main():
    print_title("Vajra.Stream Holistic Blessing & Radionics Run")

    # 1. Initialize Orchestrator & Analyzer
    logger.info("Initializing Unified Orchestrator & Radionics Analyzer...")
    orchestrator = UnifiedOrchestrator()
    analyzer = RadionicsAnalyzer()

    # Subscribe to key events on the bus
    orchestrator.event_bus.subscribe(BlessingRouted, print_event)
    orchestrator.event_bus.subscribe(BlessingGenerated, print_event)
    orchestrator.event_bus.subscribe(CrystalBroadcastStarted, print_event)
    orchestrator.event_bus.subscribe(CrystalBroadcastCompleted, print_event)

    # 2. Retrieve seeded populations from Manager
    manager = get_population_manager()
    all_pops = manager.get_all_populations()

    # Filter for our newly added global targets
    global_names = [
        "Amazon Rainforest",
        "Global Hospital Patients",
        "Sahel Green Wall Initiative",
        "Great Barrier Reef Ecosystem",
        "Global Communities",
        "Refugees & War Victims",
        "World Leaders"
    ]
    global_targets = [p for p in all_pops if p.name in global_names]

    print(f"\nLoaded {len(global_targets)} global target populations from local database.")

    # 3. Process each global target population holistically
    for idx, pop in enumerate(global_targets, 1):
        print_title(f"Target {idx}: {pop.name}")
        print(f"Category:    {pop.category.value}")
        print(f"Description: {pop.description}")
        print(f"Intentions:  {', '.join(pop.intentions)}")
        
        # Parse notes JSON to extract esoteric mappings
        esoteric = {}
        if pop.notes:
            try:
                esoteric = json.loads(pop.notes)
            except Exception as e:
                logger.warning(f"Could not parse notes for {pop.name}: {e}")

        # Display Esoteric Mappings
        if esoteric:
            print("\n🔮 Multi-Dimensional Esoteric Coordinates:")
            
            # Astrology
            astro = esoteric.get("astrology", {})
            print(f"  [Astrology] Ruling Planet: {astro.get('ruling_planet')} | Sign: {astro.get('zodiac_sign')} | Element: {astro.get('element')}")
            print(f"              Alignment:     {astro.get('planetary_alignment')}")

            # Geomancy
            geom = esoteric.get("geomancy", {})
            pattern_str = "".join("*" if x == 1 else "**" for x in geom.get("pattern", []))
            print(f"  [Geomancy]  Figure: {geom.get('figure')} ({geom.get('translation')}) | Pattern: {geom.get('pattern')} | Element: {geom.get('element', 'Spirit')}")
            print(f"              Meaning: {geom.get('meaning')}")

            # Archetype
            arch = esoteric.get("archetype", {})
            print(f"  [Archetype] Tarot:  {arch.get('tarot_card')} | Hebrew: {arch.get('hebrew_letter')}")
            print(f"              Aspect:   {arch.get('meaning')}")

            # Radionics Rate
            rad = esoteric.get("radionics", {})
            print(f"  [Radionics] Rate:   {'-'.join(map(str, rad.get('rate', [])))} | Baseline Vitality: {rad.get('general_vitality')}/1000")

        # 4. Perform Real-Time Radionics Analysis
        print("\n📊 Running Real-Time Radionics Scan...")
        
        # Measure baseline General Vitality using the analyzer
        gv = analyzer.gv_meter.measure(pop.name, context={
            "moon_phase": "Full Moon",
            "hour": 5, # Brahma Muhurta hour
            "intention_length": len(pop.description)
        })
        print(f"  Measured General Vitality: {gv:.1f}/1000 ({analyzer.gv_meter.interpret_gv(gv)})")

        # Generate balancing rates
        balancing_rates = analyzer.find_balancing_rates(pop.name, num_rates=2)
        print("  Resonant Balancing Rates:")
        for rate in balancing_rates:
            print(f"    - {rate} (Resonance: {rate.potency:.3f})")

        # 5. Broadcast Intention via Unified System
        print("\n📡 Initiating Alchemical Broadcast Session...")
        
        targets_spec = [
            {
                "type": "location" if "Ecosystem" in pop.name or "Rainforest" in pop.name else "individual",
                "identifier": pop.name,
                "metadata": {
                    "astrology": esoteric.get("astrology", {}),
                    "geomancy": esoteric.get("geomancy", {}),
                    "radionics_rate": esoteric.get("radionics", {}).get("rate", [])
                }
            }
        ]

        # Trigger session through the central orchestrator
        # Short duration of 2 seconds per target for fast simulation demo
        session_id = orchestrator.create_session(
            intention=f"Healing, Harmony, and Elevation for {pop.name}",
            targets=targets_spec,
            modalities=["crystal"],
            duration=2
        )
        print(f"  Unified Session Activated: {session_id}")
        
        # Small wait buffer to simulate broadcasting process
        time.sleep(3)

    print_title("Holistic Simulation Complete")
    print("All global target populations successfully analyzed, balanced, and broadcasted.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
