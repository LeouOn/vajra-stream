"""
Radionics Analysis Engine

This module implements core radionics functionality including:
- Rate analysis and generation
- General Vitality (GV) draws
- Signature-to-rate conversion
- Rate database management
- Random number generation for rate selection
- Broadcasting feedback loops

Inspired by AetherOnePi and traditional radionics practices.

Provenance (docs/DEVELOPMENT_ROADMAP.md, "the honest instrument"): the RNG
here is the digital analog of the stick pad or pendulum. GV values, drawn
potencies and drawn dial values are ``draw`` values, a divinatory method and
never a measurement. Signature rates are ``computed`` (deterministic from the
text). Every structure returned by this module says which is which through a
``provenance`` mapping of field name to one of ``core.provenance.PROVENANCE_KINDS``.
"""

import hashlib
import json
import os
import random
import secrets
import time
from datetime import datetime

import numpy as np

from core.provenance import COMPUTED, DRAW

# Every number in a GV statistics block derives from RNG draws.
GV_STATS_PROVENANCE: dict[str, str] = {
    "mean": DRAW,
    "median": DRAW,
    "std": DRAW,
    "min": DRAW,
    "max": DRAW,
    "measurements": DRAW,
}

GV_DRAW_NOTE = (
    "GV is drawn with an RNG, the digital analog of the stick pad or pendulum. "
    "It is a divinatory reading, not a measurement, and never a diagnosis."
)


