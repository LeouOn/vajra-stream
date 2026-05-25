#!/usr/bin/env python3
"""
Create Test Populations

This script creates the test populations (California, Myanmar, Congo)
that are expected by the data loading test, as well as the new global
multidimensional populations.
"""

import json
import os
import sys

# Add parent directory to path to import backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

from backend.core.services.population_manager import PopulationCategory, SourceType, get_population_manager


def create_test_populations():
    """Create test populations"""
    manager = get_population_manager()

    # Load existing populations by name to avoid duplicates
    existing_pops = {pop.name: pop for pop in manager.get_all_populations()}

    def get_or_create(name, **kwargs):
        if name in existing_pops:
            print(f"Population '{name}' already exists. Updating fields...")
            return manager.update_population(existing_pops[name].id, **kwargs)
        else:
            print(f"Creating population '{name}'...")
            return manager.create_population(name=name, **kwargs)

    # 1. Create/Update California population (preserves unit test expectation)
    california = get_or_create(
        name="California",
        description="Missing persons from California",
        category=PopulationCategory.MISSING_PERSONS,
        source_type=SourceType.MANUAL,
        intentions=["safety", "reunion", "love"],
        priority=7,
    )

    # 2. Create/Update Myanmar population (preserves unit test expectation)
    myanmar = get_or_create(
        name="Myanmar",
        description="Genocide victims from Myanmar",
        category=PopulationCategory.CONFLICT_ZONES,
        source_type=SourceType.MANUAL,
        intentions=["peace", "healing", "justice"],
        priority=8,
    )

    # 3. Create/Update Congo population (preserves unit test expectation)
    congo = get_or_create(
        name="Congo",
        description="Refugees from Congo",
        category=PopulationCategory.REFUGEES,
        source_type=SourceType.MANUAL,
        intentions=["safety", "shelter", "peace"],
        priority=6,
    )

    # 4. Amazon Rainforest
    get_or_create(
        name="Amazon Rainforest",
        description="Ecosystem protection and biodiversity restoration of the Amazon Rainforest.",
        category=PopulationCategory.ENDANGERED_SPECIES,
        source_type=SourceType.MANUAL,
        intentions=["ecological protection", "biodiversity", "healing", "vitality"],
        priority=8,
        tags=["ecological", "rainforest", "astrology-venus", "geomancy-albus", "archetype-empress"],
        notes=json.dumps({
            "astrology": {
                "ruling_planet": "Venus",
                "zodiac_sign": "Taurus",
                "element": "Earth",
                "planetary_alignment": "Venus sextile Neptune"
            },
            "geomancy": {
                "figure": "Albus",
                "pattern": [2, 2, 1, 2],
                "translation": "The White",
                "meaning": "Wisdom, clarity, peace, purification"
            },
            "archetype": {
                "tarot_card": "The Empress",
                "hebrew_letter": "Daleth",
                "meaning": "Abundance, creativity, nature, mothering"
            },
            "radionics": {
                "rate": [15, 45, 92],
                "general_vitality": 850
            }
        })
    )

    # 5. Global Hospital Patients
    get_or_create(
        name="Global Hospital Patients",
        description="Recovery and healing support for children and adults in critical care worldwide.",
        category=PopulationCategory.HOSPITAL_PATIENTS,
        source_type=SourceType.MANUAL,
        intentions=["recovery", "comfort", "healing", "peace"],
        priority=9,
        tags=["healthcare", "healing", "astrology-moon", "geomancy-laetitia", "archetype-high-priestess"],
        notes=json.dumps({
            "astrology": {
                "ruling_planet": "Moon",
                "zodiac_sign": "Cancer",
                "element": "Water",
                "planetary_alignment": "Moon conjunct Jupiter"
            },
            "geomancy": {
                "figure": "Laetitia",
                "pattern": [1, 2, 2, 2],
                "translation": "Joy",
                "meaning": "Joy, health, expansion, positive news"
            },
            "archetype": {
                "tarot_card": "The High Priestess",
                "hebrew_letter": "Gimel",
                "meaning": "Intuition, subconscious, healing, inner secrets"
            },
            "radionics": {
                "rate": [42, 60, 85],
                "general_vitality": 720
            }
        })
    )

    # 6. Sahel Green Wall Initiative
    get_or_create(
        name="Sahel Green Wall Initiative",
        description="Desert reclamation, land restoration, and community resilience across the Sahel region.",
        category=PopulationCategory.CUSTOM,
        source_type=SourceType.MANUAL,
        intentions=["restoration", "growth", "cohesion", "resilience"],
        priority=7,
        tags=["sahel", "ecological", "astrology-saturn", "geomancy-acquisitio", "archetype-emperor"],
        notes=json.dumps({
            "astrology": {
                "ruling_planet": "Saturn",
                "zodiac_sign": "Capricorn",
                "element": "Earth",
                "planetary_alignment": "Saturn trine Sun"
            },
            "geomancy": {
                "figure": "Acquisitio",
                "pattern": [2, 1, 2, 1],
                "translation": "Gain",
                "meaning": "Increase, expansion, success"
            },
            "archetype": {
                "tarot_card": "The Emperor",
                "hebrew_letter": "Heh",
                "meaning": "Structure, authority, discipline, strong foundation"
            },
            "radionics": {
                "rate": [28, 55, 94],
                "general_vitality": 680
            }
        })
    )

    # 7. Great Barrier Reef Ecosystem
    get_or_create(
        name="Great Barrier Reef Ecosystem",
        description="Marine preservation, coral recovery, and ecological protection of the Great Barrier Reef.",
        category=PopulationCategory.ENDANGERED_SPECIES,
        source_type=SourceType.MANUAL,
        intentions=["marine restoration", "coral healing", "biodiversity", "protection"],
        priority=8,
        tags=["marine", "reef", "astrology-neptune", "geomancy-populus", "archetype-star"],
        notes=json.dumps({
            "astrology": {
                "ruling_planet": "Neptune",
                "zodiac_sign": "Pisces",
                "element": "Water",
                "planetary_alignment": "Moon trine Neptune"
            },
            "geomancy": {
                "figure": "Populus",
                "pattern": [2, 2, 2, 2],
                "translation": "The People",
                "meaning": "Consensus, flow, gathering, diffusion"
            },
            "archetype": {
                "tarot_card": "The Star",
                "hebrew_letter": "Tzaddi",
                "meaning": "Hope, renewal, cosmic inspiration"
            },
            "radionics": {
                "rate": [33, 77, 99],
                "general_vitality": 790
            }
        })
    )

    # 8. Global Communities
    get_or_create(
        name="Global Communities",
        description="Nurturing social cohesion, mutual understanding, and regional harmony across all communities.",
        category=PopulationCategory.CUSTOM,
        source_type=SourceType.MANUAL,
        intentions=["harmony", "cohesion", "mutual understanding", "peace"],
        priority=6,
        tags=["communities", "social", "astrology-jupiter", "geomancy-fortuna-major", "archetype-lovers"],
        notes=json.dumps({
            "astrology": {
                "ruling_planet": "Jupiter",
                "zodiac_sign": "Libra",
                "element": "Air",
                "planetary_alignment": "Jupiter sextile Venus"
            },
            "geomancy": {
                "figure": "Fortuna Major",
                "pattern": [2, 2, 1, 1],
                "translation": "Greater Fortune",
                "meaning": "Inner victory, supreme success, protection"
            },
            "archetype": {
                "tarot_card": "The Lovers",
                "hebrew_letter": "Zayin",
                "meaning": "Alignment of values, choices, harmony"
            },
            "radionics": {
                "rate": [50, 50, 50],
                "general_vitality": 880
            }
        })
    )

    # 9. Refugees & War Victims
    get_or_create(
        name="Refugees & War Victims",
        description="Providing safety, sanctuary, and psychological healing to displaced populations and war victims.",
        category=PopulationCategory.REFUGEES,
        source_type=SourceType.MANUAL,
        intentions=["safety", "shelter", "inner peace", "healing"],
        priority=9,
        tags=["refugees", "humanitarian", "astrology-mars", "geomancy-carcer", "archetype-strength"],
        notes=json.dumps({
            "astrology": {
                "ruling_planet": "Venus",
                "zodiac_sign": "Leo",
                "element": "Fire",
                "planetary_alignment": "Mars conjunct Venus"
            },
            "geomancy": {
                "figure": "Carcer",
                "pattern": [1, 2, 2, 1],
                "translation": "Sanctuary",
                "meaning": "Transmuting restriction and danger into security and safe containment"
            },
            "archetype": {
                "tarot_card": "Strength",
                "hebrew_letter": "Teth",
                "meaning": "Inner strength, patience, fortitude, compassion"
            },
            "radionics": {
                "rate": [18, 38, 72],
                "general_vitality": 550
            }
        })
    )

    # 10. World Leaders
    get_or_create(
        name="World Leaders",
        description="Inspiring wisdom, clear decision-making, and compassion in global leadership.",
        category=PopulationCategory.CUSTOM,
        source_type=SourceType.MANUAL,
        intentions=["wisdom", "clear decision-making", "compassion", "clarity"],
        priority=7,
        tags=["leaders", "decision-making", "astrology-sun", "geomancy-caput-draconis", "archetype-magician"],
        notes=json.dumps({
            "astrology": {
                "ruling_planet": "Sun",
                "zodiac_sign": "Sagittarius",
                "element": "Fire",
                "planetary_alignment": "Sun conjunct Jupiter"
            },
            "geomancy": {
                "figure": "Caput Draconis",
                "pattern": [2, 1, 1, 1],
                "translation": "Dragon's Head",
                "meaning": "New beginnings, entry point, spiritual growth"
            },
            "archetype": {
                "tarot_card": "The Magician",
                "hebrew_letter": "Beth",
                "meaning": "Willpower, manifestation, clear vision"
            },
            "radionics": {
                "rate": [10, 80, 90],
                "general_vitality": 620
            }
        })
    )

    # Get all populations to verify
    all_populations = manager.get_all_populations()
    print(f"\nTotal populations managed: {len(all_populations)}")
    for pop in all_populations:
        print(f"  - {pop.name} ({pop.category.value})")

    return len(all_populations)


if __name__ == "__main__":
    print("Creating/updating populations...")
    count = create_test_populations()
    print(f"\nSuccessfully managed {count} populations")
