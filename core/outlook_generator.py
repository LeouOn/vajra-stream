"""
Outlook Generator — narrative healing and sutra-style blessing orchestration.

Generates personalised healing narratives, astrological outlooks, and
compassionate blessings for individuals based on their birth chart, current
transits, and divination results. Integrates with the backend's character
manager, location manager, population manager, and divination service to
produce context-rich, spiritually-grounded narratives.

Dependencies:
    Optional (gracefully degraded): :class:`~core.astrology.AstrologyEngine`,
    :mod:`backend.core.services.divination_service`,
    :mod:`backend.core.services.character_manager`,
    :mod:`backend.core.services.location_manager`,
    :mod:`backend.core.services.population_manager`.

Exports:
    OutlookGenerator — main narrative generation class.
"""

import json
import os
import random
from datetime import datetime
from typing import Any

# Attempt imports for local services, degraded gracefully if missing
try:
    from backend.core.services.divination_service import divination_service
except ImportError:
    divination_service = None

try:
    from core.astrology import AstrologyEngine
except ImportError:
    AstrologyEngine = None

try:
    from backend.core.services.character_manager import get_character_manager
    from backend.core.services.location_manager import get_location_manager
    from backend.core.services.population_manager import get_population_manager
except ImportError:
    get_character_manager = None
    get_location_manager = None
    get_population_manager = None