class RadionicsRate:
    """A radionics rate — a numerical signature for an energy pattern, condition, or remedy.

    Rates are the fundamental unit of radionics analysis. They can be single,
    dual, triple, or multi-dial values that represent specific energetic
    signatures. This class provides serialisation (``to_dict`` / ``from_dict``)
    for persistence and comparison operators for rate matching.

    Attributes:
        values: List of integer dial values (e.g. ``[45, 72]``).
        name: Human-readable label.
        description: What this rate represents.
        category: Grouping (``"remedy"``, ``"condition"``, ``"organ"``, etc.).
        potency: Resonance strength (0.0–1.0). When the engine sets it, it is
            a draw (see ``provenance``), not a measurement.
        provenance: Field name -> provenance kind, e.g.
            ``{"values": "computed"}`` or ``{"values": "draw", "potency": "draw"}``.
        timestamp: When this rate was created.
    """

    def __init__(
        self,
        values: list[int],
        name: str = "",
        description: str = "",
        category: str = "",
        potency: float = 0.0,
        provenance: dict[str, str] | None = None,
    ):
        """
        Initialize a radionics rate.

        Args:
            values: List of integers representing the rate (e.g., [45, 72])
            name: Name/label for this rate
            description: Description of what this rate represents
            category: Category (remedy, condition, organ, etc.)
            potency: Potency/resonance (0.0-1.0); drawn when set by the engine
            provenance: Field name -> provenance kind (``draw``, ``computed``, ...)
        """
        self.values = values
        self.name = name
        self.description = description
        self.category = category
        self.potency = potency
        self.provenance: dict[str, str] = dict(provenance or {})
        self.timestamp = datetime.now()

    def __str__(self) -> str:
        rate_str = "-".join(str(v) for v in self.values)
        if self.name:
            return f"{self.name}: {rate_str}"
        return rate_str

    def __repr__(self) -> str:
        return f"RadionicsRate({self.values}, name='{self.name}', potency={self.potency:.2f})"

    def to_dict(self) -> dict:
        """Convert to dictionary for storage/serialization."""
        return {
            "values": self.values,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "potency": self.potency,
            "provenance": dict(self.provenance),
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RadionicsRate":
        """Create from dictionary."""
        rate = cls(
            values=data["values"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=data.get("category", ""),
            potency=data.get("potency", 0.0),
            provenance=data.get("provenance"),
        )
        if "timestamp" in data:
            rate.timestamp = datetime.fromisoformat(data["timestamp"])
        return rate


class RandomNumberGenerator:
    """
    Random number generator for radionics rate selection.

    Supports multiple modes:
    - Secure pseudo-random (cryptographic, ``secrets``)
    - "quantum": a Mersenne Twister seeded from ``os.urandom`` plus the clock.
      The name is historical; no quantum source is involved.
    - Intention-modulated (seeded by intention text, reproducible)

    Whatever the mode, the output is a draw. Each call uses its own
    ``random.Random`` instance so seeding never touches the process-wide RNG.
    """

    def __init__(self, mode: str = "secure"):
        """
        Initialize RNG.

        Args:
            mode: 'secure', 'quantum', or 'intention'
        """
        self.mode = mode

    def generate(self, min_val: int = 0, max_val: int = 100, count: int = 1, intention: str = "") -> list[int]:
        """
        Generate random numbers for rate selection.

        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)
            count: How many numbers to generate
            intention: Optional intention text for seeding

        Returns:
            List of random integers
        """
        if self.mode == "secure":
            return [secrets.randbelow(max_val - min_val + 1) + min_val for _ in range(count)]

        elif self.mode == "quantum":
            # System entropy plus the clock seeds a local PRNG.
            seed = int.from_bytes(os.urandom(8), "big") + int(time.time() * 1000000)
            rng = random.Random(seed)
            return [rng.randint(min_val, max_val) for _ in range(count)]

        elif self.mode == "intention":
            # Seed with intention text for reproducible but intention-specific randomness
            if intention:
                seed = int(hashlib.sha256(intention.encode()).hexdigest(), 16) % (2**32)
                rng = random.Random(seed)
            else:
                rng = random.Random()
            return [rng.randint(min_val, max_val) for _ in range(count)]

        else:
            # Fallback to an unseeded local PRNG
            rng = random.Random()
            return [rng.randint(min_val, max_val) for _ in range(count)]

    def generate_float(self, min_val: float = 0.0, max_val: float = 1.0, count: int = 1) -> list[float]:
        """Generate random floats (draws)."""
        if self.mode == "secure":
            return [min_val + secrets.randbelow(10000) / 10000.0 * (max_val - min_val) for _ in range(count)]
        else:
            rng = random.Random()
            return [rng.uniform(min_val, max_val) for _ in range(count)]


class SignatureCalculator:
    """
    Converts text signatures (names, intentions, etc.) into radionics rates.

    Uses multiple algorithms:
    - Hash-based (SHA-256)
    - Gematria-style (letter values)
    - Phonetic (sound-based)
    - Resonance (frequency-based)
    """

    def __init__(self):
        # Letter value mappings for gematria-style calculations
        self.english_gematria = {chr(i): i - 64 for i in range(65, 91)}  # A=1, B=2, etc.

    def text_to_rate(
        self, text: str, num_dials: int = 3, max_value: int = 100, algorithm: str = "hash"
    ) -> RadionicsRate:
        """
        Convert text signature to radionics rate.

        Args:
            text: Input text (name, intention, etc.)
            num_dials: Number of rate values to generate (2-5 typical)
            max_value: Maximum value for each dial (100 traditional)
            algorithm: 'hash', 'gematria', 'phonetic', or 'mixed'

        Returns:
            RadionicsRate object
        """
        text = text.strip().upper()

        if algorithm == "hash":
            return self._hash_algorithm(text, num_dials, max_value)
        elif algorithm == "gematria":
            return self._gematria_algorithm(text, num_dials, max_value)
        elif algorithm == "phonetic":
            return self._phonetic_algorithm(text, num_dials, max_value)
        elif algorithm == "mixed":
            return self._mixed_algorithm(text, num_dials, max_value)
        else:
            return self._hash_algorithm(text, num_dials, max_value)

    def _hash_algorithm(self, text: str, num_dials: int, max_value: int) -> RadionicsRate:
        """Use cryptographic hash for consistent rate generation."""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        values = []
        for i in range(num_dials):
            # Take different bytes from hash for each dial
            byte_val = hash_bytes[i % len(hash_bytes)]
            dial_val = int((byte_val / 255.0) * max_value)
            values.append(dial_val)

        return RadionicsRate(
            values=values,
            name=text,
            description=f"Hash-generated rate for '{text}'",
            category="signature",
            provenance={"values": COMPUTED},
        )

    def _gematria_algorithm(self, text: str, num_dials: int, max_value: int) -> RadionicsRate:
        """Use letter values (gematria-style) for rate generation."""
        # Calculate total value
        total = sum(self.english_gematria.get(char, 0) for char in text if char.isalpha())

        values = []
        remaining = total
        for i in range(num_dials):
            if i == num_dials - 1:
                # Last dial gets remainder
                dial_val = remaining % (max_value + 1)
            else:
                # Divide by number of remaining dials
                dial_val = (remaining // (num_dials - i)) % (max_value + 1)
                remaining -= dial_val
            values.append(dial_val)

        return RadionicsRate(
            values=values,
            name=text,
            description=f"Gematria-generated rate for '{text}' (value: {total})",
            category="signature",
            provenance={"values": COMPUTED},
        )

    def _phonetic_algorithm(self, text: str, num_dials: int, max_value: int) -> RadionicsRate:
        """Use phonetic properties for rate generation."""
        # Vowels and consonants have different weights
        vowels = "AEIOU"
        vowel_count = sum(1 for char in text if char in vowels)
        consonant_count = sum(1 for char in text if char.isalpha() and char not in vowels)

        values = []
        # First dial: vowel ratio
        if len(text) > 0:
            values.append(int((vowel_count / len(text)) * max_value))

        # Second dial: consonant density
        if num_dials > 1:
            values.append(int((consonant_count / max(len(text), 1)) * max_value))

        # Remaining dials: hash-based
        if num_dials > 2:
            hash_rate = self._hash_algorithm(text, num_dials - 2, max_value)
            values.extend(hash_rate.values)

        return RadionicsRate(
            values=values,
            name=text,
            description=f"Phonetic-generated rate for '{text}'",
            category="signature",
            provenance={"values": COMPUTED},
        )

    def _mixed_algorithm(self, text: str, num_dials: int, max_value: int) -> RadionicsRate:
        """Combine multiple algorithms for robust rate generation."""
        hash_rate = self._hash_algorithm(text, num_dials, max_value)
        gematria_rate = self._gematria_algorithm(text, num_dials, max_value)

        # Average the two methods
        values = []
        for i in range(num_dials):
            avg_val = (hash_rate.values[i] + gematria_rate.values[i]) // 2
            values.append(avg_val)

        return RadionicsRate(
            values=values,
            name=text,
            description=f"Mixed-algorithm rate for '{text}'",
            category="signature",
            provenance={"values": COMPUTED},
        )


class GeneralVitalityMeter:
    """
    Draws General Vitality (GV), the core resonance reading in radionics.

    GV is a **draw**: an RNG stands in for the stick pad or pendulum. The
    class keeps its historical name and ``measure`` method for API stability,
    but nothing here measures anything. Readings are framed accordingly.

    GV scale: 0-1000. Traditional reading bands, as read in the stick-pad
    tradition (see :func:`gv_band`):
    - 0-200: very low vitality
    - 200-400: low vitality
    - 400-600: balanced vitality
    - 600-800: high vitality
    - 800-1000: very high vitality
    """

    def __init__(self, rng: RandomNumberGenerator | None = None):
        """Initialize GV meter."""
        self.rng = rng or RandomNumberGenerator(mode="quantum")
        self.history = []

    def measure(self, subject: str = "", context: dict = None) -> float:
        """
        Draw a General Vitality value.

        In traditional radionics this reading is taken with a stick pad or
        pendulum. Here an RNG draw takes that role, optionally nudged by
        context (moon phase, hour, intention length). The result is a draw,
        not a measurement.

        Args:
            subject: What the draw is for (person, intention, etc.)
            context: Optional context that nudges the draw

        Returns:
            Drawn GV value (0-1000)
        """
        # Base draw from the engine RNG
        base_gv = self.rng.generate(min_val=0, max_val=1000, count=1)[0]

        # Apply context-based adjustments if provided
        if context:
            adjustments = 0

            # Astrological factors
            if "moon_phase" in context:
                phase = context["moon_phase"]
                if "full" in phase.lower():
                    adjustments += 50  # Full moon boost
                elif "new" in phase.lower():
                    adjustments -= 30  # New moon reduction

            # Time of day factors
            if "hour" in context:
                hour = context["hour"]
                if 4 <= hour <= 6:  # Brahma Muhurta
                    adjustments += 40
                elif 12 <= hour <= 13:  # Solar noon
                    adjustments += 30

            # Intention clarity
            if "intention_length" in context:
                # Longer, more detailed intentions may correlate with clarity
                length = context["intention_length"]
                if length > 50:
                    adjustments += 20

            # Apply adjustments with bounds
            base_gv = max(0, min(1000, base_gv + adjustments))

        # Record the draw
        draw = {
            "gv": base_gv,
            "subject": subject,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
            "provenance": {"gv": DRAW},
        }
        self.history.append(draw)

        return base_gv

    def measure_multiple(self, count: int = 10, subject: str = "", context: dict = None) -> dict:
        """
        Take several GV draws and return their statistics.

        Args:
            count: Number of draws
            subject: What the draws are for
            context: Optional context

        Returns:
            Dictionary with mean, median, std, min, max, the raw draws and a
            ``provenance`` mapping marking every value as a draw.
        """
        measurements = [self.measure(subject, context) for _ in range(count)]

        return {
            "mean": np.mean(measurements),
            "median": np.median(measurements),
            "std": np.std(measurements),
            "min": min(measurements),
            "max": max(measurements),
            "measurements": measurements,
            "count": count,
            "provenance": dict(GV_STATS_PROVENANCE),
        }

    def interpret_gv(self, gv: float) -> str:
        """
        Read a drawn GV value in the stick-pad tradition.

        The wording always names the value as drawn and frames the band as a
        traditional reading. It never claims a measurement or a diagnosis.

        Args:
            gv: Drawn GV value (0-1000)

        Returns:
            Reading string, e.g. ``"Drawn GV 812 — in the stick-pad tradition
            this reads as very high vitality."``
        """
        return f"Drawn GV {gv:.0f} — in the stick-pad tradition this reads as {gv_band(gv)} vitality."


def gv_band(gv: float) -> str:
    """Traditional reading band for a drawn GV value (0-1000)."""
    if gv >= 800:
        return "very high"
    elif gv >= 600:
        return "high"
    elif gv >= 400:
        return "balanced"
    elif gv >= 200:
        return "low"
    else:
        return "very low"


class RateDatabase:
    """
    Manages collections of radionics rates.

    Supports:
    - Loading/saving rate collections
    - Searching and filtering rates
    - Category management
    - Rate watchlists
    """

    def __init__(self, database_path: str | None = None):
        """
        Initialize rate database.

        Args:
            database_path: Path to JSON database file
        """
        self.rates: list[RadionicsRate] = []
        self.database_path = database_path

        if database_path and os.path.exists(database_path):
            self.load(database_path)

    def add_rate(self, rate: RadionicsRate):
        """Add a rate to the database."""
        self.rates.append(rate)

    def find_by_name(self, name: str, exact: bool = False) -> list[RadionicsRate]:
        """
        Find rates by name.

        Args:
            name: Name to search for
            exact: If True, require exact match; if False, substring match

        Returns:
            List of matching rates
        """
        name_lower = name.lower()
        if exact:
            return [r for r in self.rates if r.name.lower() == name_lower]
        else:
            return [r for r in self.rates if name_lower in r.name.lower()]

    def find_by_category(self, category: str) -> list[RadionicsRate]:
        """Find all rates in a category."""
        category_lower = category.lower()
        return [r for r in self.rates if r.category.lower() == category_lower]

    def get_categories(self) -> list[str]:
        """Get all unique categories."""
        return sorted(list(set(r.category for r in self.rates if r.category)))

    def save(self, path: str | None = None):
        """Save database to JSON file."""
        save_path = path or self.database_path
        if not save_path:
            raise ValueError("No database path specified")

        data = {
            "rates": [r.to_dict() for r in self.rates],
            "saved_at": datetime.now().isoformat(),
            "count": len(self.rates),
        }

        with open(save_path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str):
        """Load database from JSON file."""
        with open(path) as f:
            data = json.load(f)

        self.rates = [RadionicsRate.from_dict(r) for r in data.get("rates", [])]
        self.database_path = path

    def export_watchlist(self, path: str, category: str | None = None):
        """
        Export rates to CSV watchlist format.

        Args:
            path: Path to CSV file
            category: Optional category filter
        """
        rates_to_export = self.rates
        if category:
            rates_to_export = self.find_by_category(category)

        with open(path, "w") as f:
            f.write("Name,Rate,Category,Description,Potency\n")
            for rate in rates_to_export:
                rate_str = "-".join(str(v) for v in rate.values)
                f.write(f'"{rate.name}","{rate_str}","{rate.category}","{rate.description}",{rate.potency:.3f}\n')

    def import_watchlist(self, path: str):
        """Import rates from CSV watchlist."""
        with open(path) as f:
            # Skip header
            next(f)
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    name = parts[0].strip('"')
                    rate_str = parts[1].strip('"')
                    category = parts[2].strip('"') if len(parts) > 2 else ""
                    description = parts[3].strip('"') if len(parts) > 3 else ""
                    potency = float(parts[4]) if len(parts) > 4 else 0.0

                    values = [int(v) for v in rate_str.split("-")]
                    rate = RadionicsRate(values, name, description, category, potency)
                    self.add_rate(rate)


class RadionicsAnalyzer:
    """
    Core radionics analysis engine.

    Performs:
    - Rate analysis on subjects/targets
    - Resonance detection
    - Pattern analysis
    - Broadcasting recommendations
    """

    def __init__(self, rate_database: RateDatabase | None = None):
        """Initialize analyzer."""
        self.rate_database = rate_database or RateDatabase()
        self.rng = RandomNumberGenerator(mode="quantum")
        self.gv_meter = GeneralVitalityMeter(self.rng)
        self.sig_calculator = SignatureCalculator()
        self.analysis_history = []

    def analyze_subject(self, subject: str, num_rates: int = 10, context: dict = None) -> dict:
        """
        Perform a radionics reading on a subject.

        The signature rate is computed from the subject text. The baseline GV,
        the resonant rates and their potencies are draws (stick-pad analog).
        The result carries a ``provenance`` mapping that says so.

        Args:
            subject: What/who to analyze (name, intention, etc.)
            num_rates: How many rates to generate
            context: Optional context (astrological, temporal, etc.)

        Returns:
            Analysis results dictionary
        """
        print(f"\n🔮 Performing radionics analysis on: {subject}")

        # Draw baseline General Vitality
        print("📊 Drawing General Vitality (stick-pad analog)...")
        gv_stats = self.gv_meter.measure_multiple(count=10, subject=subject, context=context)
        baseline_gv = gv_stats["mean"]

        print(f"   {self.gv_meter.interpret_gv(baseline_gv)}")

        # Generate signature rate for subject
        print("🔢 Generating signature rate...")
        signature_rate = self.sig_calculator.text_to_rate(subject, num_dials=3, algorithm="mixed")
        print(f"   Signature: {signature_rate}")

        # Generate additional resonant rates
        print(f"🎲 Drawing {num_rates} resonant rates...")
        resonant_rates = []
        for i in range(num_rates):
            # Draw the dial values
            values = self.rng.generate(min_val=0, max_val=100, count=3, intention=subject)

            # Draw a potency for the rate. This is the stick-pad step done by
            # RNG: a draw, not a measured resonance.
            test_rate = RadionicsRate(
                values,
                f"Rate-{i + 1}",
                category="generated",
                provenance={"values": DRAW, "potency": DRAW},
            )
            test_rate.potency = self.rng.generate_float(0.0, 1.0, 1)[0]

            resonant_rates.append(test_rate)

        # Sort by potency
        resonant_rates.sort(key=lambda r: r.potency, reverse=True)

        print("   Top 5 resonant rates:")
        for i, rate in enumerate(resonant_rates[:5], 1):
            print(f"      {i}. {rate} (drawn potency: {rate.potency:.2f})")

        # Create analysis result
        result = {
            "subject": subject,
            "timestamp": datetime.now().isoformat(),
            "baseline_gv": baseline_gv,
            "gv_stats": gv_stats,
            "signature_rate": signature_rate.to_dict(),
            "resonant_rates": [r.to_dict() for r in resonant_rates],
            "context": context or {},
            "interpretation": self.gv_meter.interpret_gv(baseline_gv),
            "note": GV_DRAW_NOTE,
            "provenance": {
                "baseline_gv": DRAW,
                "gv_stats": DRAW,
                "signature_rate": COMPUTED,
                "resonant_rates": DRAW,
                "interpretation": DRAW,
            },
        }

        self.analysis_history.append(result)
        return result

    def broadcast_with_feedback(
        self, subject: str, rate: RadionicsRate, duration_seconds: int = 300, check_interval: int = 60
    ) -> dict:
        """
        Hold a rate for a duration while drawing General Vitality at intervals.

        This follows the "auto-mode" concept from AetherOnePi. Nothing is
        emitted from here: no audio, scalar or hardware output happens in this
        loop. It waits and draws GV, so every GV value and the trend are draws.
        The result says so with ``emitted: False`` and a ``provenance`` map.

        Args:
            subject: Who or what the rate is held for
            rate: The rate being held
            duration_seconds: How long to hold
            check_interval: How often to draw GV (seconds)

        Returns:
            Holding results with the drawn GV trend
        """
        print(f"\n📡 Holding rate {rate} for: {subject} (no emission from this loop)")
        print(f"   Duration: {duration_seconds}s, drawing GV every {check_interval}s")

        gv_measurements = []
        start_time = time.time()

        # Initial GV draw
        initial_gv = self.gv_meter.measure(subject)
        gv_measurements.append({"time": 0, "gv": initial_gv})
        print(f"   Initial drawn GV: {initial_gv:.1f}")

        # Wait between draws. This loop only waits and draws; emission (audio,
        # scalar, hardware) is done elsewhere, by the broadcast services.
        elapsed = 0
        while elapsed < duration_seconds:
            time.sleep(min(check_interval, duration_seconds - elapsed))
            elapsed = time.time() - start_time

            current_gv = self.gv_meter.measure(subject)
            gv_measurements.append({"time": elapsed, "gv": current_gv})
            print(f"   Drawn GV at {elapsed:.0f}s: {current_gv:.1f}")

        # Final GV draw
        final_gv = self.gv_meter.measure(subject)
        gv_measurements.append({"time": duration_seconds, "gv": final_gv})
        print(f"   Final drawn GV: {final_gv:.1f}")

        # Trend between two draws
        gv_change = final_gv - initial_gv
        gv_trend = "improving" if gv_change > 20 else "declining" if gv_change < -20 else "stable"

        print(f"   Drawn GV change: {gv_change:+.1f} ({gv_trend})")

        return {
            "subject": subject,
            "rate": rate.to_dict(),
            "duration": duration_seconds,
            "initial_gv": initial_gv,
            "final_gv": final_gv,
            "gv_change": gv_change,
            "gv_trend": gv_trend,
            "gv_measurements": gv_measurements,
            "emitted": False,
            "note": GV_DRAW_NOTE,
            "provenance": {
                "initial_gv": DRAW,
                "final_gv": DRAW,
                "gv_change": DRAW,
                "gv_trend": DRAW,
                "gv_measurements": DRAW,
            },
            "timestamp": datetime.now().isoformat(),
        }

    def find_balancing_rates(self, subject: str, num_rates: int = 5) -> list[RadionicsRate]:
        """
        Find rates that could help balance/heal the subject.

        The subject's signature is computed and inverted; each dial is then
        offset by a draw, and each rate's potency is drawn. Every returned
        rate carries ``provenance = {"values": "draw", "potency": "draw"}``.

        Args:
            subject: Subject to find balancing rates for
            num_rates: Number of rates to generate

        Returns:
            List of balancing rates
        """
        # Get subject's signature
        signature = self.sig_calculator.text_to_rate(subject, num_dials=3, algorithm="mixed")

        balancing_rates = []

        # Generate complementary rates
        for i in range(num_rates):
            # Create inverse/complementary values
            complementary_values = [(100 - v + self.rng.generate(0, 20, 1)[0]) % 100 for v in signature.values]

            rate = RadionicsRate(
                values=complementary_values,
                name=f"Balance-{i + 1} for {subject}",
                description=f"Complementary balancing rate for {subject} (signature inverse, offset by a draw)",
                category="balancing",
                provenance={"values": DRAW, "potency": DRAW},
            )

            # Draw a potency (stick-pad analog), not an estimate of anything
            rate.potency = self.rng.generate_float(0.4, 0.9, 1)[0]
            balancing_rates.append(rate)

        balancing_rates.sort(key=lambda r: r.potency, reverse=True)
        return balancing_rates


# Convenience function for quick analysis
def quick_analysis(subject: str, verbose: bool = True) -> dict:
    """
    Perform a quick radionics analysis on a subject.

    Args:
        subject: What/who to analyze
        verbose: Print detailed output

    Returns:
        Analysis results
    """
    analyzer = RadionicsAnalyzer()
    result = analyzer.analyze_subject(subject, num_rates=10)

    if verbose:
        print("\n✅ Analysis complete!")
        print(f"   Subject: {subject}")
        print(f"   Drawn GV: {result['baseline_gv']:.1f}")
        print(f"   Reading: {result['interpretation']}")

    return result


if __name__ == "__main__":
    # Demo usage
    print("=" * 70)
    print("RADIONICS ENGINE DEMONSTRATION")
    print("=" * 70)

    # Test signature calculation
    print("\n1. SIGNATURE CALCULATION")
    sig_calc = SignatureCalculator()

    test_subjects = ["John Doe", "World Peace", "Planetary Healing"]
    for subject in test_subjects:
        rate = sig_calc.text_to_rate(subject, num_dials=3, algorithm="mixed")
        print(f"   {subject}: {rate}")

    # GV draws
    print("\n2. GENERAL VITALITY DRAWS")
    gv_meter = GeneralVitalityMeter()

    for subject in test_subjects:
        gv = gv_meter.measure(subject)
        interpretation = gv_meter.interpret_gv(gv)
        print(f"   {subject}: {interpretation}")

    # Test full analysis
    print("\n3. FULL RADIONICS ANALYSIS")
    analyzer = RadionicsAnalyzer()
    result = analyzer.analyze_subject("Healing for Earth", num_rates=5)

    # Test balancing rates
    print("\n4. BALANCING RATE GENERATION")
    balancing = analyzer.find_balancing_rates("Stress Relief", num_rates=3)
    print("   Balancing rates for Stress Relief:")
    for rate in balancing:
        print(f"      {rate}")

    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)
