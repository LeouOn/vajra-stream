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
    from backend.core.services.sigil_service import sigil_service
except ImportError:
    sigil_service = None

try:
    from core.radionics_engine import RadionicsAnalyzer, SignatureCalculator
except ImportError:
    RadionicsAnalyzer = None
    SignatureCalculator = None

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

        self.sigil = sigil_service
        if RadionicsAnalyzer and SignatureCalculator:
            self.radionics_analyzer = RadionicsAnalyzer()
            self.signature_calc = SignatureCalculator()
        else:
            self.radionics_analyzer = None
            self.signature_calc = None

    def _calculate_radionics_and_sigils(self, genre: str, intention: str) -> tuple[str, dict]:
        parts = []
        raw = {}

        # 1. Select Kamea & Frequencies based on genre
        genre = genre.lower()
        if genre in ["healing", "peace"]:
            kamea = "jupiter"
            freq = "528Hz (DNA Repair) & 852Hz (Spiritual Order)"
        elif genre in ["victory", "dharani"]:
            kamea = "mars"
            freq = "396Hz (Liberation) & 126.22Hz (Sun)"
        elif genre in ["alchemist"]:
            kamea = "saturn"
            freq = "963Hz (Divine Consciousness)"
        else:
            kamea = "saturn"
            freq = "432Hz (Harmonic Resonance)"

        parts.append(f"Vibrational Frequencies locked to {freq}.")
        parts.append(f"Kamea Grid Selected: The Planetary Square of {kamea.capitalize()}.")

        # 2. Calculate Signature Rates
        if self.signature_calc and self.radionics_analyzer:
            sig_rate = self.signature_calc.text_to_rate(intention, num_dials=3)
            parts.append(f"Base Radionic Signature Rate: {sig_rate}")

            balancing = self.radionics_analyzer.find_balancing_rates(intention, num_rates=1)
            if balancing:
                parts.append(f"Complementary Balancing Rate: {balancing[0]}")

            raw["rates"] = {"signature": sig_rate.to_dict(), "balancing": [r.to_dict() for r in balancing]}

        # 3. Trace Sigil Coordinates
        if self.sigil:
            coords = self.sigil.text_to_coordinates(intention, kamea)
            reduced_text = self.sigil.reduce_text(intention)
            coord_str = " -> ".join([f"({c['x']},{c['y']})" for c in coords])
            parts.append(
                f"Sigil traced over {kamea.capitalize()} grid via reduction '{reduced_text}'. Coordinates: {coord_str}"
            )
            raw["sigil"] = {"kamea": kamea, "reduced": reduced_text, "coordinates": coords}

        return " ".join(parts), raw

    def _load_sacred_entities(self) -> dict[str, Any]:
        path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "sacred_entities.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _gather_astrology_context(
        self, lat: float, lon: float, date: datetime = None,
        natal_dt: datetime | None = None,
        natal_location: tuple[float, float] | None = None,
    ) -> str:
        if not self.astro_engine:
            return "Astrological alignment: The stars dance in unknown but auspicious patterns."
        if not hasattr(self.astro_engine, "calculate_chart"):
            return "Astrological alignment: The celestial calculator is currently unavailable."
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

            # --- Transit-to-Natal Aspects ---
            # The single biggest astrology quality gap: previously the LLM
            # only saw where planets ARE right now (transit-to-transit),
            # never how they interact with the birth chart. If a natal chart
            # is provided, compute transit-to-natal aspects and inject the
            # most exact ones so the LLM can write "Transit Saturn squares
            # your natal Moon" instead of generic "Saturn is in Aries".
            if natal_dt and natal_location:
                try:
                    transit_aspects = self.astro_engine.get_transits_to_natal(
                        natal_dt, natal_location, target_date
                    )
                    if transit_aspects:
                        # Filter to harmonious + challenging (skip cusp-only)
                        notable = [
                            a for a in transit_aspects
                            if a.get("aspect") in ("Conjunction", "Trine", "Sextile", "Square", "Opposition")
                        ][:7]
                        if notable:
                            tn_lines = [
                                f"  Transit {a['transit_planet'].title()} {a['aspect']} "
                                f"Natal {a['natal_planet'].title()} "
                                f"(orb {a['orb']:.1f}°)"
                                for a in notable
                            ]
                            lines.append("Transit-to-Natal Aspects:\n" + "\n".join(tn_lines))
                except Exception:
                    pass  # transit-to-natal is optional enrichment

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

    def _gather_divination_data(
        self, include_tarot: bool = True, include_iching: bool = True, include_geomancy: bool = True
    ) -> tuple[str, dict]:
        if not self.divination:
            return "The oracles remain silent.", {}
        parts = []
        raw = {}
        try:
            if include_tarot:
                tarot = self.divination.draw_tarot(1)[0]
                tarot_desc = f"The Tarot reveals {tarot['name']} ({tarot['orientation']}). Meaning: {tarot['meaning']}."
                if tarot.get("hebrew"):
                    tarot_desc += (
                        f" Letter: {tarot['hebrew']}, Ruler: {tarot.get('ruler')}, Element: {tarot.get('element')}."
                    )
                parts.append(tarot_desc)
                raw["tarot"] = {
                    "name": tarot.get("name"),
                    "orientation": tarot.get("orientation"),
                    "meaning": tarot.get("meaning"),
                    "hebrew": tarot.get("hebrew"),
                    "ruler": tarot.get("ruler"),
                    "svg": tarot.get("svg"),
                }
            if include_iching:
                iching = self.divination.cast_i_ching()
                primary_hex = iching.get("primary", {})
                relating_hex = iching.get("relating", {})
                lines = iching.get("changing_lines", [])

                iching_desc = f"The I Ching casts Hexagram {primary_hex.get('name')}: {primary_hex.get('meaning')}."
                if lines:
                    iching_desc += f" Changing lines {lines} transform it into Hexagram {relating_hex.get('name')}."
                parts.append(iching_desc)
                raw["iching"] = {
                    "name": primary_hex.get("name"),
                    "meaning": primary_hex.get("meaning"),
                    "changing_lines": lines,
                    "relating_name": relating_hex.get("name"),
                    "svg": iching.get("svg"),
                }
            if include_geomancy and hasattr(self.divination, "cast_geomancy"):
                geomancy = self.divination.cast_geomancy()
                figs = geomancy.get("figures", {})
                m1, m2, m3, m4 = figs.get("Mother 1"), figs.get("Mother 2"), figs.get("Mother 3"), figs.get("Mother 4")
                judge = figs.get("Judge")
                if m1 and judge:
                    geo_desc = f"Geomancy cast shield. Mothers: {m1['name']}, {m2['name']}, {m3['name']}, {m4['name']}. Judge: {judge['name']} ({judge['meaning']})."
                    parts.append(geo_desc)
                    raw["geomancy"] = geomancy

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

        # Rich entity context — previously only name + dharani_mantra were
        # injected, leaving the qualities/element/description/purpose fields
        # loaded from sacred_entities.json silently discarded. These rich
        # descriptions give the LLM the flavor it needs to write compelling,
        # entity-specific invocations rather than generic mystical filler.
        parts = [f"Under the auspices of {buddha['name']}, Buddha of the Fortunate Eon."]
        if buddha.get("qualities"):
            parts.append(f"  Qualities: {buddha['qualities']}")
        if buddha.get("element"):
            parts.append(f"  Elemental Nature: {buddha['element']}")

        parts.append(f"Invoking the Yidam {yidam['name']} with the dharani: {yidam['dharani_mantra']}.")
        if yidam.get("description"):
            parts.append(f"  Nature: {yidam['description']}")
        if yidam.get("purpose"):
            parts.append(f"  Purpose: {yidam['purpose']}")

        return " ".join(parts)

    def _debug_log_prompt(self, prompt: str, genre: str, lat: float, lon: float) -> str:
        """Write the full LLM prompt to a debug file and print summary to console."""
        filename = ""
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
        return filename

    def _debug_log_response(self, filename: str, result: str, error: str = None) -> None:
        """Append the LLM response (or error) to the debug file."""
        if not filename:
            return
        try:
            with open(filename, "a", encoding="utf-8") as f:
                f.write("\n\n# LLM Response Log\n")
                if error:
                    f.write(f"# ERROR Encountered:\n{error}\n")
                else:
                    f.write(f"# Response length: {len(result) if result else 0} chars\n")
                    f.write(f"{'=' * 70}\n\n")
                    f.write(result if result else "[Empty Response]")
                    f.write(f"\n\n{'=' * 70}\n")
                    f.write("# End of response\n")
        except Exception:
            pass

    def evaluate_ritual(self, prompt: str, outlook_text: str, model: str = None) -> dict:
        """The Critic Model: evaluate a generated ritual for esoteric resonance."""
        if not self.llm:
            return {"score": 5, "feedback": "LLM not available for critique."}

        critic_prompt = f"""You are a Master Esoteric Critic.
Read the original prompt and the generated ritual narrative. Score the resonance, alignment, and esoteric depth from 1 to 10.
Provide a brief feedback summary.
Format your output EXACTLY as:
SCORE: [number]
FEEDBACK: [summary]

Original Prompt:
{prompt[:1000]}...

Generated Ritual:
{outlook_text[:2000]}...
"""
        try:
            result = self.llm.generate(critic_prompt, max_tokens=500, temperature=0.3, model=model)
            if not result or "No LLM initialized" in result:
                return {"score": 5, "feedback": "LLM critique unavailable."}

            score = 5
            feedback = result
            for line in result.split("\n"):
                if line.startswith("SCORE:"):
                    try:
                        score = int(line.split(":")[1].strip())
                    except ValueError:
                        pass
                elif line.startswith("FEEDBACK:"):
                    feedback = line.split(":", 1)[1].strip()
            return {"score": score, "feedback": feedback}
        except Exception as e:
            return {"score": 5, "feedback": f"Critic failed: {e}"}

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
        include_geomancy: bool = True,
        randomize_realm: bool = False,
        randomize_characters: bool = False,
        sensor_context: str | None = None,
        natal_dt: datetime | None = None,
        natal_location: tuple[float, float] | None = None,
    ) -> dict[str, Any]:
        """
        Generates a dense, 300-3000 token single-pass narrative outlook.

        ``natal_dt`` and ``natal_location``: if provided, transit-to-natal
        aspects are computed and injected into the astrology context so the
        LLM can reference "Transit Saturn squares your natal Moon" rather
        than only "Saturn is in Aries".
        """
        if randomize_realm and get_location_manager:
            active_locs = get_location_manager().get_active_locations()
            if active_locs:
                # Weighted random by priority — higher-priority sacred sites
                # (Mount Kailash priority 8, Heavenly Court priority 10) are
                # picked more often than lower-priority ones. Previously
                # used unweighted random.choice giving equal odds to all.
                weights = [max(getattr(l, "priority", 5), 1) for l in active_locs]
                realm_id = random.choices(active_locs, weights=weights, k=1)[0].id

        if randomize_characters and get_character_manager:
            active_chars = get_character_manager().get_active_characters()
            if active_chars:
                # Same weighted approach for characters.
                weights = [max(getattr(c, "priority", 5), 1) for c in active_chars]
                k = min(random.randint(2, 3), len(active_chars))
                chosen = random.choices(active_chars, weights=weights, k=k)
                character_ids = [c.id for c in chosen]
        if realm_id and get_location_manager:
            loc = get_location_manager().get_location(realm_id)
            if loc:
                get_location_manager().record_location_feature(realm_id)
                if not loc.is_metaphysical and loc.latitude is not None and loc.longitude is not None:
                    lat = loc.latitude
                    lon = loc.longitude

        astro_context = (
            self._gather_astrology_context(lat, lon, date, natal_dt=natal_dt, natal_location=natal_location)
            if include_astrology
            else "The stars wheel in their ancient courses."
        )
        divination_context, divination_raw = self._gather_divination_data(
            include_tarot=include_tarot, include_iching=include_iching, include_geomancy=include_geomancy
        )

        # Calculate Radionics and Sigils
        intention = custom_context if custom_context else f"Blessing for {lat},{lon}"
        radionics_context, radionics_raw = self._calculate_radionics_and_sigils(genre, intention)
        divination_raw.update(radionics_raw)

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
                # Previously dropped — these fields give the LLM the
                # astrological signature and contextual notes of the sacred
                # site, e.g. "Saturn conjunct Midheaven" for Mount Kailash
                # or "Primary Buddhist pure land" for Sukhavati.
                astro_anchor = getattr(loc, "astrological_anchor", None)
                if astro_anchor:
                    detailed_context.append(f"Astrological Anchor: {astro_anchor}")
                loc_notes = getattr(loc, "notes", None)
                if loc_notes:
                    detailed_context.append(f"Realm Notes: {loc_notes}")

        if character_ids and get_character_manager:
            char_texts = []
            for c_id in character_ids:
                char = get_character_manager().get_character(c_id)
                if char:
                    get_character_manager().record_character_feature(c_id)
                    char_desc = (
                        f"- {char.name} ({char.role.value}): {char.description}. Dialogue Style: {char.dialogue_style}"
                    )
                    if getattr(char, "grounding_sense", None):
                        char_desc += f". Grounding: {char.grounding_sense}"
                    if getattr(char, "channeling_state", None):
                        char_desc += f". Channeling: {char.channeling_state}"
                    if getattr(char, "anchoring_ritual", None):
                        char_desc += f". Anchoring: {char.anchoring_ritual}"
                    char_texts.append(char_desc)
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

        prompt = f"""Write a profound, sutra-style narrative outlook and blessing formatted as a 5-part magical ritual operation.

Genre/Style: {genre.capitalize()}
Requested Languages: {lang_str} (Weave these languages gracefully into the text, perhaps using them for invocations, mantras, or key poetic phrases, with English as the main narrative bridge unless otherwise specified).

Contexts to weave deeply into the imagery:
- Astrological: {astro_context}
- Oracle/Divination: {divination_context}
- Radionics/Sigils: {radionics_context}
- Sacred Entities: {entity_context}"""

        if extra_context_str:
            prompt += f"\n\nEsoteric Settings & Universe Context:\n{extra_context_str}"

        if include_dialogue and character_ids:
            prompt += "\n\nCRITICAL INSTRUCTION: Include direct dialogue between the present characters. Write spoken lines that reflect their specific Dialogue Styles (e.g. speaking in koans, regally, or hermetically). Ground the ritual in their sensory experience using their specified Grounding Senses, depict them entering their Channeling States, and describe them executing their Anchoring Rituals."

        prompt += """

CRITICAL INSTRUCTION: Your output MUST be structured into exactly these 5 distinct sections with clear headings:
1. I. Invocatio (Awakening & Invocation): Open the spatial directions, activate the planetary hours/nakshatras, and invoke the deities (Sanskrit/Tibetan/Latin mantras).
2. II. Pacificatio (Purification & Pacification): Disperse obstacles and pacify negative forces.
3. III. Attunement (Radionic & Vibrational Lock): Broadcast the specific signature rates and Solfeggio frequencies into the field.
4. IV. Sigillum (Kamea Sigil Trace): Describe the charging of the digital talisman using the grid coordinate pathway provided.
5. V. Dedicatio (Sealing of Merit): Dedicate the generated energy to the target populations or the universe.

The narrative should read like a high-resonance, ceremonial, liturgical grimoire or sutra. Do not simply list the contexts—integrate them seamlessly into this compelling 5-step ritual operation.
Length: 5-8 paragraphs of dense, visionary prose.
"""

        # Debug: log the full prompt for verification
        log_filename = self._debug_log_prompt(prompt, genre, lat, lon)

        # Propagate ``None`` so the registry's pick_best() selects the best
        # HEALTHY registered provider at call time. Hardcoding a provider here
        # caused "Provider 'deepseek' is not registered" when DeepSeek was not
        # configured. See _generate_async() in core/llm/legacy_adapter.py.
        effective_model = model

        print(
            f"[DEBUG generate_single_outlook] model={model!r}, effective_model={effective_model!r}, self.llm={type(self.llm).__name__ if self.llm else 'None'}"
        )
        if self.llm:
            try:
                result = self.llm.generate(
                    prompt=prompt,
                    system_prompt="You are a transcendent oracle and dharma scribe, speaking across eons. Your words heal, transform, and reveal the hidden architecture of reality.",
                    max_tokens=1200,
                    temperature=0.7,
                    model=effective_model,
                )
                if result and "No LLM initialized" in result:
                    result = f"LLM unavailable. Fallback Generation:\n\n{entity_context}\n{astro_context}\n{divination_context}\n\nMay this transmission bring peace."
                self._debug_log_response(log_filename, result)
            except Exception as e:
                self._debug_log_response(log_filename, None, error=str(e))
                result = f"Error during generation: {e}"
        else:
            result = f"LLM unavailable. Fallback Generation:\n\n{entity_context}\n{astro_context}\n{divination_context}\n\nMay this transmission bring peace."
            self._debug_log_response(log_filename, result)

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
        include_geomancy: bool = True,
        randomize_realm: bool = False,
        randomize_characters: bool = False,
        sensor_context: str | None = None,
        natal_dt: datetime | None = None,
        natal_location: tuple[float, float] | None = None,
    ) -> dict[str, Any]:
        """
        Orchestrates a multi-stage (e.g. 9-12 stages) epic narrative outlook.
        """
        # Propagate ``None`` so registry.pick_best() selects the best healthy
        # provider. Hardcoding a provider here caused registration errors when
        # that provider was not configured. See core/llm/legacy_adapter.py.
        epic_model = model

        if randomize_realm and get_location_manager:
            active_locs = get_location_manager().get_active_locations()
            if active_locs:
                # Weighted random by priority — higher-priority sacred sites
                # (Mount Kailash priority 8, Heavenly Court priority 10) are
                # picked more often than lower-priority ones. Previously
                # used unweighted random.choice giving equal odds to all.
                weights = [max(getattr(l, "priority", 5), 1) for l in active_locs]
                realm_id = random.choices(active_locs, weights=weights, k=1)[0].id

        if randomize_characters and get_character_manager:
            active_chars = get_character_manager().get_active_characters()
            if active_chars:
                # Same weighted approach for characters.
                weights = [max(getattr(c, "priority", 5), 1) for c in active_chars]
                k = min(random.randint(2, 3), len(active_chars))
                chosen = random.choices(active_chars, weights=weights, k=k)
                character_ids = [c.id for c in chosen]
        if realm_id and get_location_manager:
            loc = get_location_manager().get_location(realm_id)
            if loc:
                get_location_manager().record_location_feature(realm_id)
                if not loc.is_metaphysical and loc.latitude is not None and loc.longitude is not None:
                    lat = loc.latitude
                    lon = loc.longitude

        astro_context = (
            self._gather_astrology_context(lat, lon, date, natal_dt=natal_dt, natal_location=natal_location)
            if include_astrology
            else "The stars wheel in their ancient courses."
        )
        divination_context, divination_raw = self._gather_divination_data(
            include_tarot=include_tarot, include_iching=include_iching, include_geomancy=include_geomancy
        )

        intention = custom_context if custom_context else f"Blessing for {lat},{lon}"
        radionics_context, radionics_raw = self._calculate_radionics_and_sigils(genre, intention)
        divination_raw.update(radionics_raw)

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
                # Previously dropped — these fields give the LLM the
                # astrological signature and contextual notes of the sacred
                # site, e.g. "Saturn conjunct Midheaven" for Mount Kailash
                # or "Primary Buddhist pure land" for Sukhavati.
                astro_anchor = getattr(loc, "astrological_anchor", None)
                if astro_anchor:
                    detailed_context.append(f"Astrological Anchor: {astro_anchor}")
                loc_notes = getattr(loc, "notes", None)
                if loc_notes:
                    detailed_context.append(f"Realm Notes: {loc_notes}")

        if character_ids and get_character_manager:
            char_texts = []
            council_intentions = []

            for c_id in character_ids:
                char = get_character_manager().get_character(c_id)
                if char:
                    get_character_manager().record_character_feature(c_id)
                    char_desc = (
                        f"- {char.name} ({char.role.value}): {char.description}. Dialogue Style: {char.dialogue_style}"
                    )
                    if getattr(char, "grounding_sense", None):
                        char_desc += f". Grounding: {char.grounding_sense}"
                    if getattr(char, "channeling_state", None):
                        char_desc += f". Channeling: {char.channeling_state}"
                    if getattr(char, "anchoring_ritual", None):
                        char_desc += f". Anchoring: {char.anchoring_ritual}"
                    char_texts.append(char_desc)

                    # Part 3: The Debate Model (Autonomous Council)
                    if include_dialogue and self.llm:
                        council_prompt = (
                            f"You are the character {char.name}, a {char.role.value}.\n"
                            f"Description: {char.description}\n"
                            f"Grounding: {getattr(char, 'grounding_sense', 'the earth beneath')}\n"
                            f"Channeling: {getattr(char, 'channeling_state', 'open as a vessel')}\n"
                            f"In 2-3 sentences, using your dialogue style '{char.dialogue_style}', declare your intention for this upcoming ritual blessing. "
                            "Do not write anything else, just your spoken dialogue."
                        )
                        try:
                            intention = self.llm.generate(
                                council_prompt, max_tokens=150, temperature=0.8, model=epic_model
                            )
                            if intention and "No LLM" not in intention:
                                council_intentions.append(f'{char.name} declares: "{intention.strip()}"')
                        except Exception:
                            pass

            if char_texts:
                detailed_context.append("Esoteric Characters present:\n" + "\n".join(char_texts))
            if council_intentions:
                detailed_context.append(
                    "Character Council Intentions (Weave these into the narrative):\n" + "\n".join(council_intentions)
                )

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

        # Model resolution is handled per-call by the registry; no hardcoded
        # default here. See epic_model initialization above.
        is_fallback = False

        # Stage 1: Invocation
        prompt_1 = f"""Start an epic {stages}-part sutra/tale in the '{genre}' style.
Requested Languages: {lang_str}.
Entities: {entity_context}
Astrology: {astro_context}
Oracle: {divination_context}
Radionics/Sigils: {radionics_context}"""

        if extra_context_str:
            prompt_1 += f"\n\nEsoteric Settings & Universe Context:\n{extra_context_str}"

        if include_dialogue and character_ids:
            prompt_1 += "\n\nCRITICAL INSTRUCTION: Include direct dialogue between the present characters. Write spoken lines that reflect their specific Dialogue Styles (e.g. speaking in koans, regally, or hermetically)."
            prompt_1 += " Also, ground their presence using their specified Grounding Senses, describe them entering their Channeling States, and depict them performing their Anchoring Rituals."
        else:
            prompt_1 += "\n\nWrite this as a description, vision, or parable. Dedicate the merit and energy of this transmission to the beneficiary target populations if specified."

        prompt_1 += "\n\nWrite Chapter 1: The Invocation and the Setting of the Stage. Establish the cosmic weather and call upon the entities. End with a cliffhanger or mystery."

        log_filename_1 = self._debug_log_prompt(prompt_1, f"{genre}_epic_ch1", lat, lon)
        try:
            chap_1 = self.llm.generate(prompt_1, max_tokens=2000, temperature=0.7, model=epic_model)
            if chap_1 and "No LLM initialized" in chap_1:
                is_fallback = True
                chap_1 = f"LLM unavailable. Fallback Epic Stage 1:\n\n{entity_context}\n{astro_context}\n{divination_context}"
            self._debug_log_response(log_filename_1, chap_1)
        except Exception as e:
            self._debug_log_response(log_filename_1, None, error=str(e))
            chap_1 = f"Error generating Chapter 1: {e}"
            is_fallback = True

        epic_narrative.append({"chapter": 1, "title": "The Invocation", "content": chap_1})

        # Final chapter
        prompt_final = f"""Context: The epic started with: {chap_1[:200]}...
Now, write the final chapter (Chapter {stages}): The Resolution and Sealing of the Blessing.
Seal the dharani, resolve the oracle's prophecy ({divination_context}), and shower blessings upon the world. Weave in the requested languages: {lang_str}."""

        if extra_context_str:
            prompt_final += f"\n\nEsoteric Settings & Universe Context:\n{extra_context_str}"

        if include_dialogue and character_ids:
            prompt_final += "\n\nCRITICAL INSTRUCTION: Include direct dialogue between the present characters. Write spoken lines that reflect their specific Dialogue Styles."
            prompt_final += " Again, emphasize their physical Grounding Senses and describe how they seal the ritual using their unique Anchoring Rituals."

        log_filename_final = self._debug_log_prompt(prompt_final, f"{genre}_epic_final", lat, lon)

        if is_fallback:
            chap_final = (
                "LLM unavailable. Fallback Epic Final Stage:\n\nMay this transmission bring peace to all beings."
            )
            self._debug_log_response(log_filename_final, chap_final)
        else:
            try:
                chap_final = self.llm.generate(prompt_final, max_tokens=2000, temperature=0.7, model=epic_model)
                if chap_final and "No LLM initialized" in chap_final:
                    chap_final = "LLM unavailable. Fallback Epic Final Stage:\n\nMay this transmission bring peace to all beings."
                self._debug_log_response(log_filename_final, chap_final)
            except Exception as e:
                self._debug_log_response(log_filename_final, None, error=str(e))
                chap_final = f"Error generating final chapter: {e}"

        epic_narrative.append({"chapter": stages, "title": "The Sealing", "content": chap_final})

        # Part 1: The Critic Evaluation
        if not is_fallback:
            eval_result = self.evaluate_ritual(prompt_1, chap_1, epic_model)
            # If the score is too low, we could auto-correct, but for now we'll just log it
            print(f"[CRITIC] Stage 1 Score: {eval_result['score']} - {eval_result['feedback']}")

        # Part 1: Reward Characters (EXP)
        if character_ids and get_character_manager:
            for c_id in character_ids:
                try:
                    get_character_manager().add_exp_and_log(
                        c_id, 25, f"Participated in an Epic Outlook in the {genre} genre."
                    )
                except Exception as e:
                    print(f"Failed to add exp: {e}")

        return {
            "status": "success",
            "type": "epic",
            "stages_generated": 2,  # simplified for sync return
            "astrology_used": astro_context,
            "divination_used": divination_context,
            "divination_raw": divination_raw,
            "entities_used": entity_context,
            "narrative_parts": epic_narrative,
            "critic_score": eval_result.get("score", 0) if not is_fallback else 0,
        }