class OutlookGenerator:
    """
    Advanced Narrative Generation and Outlook orchestration engine.
    Weaves astrology, divination (I Ching, Tarot), and sacred entities into sutra-style blessings.
    """

    def __init__(self, llm_integration=None):
        self.llm = llm_integration
        self.astro_engine = AstrologyEngine() if AstrologyEngine else None
        self.divination = divination_service
        self.sacred_entities = self._load_sacred_entities()

        self.genres = ["healing", "victory", "fun_parable", "alchemist", "dharani"]
        self.supported_languages = ["English", "Sanskrit", "Tibetan", "Chinese", "Latin", "Greek", "Hebrew"]

    def _load_sacred_entities(self) -> dict[str, Any]:
        path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "sacred_entities.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _gather_astrology_context(self, lat: float, lon: float, date: datetime = None) -> str:
        if not self.astro_engine:
            return "Astrological alignment: The stars dance in unknown but auspicious patterns."
        try:
            target_date = date or datetime.now()
            chart = self.astro_engine.calculate_chart(target_date, lat, lon)
            western = chart.get("western", {})
            positions = western.get("positions", {})
            indian = chart.get("indian", {})
            chinese = chart.get("chinese", {})
            planetary_hours = chart.get("planetary_hours", {})

            lines = []

            # --- Planetary Positions ---
            planet_order = [
                "sun",
                "moon",
                "mercury",
                "venus",
                "mars",
                "jupiter",
                "saturn",
                "uranus",
                "neptune",
                "pluto",
            ]
            planet_lines = []
            for p in planet_order:
                data = positions.get(p, {})
                if data:
                    sign = data.get("sign", "?")
                    deg = data.get("degree", 0)
                    house = data.get("house")
                    retro = " ℞" if data.get("retrograde") else ""
                    house_str = f" in House {house}" if house else ""
                    planet_lines.append(f"  {p.title():>8} → {sign} {deg:.1f}°{retro}{house_str}")
            if planet_lines:
                lines.append("Planetary Positions:\n" + "\n".join(planet_lines))

            # --- Angles ---
            asc = positions.get("ascendant", {})
            mc = positions.get("midheaven", {})
            if asc or mc:
                angle_parts = []
                if asc:
                    angle_parts.append(f"Ascendant: {asc.get('sign', '?')} {asc.get('degree', 0):.1f}°")
                if mc:
                    angle_parts.append(f"Midheaven: {mc.get('sign', '?')} {mc.get('degree', 0):.1f}°")
                lines.append("Angles: " + " | ".join(angle_parts))

            # --- Elements & Modalities ---
            elements = western.get("elements", {})
            modalities = western.get("modalities", {})
            dom_elem = western.get("dominant_element", "")
            dom_mod = western.get("dominant_modality", "")
            if elements:
                elem_str = ", ".join(f"{k}: {v}" for k, v in sorted(elements.items(), key=lambda x: -x[1]))
                lines.append(f"Elemental Balance: {elem_str} → Dominant: {dom_elem} | Modality: {dom_mod}")

            # --- Top Aspects ---
            aspects = western.get("aspects", [])
            if aspects:
                top_aspects = sorted(aspects, key=lambda a: -a.get("exactness", 0))[:5]
                aspect_lines = [f"  {a['description']}" for a in top_aspects]
                lines.append("Major Aspects:\n" + "\n".join(aspect_lines))

            # --- Moon Phase ---
            try:
                moon_phase = self.astro_engine.get_moon_phase(target_date)
                lines.append(f"Moon Phase: {moon_phase['phase_name']} ({moon_phase['illumination']:.0f}% illuminated)")
            except Exception:
                pass

            # --- Chinese Zodiac ---
            if chinese:
                animal = chinese.get("zodiac_animal", "")
                elem = chinese.get("element", "")
                lunar = chinese.get("lunar_date", {}).get("formatted", "")
                if animal:
                    lines.append(f"Chinese Zodiac: {elem} {animal} — {lunar}")

            # --- Vedic Nakshatra ---
            panchanga = indian.get("panchanga", {})
            nakshatra = panchanga.get("nakshatra", {})
            if nakshatra.get("name"):
                lines.append(f"Vedic Nakshatra: Moon in {nakshatra['name']} (Pada {nakshatra.get('pada', '?')})")

            # --- Planetary Hour ---
            ruler = planetary_hours.get("current_ruler", "")
            if ruler:
                lines.append(f"Planetary Hour Ruler: {ruler}")

            # --- Local Time ---
            try:
                from datetime import timedelta as _td

                tz_offset_hours = round(lon / 15.0)
                tz_name = (
                    "PDT"
                    if (-8 <= tz_offset_hours <= -7)
                    else "PST"
                    if tz_offset_hours == -8
                    else f"UTC{tz_offset_hours:+d}"
                )
                local_dt = target_date + _td(hours=tz_offset_hours)
                lines.append(f"Local Time: {local_dt.strftime('%Y-%m-%d %H:%M')} {tz_name} (approx)")
            except Exception:
                pass

            result = "Cosmic Weather Report:\n" + "\n".join(lines)
            return result

        except Exception as e:
            return f"Astrological context unavailable: {e}"

    def _gather_divination_data(self, include_tarot: bool = True, include_iching: bool = True) -> tuple[str, dict]:
        if not self.divination:
            return "The oracles remain silent.", {}
        parts = []
        raw = {}
        try:
            if include_tarot:
                tarot = self.divination.draw_tarot(1)[0]
                parts.append(f"The Tarot reveals {tarot['name']} ({tarot['orientation']}): {tarot['meaning']}.")
                raw["tarot"] = {
                    "name": tarot.get("name"),
                    "orientation": tarot.get("orientation"),
                    "meaning": tarot.get("meaning"),
                    "svg": tarot.get("svg"),
                }
            if include_iching:
                iching = self.divination.cast_i_ching()
                primary_hex = iching.get("primary", {})
                parts.append(f"The I Ching casts Hexagram {primary_hex.get('name')}: {primary_hex.get('meaning')}.")
                raw["iching"] = {
                    "name": primary_hex.get("name"),
                    "meaning": primary_hex.get("meaning"),
                    "svg": iching.get("svg"),
                }
            text = " ".join(parts) if parts else "The oracles remain silent."
            return text, raw
        except Exception as e:
            return f"Divination context unavailable: {e}", {}

    def _select_sacred_entities(self) -> str:
        if not self.sacred_entities:
            return "Invoking the nameless Buddhas of the ten directions."

        buddha = random.choice(self.sacred_entities.get("buddhas_of_the_fortunate_eon", [{"name": "Shakyamuni"}]))
        yidam = random.choice(
            self.sacred_entities.get(
                "yidams_and_mantras", [{"name": "Chenrezig", "dharani_mantra": "Om Mani Padme Hum"}]
            )
        )

        return (
            f"Under the auspices of {buddha['name']}, Buddha of the Fortunate Eon. "
            f"Invoking the Yidam {yidam['name']} with the dharani: {yidam['dharani_mantra']}."
        )

    def _debug_log_prompt(self, prompt: str, genre: str, lat: float, lon: float) -> None:
        """Write the full LLM prompt to a debug file and print summary to console."""
        try:
            import os as _os
            from datetime import datetime as _dt

            log_dir = _os.path.join(_os.path.dirname(__file__), "..", "session_logs")
            _os.makedirs(log_dir, exist_ok=True)
            timestamp = _dt.now().strftime("%Y%m%d_%H%M%S")
            filename = _os.path.join(log_dir, f"outlook_prompt_{genre}_{timestamp}.txt")
            latest = _os.path.join(log_dir, "outlook_prompt_LATEST.txt")
            with open(filename, "w", encoding="utf-8") as f:
                f.write("# Outlook Prompt Debug Log\n")
                f.write(f"# Time: {_dt.now().isoformat()}\n")
                f.write(f"# Genre: {genre}\n")
                f.write(f"# Coordinates: {lat}, {lon}\n")
                f.write(f"# Prompt length: {len(prompt)} chars\n")
                f.write(f"{'=' * 70}\n\n")
                f.write(prompt)
                f.write(f"\n\n{'=' * 70}\n")
                f.write(f"# End of prompt — {len(prompt)} chars total\n")
            # Also write to LATEST for quick access
            with open(latest, "w", encoding="utf-8") as f:
                f.write(prompt)
            # Print summary to console
            has_unknown = "Unknown" in prompt
            summary = prompt[:300].replace("\n", " ")[:300]
            print(f"[DEBUG] Prompt ({len(prompt)} chars, has_unknown={has_unknown}) → {filename}")
            print(f"[DEBUG] Preview: {summary}...")
        except Exception:
            pass  # Debug logging must never break generation

    def generate_single_outlook(
        self,
        lat: float,
        lon: float,
        languages: list[str],
        genre: str = "healing",
        date: datetime = None,
        custom_context: str | None = None,
        realm_id: str | None = None,
        population_ids: list[str] | None = None,
        character_ids: list[str] | None = None,
        excluded_forces: list[str] | None = None,
        include_dialogue: bool = False,
        model: str | None = None,
        include_astrology: bool = True,
        include_tarot: bool = True,
        include_iching: bool = True,
        randomize_realm: bool = False,
        randomize_characters: bool = False,
        sensor_context: str | None = None,
    ) -> dict[str, Any]:
        """
        Generates a dense, 300-3000 token single-pass narrative outlook.
        """
        if randomize_realm and get_location_manager:
            active_locs = get_location_manager().get_active_locations()
            if active_locs:
                realm_id = random.choice(active_locs).id

        if randomize_characters and get_character_manager:
            active_chars = get_character_manager().get_active_characters()
            if active_chars:
                k = min(random.randint(2, 3), len(active_chars))
                chosen = random.sample(active_chars, k)
                character_ids = [c.id for c in chosen]
        if realm_id and get_location_manager:
            loc = get_location_manager().get_location(realm_id)
            if loc:
                get_location_manager().record_location_feature(realm_id)
                if not loc.is_metaphysical and loc.latitude is not None and loc.longitude is not None:
                    lat = loc.latitude
                    lon = loc.longitude

        astro_context = (
            self._gather_astrology_context(lat, lon, date)
            if include_astrology
            else "The stars wheel in their ancient courses."
        )
        divination_context, divination_raw = self._gather_divination_data(
            include_tarot=include_tarot, include_iching=include_iching
        )
        entity_context = self._select_sacred_entities()

        detailed_context = []
        if realm_id and get_location_manager:
            loc = get_location_manager().get_location(realm_id)
            if loc:
                detailed_context.append(f"Setting / Realm: {loc.name} - {loc.description}")
                if loc.is_metaphysical:
                    detailed_context.append(f"Metaphysical Coordinates: {loc.celestial_coordinates or 'Uncharted'}")
                    detailed_context.append(f"Resonance Frequency: {loc.dimension_frequency or 'Harmonic'} Hz")
                if loc.realm_governor:
                    detailed_context.append(f"Governor / Guardian of this Realm: {loc.realm_governor}")
                if loc.elemental_affinity:
                    detailed_context.append(f"Elemental Affinity: {loc.elemental_affinity}")

        if character_ids and get_character_manager:
            char_texts = []
            for c_id in character_ids:
                char = get_character_manager().get_character(c_id)
                if char:
                    get_character_manager().record_character_feature(c_id)
                    char_texts.append(
                        f"- {char.name} ({char.role.value}): {char.description}. Dialogue Style: {char.dialogue_style}"
                    )
            if char_texts:
                detailed_context.append("Esoteric Characters present:\n" + "\n".join(char_texts))

        if population_ids and get_population_manager:
            pop_texts = []
            for p_id in population_ids:
                pop = get_population_manager().get_population(p_id)
                if pop:
                    pop_texts.append(f"- {pop.name}: {pop.description}. Intended Blessing: {', '.join(pop.intentions)}")
            if pop_texts:
                detailed_context.append(
                    "Beneficiary Target Populations receiving this blessing:\n" + "\n".join(pop_texts)
                )

        if excluded_forces:
            detailed_context.append(f"Negative Forces to exclude/pacify: {', '.join(excluded_forces)}")

        if sensor_context:
            detailed_context.append(f"Quantum Sensor Field / Attunement: {sensor_context}")

        if custom_context:
            detailed_context.append(f"Additional Intentions / Aspiration Context: {custom_context}")

        extra_context_str = "\n\n".join(detailed_context)
        lang_str = ", ".join(languages) if languages else "English"

        prompt = f"""Write a profound, sutra-style narrative outlook and blessing.

Genre/Style: {genre.capitalize()}
Requested Languages: {lang_str} (Weave these languages gracefully into the text, perhaps using them for invocations, mantras, or key poetic phrases, with English as the main narrative bridge unless otherwise specified).

Contexts to weave deeply into the imagery:
- Astrological: {astro_context}
- Oracle/Divination: {divination_context}
- Sacred Entities: {entity_context}"""

        if extra_context_str:
            prompt += f"\n\nEsoteric Settings & Universe Context:\n{extra_context_str}"

        if include_dialogue and character_ids:
            prompt += "\n\nCRITICAL INSTRUCTION: Include direct dialogue between the present characters. Write spoken lines that reflect their specific Dialogue Styles (e.g. speaking in koans, regally, or hermetically)."
        else:
            prompt += "\n\nWrite this as a description, vision, or parable. Dedicate the merit and energy of this transmission to the beneficiary target populations if specified."

        prompt += """\n\nThe narrative should read like a sacred transmission or an alchemical revelation, offering a blessing for this exact time and place.
Do not simply list the contexts—integrate them seamlessly into a compelling mythological or prophetic story arc.
Length: 3-5 paragraphs of dense, visionary prose.
"""

        # Debug: log the full prompt for verification
        self._debug_log_prompt(prompt, genre, lat, lon)

        print(f"[DEBUG generate_single_outlook] model={model!r}, self.llm={type(self.llm).__name__ if self.llm else 'None'}")
        if self.llm:
            result = self.llm.generate(
                prompt=prompt,
                system_prompt="You are a transcendent oracle and dharma scribe, speaking across eons. Your words heal, transform, and reveal the hidden architecture of reality.",
                max_tokens=2500,
                temperature=0.8,
                model=model,
            )
            if result and "No LLM initialized" in result:
                result = f"LLM unavailable. Fallback Generation:\n\n{entity_context}\n{astro_context}\n{divination_context}\n\nMay this transmission bring peace."
        else:
            result = f"LLM unavailable. Fallback Generation:\n\n{entity_context}\n{astro_context}\n{divination_context}\n\nMay this transmission bring peace."

        return {
            "status": "success",
            "type": "single",
            "genre": genre,
            "languages": languages,
            "astrology_used": astro_context,
            "divination_used": divination_context,
            "divination_raw": divination_raw,
            "entities_used": entity_context,
            "narrative": result,
        }

    def generate_epic_outlook(
        self,
        lat: float,
        lon: float,
        languages: list[str],
        genre: str = "alchemist",
        stages: int = 9,
        date: datetime = None,
        custom_context: str | None = None,
        realm_id: str | None = None,
        population_ids: list[str] | None = None,
        character_ids: list[str] | None = None,
        excluded_forces: list[str] | None = None,
        include_dialogue: bool = False,
        model: str | None = None,
        include_astrology: bool = True,
        include_tarot: bool = True,
        include_iching: bool = True,
        randomize_realm: bool = False,
        randomize_characters: bool = False,
        sensor_context: str | None = None,
    ) -> dict[str, Any]:
        """
        Orchestrates a multi-stage (e.g. 9-12 stages) epic narrative outlook.
        """
        if randomize_realm and get_location_manager:
            active_locs = get_location_manager().get_active_locations()
            if active_locs:
                realm_id = random.choice(active_locs).id

        if randomize_characters and get_character_manager:
            active_chars = get_character_manager().get_active_characters()
            if active_chars:
                k = min(random.randint(2, 3), len(active_chars))
                chosen = random.sample(active_chars, k)
                character_ids = [c.id for c in chosen]
        if realm_id and get_location_manager:
            loc = get_location_manager().get_location(realm_id)
            if loc:
                get_location_manager().record_location_feature(realm_id)
                if not loc.is_metaphysical and loc.latitude is not None and loc.longitude is not None:
                    lat = loc.latitude
                    lon = loc.longitude

        astro_context = (
            self._gather_astrology_context(lat, lon, date)
            if include_astrology
            else "The stars wheel in their ancient courses."
        )
        divination_context, divination_raw = self._gather_divination_data(
            include_tarot=include_tarot, include_iching=include_iching
        )
        entity_context = self._select_sacred_entities()

        detailed_context = []
        if realm_id and get_location_manager:
            loc = get_location_manager().get_location(realm_id)
            if loc:
                detailed_context.append(f"Setting / Realm: {loc.name} - {loc.description}")
                if loc.is_metaphysical:
                    detailed_context.append(f"Metaphysical Coordinates: {loc.celestial_coordinates or 'Uncharted'}")
                    detailed_context.append(f"Resonance Frequency: {loc.dimension_frequency or 'Harmonic'} Hz")
                if loc.realm_governor:
                    detailed_context.append(f"Governor / Guardian of this Realm: {loc.realm_governor}")
                if loc.elemental_affinity:
                    detailed_context.append(f"Elemental Affinity: {loc.elemental_affinity}")

        if character_ids and get_character_manager:
            char_texts = []
            for c_id in character_ids:
                char = get_character_manager().get_character(c_id)
                if char:
                    get_character_manager().record_character_feature(c_id)
                    char_texts.append(
                        f"- {char.name} ({char.role.value}): {char.description}. Dialogue Style: {char.dialogue_style}"
                    )
            if char_texts:
                detailed_context.append("Esoteric Characters present:\n" + "\n".join(char_texts))

        if population_ids and get_population_manager:
            pop_texts = []
            for p_id in population_ids:
                pop = get_population_manager().get_population(p_id)
                if pop:
                    pop_texts.append(f"- {pop.name}: {pop.description}. Intended Blessing: {', '.join(pop.intentions)}")
            if pop_texts:
                detailed_context.append(
                    "Beneficiary Target Populations receiving this blessing:\n" + "\n".join(pop_texts)
                )

        if excluded_forces:
            detailed_context.append(f"Negative Forces to exclude/pacify: {', '.join(excluded_forces)}")

        if sensor_context:
            detailed_context.append(f"Quantum Sensor Field / Attunement: {sensor_context}")

        if custom_context:
            detailed_context.append(f"Additional Intentions / Aspiration Context: {custom_context}")

        extra_context_str = "\n\n".join(detailed_context)
        lang_str = ", ".join(languages) if languages else "English"

        epic_narrative = []

        if not self.llm:
            return {"status": "error", "message": "LLM required for epic generation"}
        
        is_fallback = False

        # Stage 1: Invocation
        prompt_1 = f"""Start an epic {stages}-part sutra/tale in the '{genre}' style.
Requested Languages: {lang_str}.
Entities: {entity_context}
Astrology: {astro_context}
Oracle: {divination_context}"""

        if extra_context_str:
            prompt_1 += f"\n\nEsoteric Settings & Universe Context:\n{extra_context_str}"

        if include_dialogue and character_ids:
            prompt_1 += "\n\nCRITICAL INSTRUCTION: Include direct dialogue between the present characters. Write spoken lines that reflect their specific Dialogue Styles (e.g. speaking in koans, regally, or hermetically)."
        else:
            prompt_1 += "\n\nWrite this as a description, vision, or parable. Dedicate the merit and energy of this transmission to the beneficiary target populations if specified."

        prompt_1 += "\n\nWrite Chapter 1: The Invocation and the Setting of the Stage. Establish the cosmic weather and call upon the entities. End with a cliffhanger or mystery."

        chap_1 = self.llm.generate(prompt_1, max_tokens=1000, model=model)
        if chap_1 and "No LLM initialized" in chap_1:
            is_fallback = True
            chap_1 = f"LLM unavailable. Fallback Epic Stage 1:\n\n{entity_context}\n{astro_context}\n{divination_context}"
            
        epic_narrative.append({"chapter": 1, "title": "The Invocation", "content": chap_1})

        # Final chapter
        prompt_final = f"""Context: The epic started with: {chap_1[:200]}...
Now, write the final chapter (Chapter {stages}): The Resolution and Sealing of the Blessing.
Seal the dharani, resolve the oracle's prophecy ({divination_context}), and shower blessings upon the world. Weave in the requested languages: {lang_str}."""

        if extra_context_str:
            prompt_final += f"\n\nEsoteric Settings & Universe Context:\n{extra_context_str}"

        if include_dialogue and character_ids:
            prompt_final += "\n\nCRITICAL INSTRUCTION: Include direct dialogue between the present characters. Write spoken lines that reflect their specific Dialogue Styles."

        if is_fallback:
            chap_final = f"LLM unavailable. Fallback Epic Final Stage:\n\nMay this transmission bring peace to all beings."
        else:
            chap_final = self.llm.generate(prompt_final, max_tokens=1500, model=model)
            if chap_final and "No LLM initialized" in chap_final:
                chap_final = f"LLM unavailable. Fallback Epic Final Stage:\n\nMay this transmission bring peace to all beings."
                
        epic_narrative.append({"chapter": stages, "title": "The Sealing", "content": chap_final})

        return {
            "status": "success",
            "type": "epic",
            "stages_generated": 2,  # simplified for sync return
            "astrology_used": astro_context,
            "divination_used": divination_context,
            "divination_raw": divination_raw,
            "entities_used": entity_context,
            "narrative_parts": epic_narrative,
        }
