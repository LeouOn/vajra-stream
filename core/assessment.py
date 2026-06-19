"""
Assessment Tools — chakra, dosha, and symptom evaluation questionnaires.

Provides self-assessment instruments for:
- **Chakra assessment** — 7-question-per-chakra questionnaire returning
  balance scores (0–10) for each chakra.
- **Dosha self-assessment** — simplified Vata/Pitta/Kapha quiz based on
  Ayurvedic constitutional typing.
- **Symptom tracker** — maps free-text symptom descriptions to conditions
  recognised by :class:`~core.protocol_selector.ProtocolSelector`.
- **Meridian clock check** — returns the currently active meridian based
  on the Chinese Medicine Clock.

Dependencies:
    :mod:`core.healing_systems` — MeridianSystem for clock lookups.
    :mod:`core.protocol_selector` — ProtocolSelector for symptom matching.

Exports:
    ChakraAssessment, DoshaAssessment, SymptomTracker — assessment classes.
    MeridianClockCheck — utility function for current meridian lookup.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChakraResult:
    """Result of a chakra assessment.

    Attributes:
        chakra_name: Sanskrit name (e.g. ``"muladhara"``).
        english_name: English name (e.g. ``"Root Chakra"``).
        score: Balance score 0–10 (0 = severely imbalanced, 10 = fully balanced).
        interpretation: Text interpretation of the score.
    """

    chakra_name: str
    english_name: str
    score: float
    interpretation: str


class ChakraAssessment:
    """Self-assessment questionnaire for the 7-chakra system.

    Each chakra has 7 Likert-scale questions (1–5). Scores are summed,
    normalised to 0–10, and interpreted as balanced / mildly imbalanced /
    moderately imbalanced / severely imbalanced.

    Usage:
        >>> assess = ChakraAssessment()
        >>> # Answer each question 1-5:
        >>> results = assess.evaluate({"muladhara": [4,3,5,3,4,5,4], ...})
        >>> for r in results:
        ...     print(f"{r.english_name}: {r.score}/10 — {r.interpretation}")
    """

    # English names for display
    ENGLISH_NAMES = {
        "muladhara": "Root Chakra",
        "svadhisthana": "Sacral Chakra",
        "manipura": "Solar Plexus Chakra",
        "anahata": "Heart Chakra",
        "vishuddha": "Throat Chakra",
        "ajna": "Third Eye Chakra",
        "sahasrara": "Crown Chakra",
    }

    # 7 questions per chakra, scored 1 (never) to 5 (always)
    QUESTIONS = {
        "muladhara": [
            "I feel physically safe and secure in my environment.",
            "I feel grounded and connected to my body.",
            "I have a stable home and financial situation.",
            "I trust that my basic needs will be met.",
            "I feel a sense of belonging in my community.",
            "I am comfortable in my physical body.",
            "I feel a connection to the Earth and nature.",
        ],
        "svadhisthana": [
            "I feel comfortable expressing my creativity.",
            "I have a healthy relationship with pleasure and enjoyment.",
            "I am comfortable with my sexuality.",
            "I can go with the flow and adapt to change.",
            "I feel emotionally balanced and stable.",
            "I nurture myself and allow time for play.",
            "I have healthy, fulfilling relationships.",
        ],
        "manipura": [
            "I feel confident in my abilities and decisions.",
            "I have a strong sense of personal power.",
            "I can set and maintain healthy boundaries.",
            "I feel motivated and purposeful in my life.",
            "I take action towards my goals consistently.",
            "I feel in control of my life direction.",
            "I can assert myself without aggression.",
        ],
        "anahata": [
            "I feel love and compassion for myself.",
            "I can give and receive love freely.",
            "I forgive myself and others easily.",
            "I feel connected to others and the world.",
            "I experience gratitude regularly.",
            "I feel a sense of inner peace and contentment.",
            "I can empathise with others without losing myself.",
        ],
        "vishuddha": [
            "I express my thoughts and feelings clearly.",
            "I speak my truth even when it is difficult.",
            "I listen to others with presence and attention.",
            "I feel heard and understood by others.",
            "I am comfortable with silence and reflection.",
            "I express myself creatively through words, art, or music.",
            "I communicate with honesty and integrity.",
        ],
        "ajna": [
            "I trust my intuition and inner guidance.",
            "I have a clear vision for my life.",
            "I can see situations from multiple perspectives.",
            "I have vivid dreams or intuitive insights.",
            "I can focus and concentrate when needed.",
            "I feel a connection to something greater than myself.",
            "I can discern truth from illusion.",
        ],
        "sahasrara": [
            "I feel a sense of unity with all of life.",
            "I experience moments of deep peace and stillness.",
            "I have a meaningful spiritual practice or connection.",
            "I feel guided by a higher wisdom or purpose.",
            "I can surrender control and trust the process of life.",
            "I experience awe and wonder regularly.",
            "I feel that my life has meaning and purpose.",
        ],
    }

    def evaluate(self, answers: dict[str, list[int]]) -> list[ChakraResult]:
        """Evaluate chakra assessment answers.

        Args:
            answers: Dict mapping chakra Sanskrit name to a list of 7 integer
                scores (1–5 each).

        Returns:
            List of :class:`ChakraResult` for each chakra that was answered.

        Raises:
            ValueError: If any answer list has the wrong length.
        """
        results = []

        for chakra_name, scores in answers.items():
            if len(scores) != 7:
                raise ValueError(f"Expected 7 answers for {chakra_name}, got {len(scores)}")

            total = sum(scores)
            # Normalise: max possible = 35, min = 7
            normalised = ((total - 7) / (35 - 7)) * 10

            interpretation = self._interpret(normalised)

            results.append(
                ChakraResult(
                    chakra_name=chakra_name,
                    english_name=self.ENGLISH_NAMES.get(chakra_name, chakra_name),
                    score=round(normalised, 1),
                    interpretation=interpretation,
                )
            )

        return results

    @staticmethod
    def _interpret(score: float) -> str:
        """Interpret a normalised chakra score."""
        if score >= 8.0:
            return "Well-balanced and flowing freely."
        elif score >= 6.0:
            return "Mildly imbalanced — gentle attention recommended."
        elif score >= 4.0:
            return "Moderately imbalanced — dedicated healing work suggested."
        elif score >= 2.0:
            return "Significantly imbalanced — focused healing protocol recommended."
        else:
            return "Severely imbalanced — priority for healing intervention."

    def get_questions(self, chakra_name: str) -> list[str]:
        """Return the 7 questions for a given chakra.

        Args:
            chakra_name: Sanskrit chakra name (e.g. ``"anahata"``).

        Returns:
            List of 7 question strings, or empty list if chakra not recognised.
        """
        return self.QUESTIONS.get(chakra_name, [])

    def list_chakras(self) -> list[str]:
        """Return all supported chakra names.

        Returns:
            Sorted list of Sanskrit chakra names.
        """
        return sorted(self.QUESTIONS.keys())


class DoshaAssessment:
    """Simplified Ayurvedic dosha self-assessment.

    Asks 10 questions per dosha (Vata, Pitta, Kapha) with 1–5 Likert
    responses. Returns the dominant dosha and percentage breakdown.

    Usage:
        >>> assess = DoshaAssessment()
        >>> results = assess.evaluate({"vata": [4,5,3,...], "pitta": [...], "kapha": [...]})
        >>> print(f"Dominant: {results['dominant']} ({results['vata_pct']:.0f}% Vata, ...)")
    """

    QUESTIONS = {
        "vata": [
            "My body frame is thin and I find it hard to gain weight.",
            "My skin tends to be dry, rough, or cool to the touch.",
            "My mind is active, creative, and sometimes restless.",
            "I often feel cold, especially in my hands and feet.",
            "I learn quickly but also forget quickly.",
            "My sleep is light and easily interrupted.",
            "I tend to worry or feel anxious under stress.",
            "My digestion is irregular and sometimes gassy.",
            "I am enthusiastic and excited by new ideas and experiences.",
            "I prefer warm, moist, grounding foods.",
        ],
        "pitta": [
            "I have a medium build with moderate muscle tone.",
            "My skin is warm, oily, or prone to redness and irritation.",
            "I have a sharp, focused mind and strong opinions.",
            "I often feel warm or hot, even when others are comfortable.",
            "I am competitive, determined, and goal-oriented.",
            "My sleep is moderate and generally sound.",
            "I tend to feel irritable, frustrated, or angry under stress.",
            "My digestion is strong and I rarely skip meals.",
            "I am a natural leader and enjoy taking charge.",
            "I prefer cooling, mildly spiced, fresh foods.",
        ],
        "kapha": [
            "I have a sturdy, heavier build and gain weight easily.",
            "My skin is smooth, thick, and tends to be oily.",
            "My mind is calm, steady, and sometimes slow to change.",
            "I am warm-natured and comfortable in most temperatures.",
            "I learn slowly but retain information very well.",
            "My sleep is deep and I need a full night's rest.",
            "I tend to withdraw, procrastinate, or feel lethargic under stress.",
            "My digestion is slow and steady.",
            "I am loyal, nurturing, and emotionally stable.",
            "I prefer light, warming, stimulating foods.",
        ],
    }

    def evaluate(self, answers: dict[str, list[int]]) -> dict:
        """Evaluate dosha assessment answers.

        Args:
            answers: Dict mapping dosha name (``"vata"``, ``"pitta"``, ``"kapha"``)
                to a list of 10 integer scores (1–5 each).

        Returns:
            Dict with ``dominant``, ``vata_pct``, ``pitta_pct``, ``kapha_pct``,
            and ``breakdown`` keys.

        Raises:
            ValueError: If any answer list has the wrong length.
        """
        totals = {}

        for dosha, scores in answers.items():
            if len(scores) != 10:
                raise ValueError(f"Expected 10 answers for {dosha}, got {len(scores)}")
            totals[dosha] = sum(scores)

        grand_total = sum(totals.values())
        if grand_total == 0:
            return {
                "dominant": "unknown",
                "vata_pct": 0.0,
                "pitta_pct": 0.0,
                "kapha_pct": 0.0,
                "breakdown": totals,
            }

        pct = {d: (t / grand_total) * 100 for d, t in totals.items()}
        dominant = max(totals, key=totals.get)

        return {
            "dominant": dominant,
            "vata_pct": round(pct.get("vata", 0), 1),
            "pitta_pct": round(pct.get("pitta", 0), 1),
            "kapha_pct": round(pct.get("kapha", 0), 1),
            "breakdown": totals,
        }

    def get_questions(self, dosha: str) -> list[str]:
        """Return the 10 questions for a given dosha.

        Args:
            dosha: One of ``"vata"``, ``"pitta"``, ``"kapha"``.

        Returns:
            List of 10 question strings, or empty list if dosha not recognised.
        """
        return self.QUESTIONS.get(dosha, [])


class SymptomTracker:
    """Map free-text symptoms / keywords to known conditions.

    Maintains a keyword→condition index built from the conditions recognised
    by :class:`~core.protocol_selector.ProtocolSelector` plus additional
    common symptom descriptions.

    Usage:
        >>> tracker = SymptomTracker()
        >>> conditions = tracker.match(["anxious", "can't sleep", "head pain"])
        >>> print(conditions)  # ["anxiety", "headache"]
    """

    # Keyword → condition mapping
    KEYWORD_MAP = {
        # Anxiety cluster
        "anxious": "anxiety",
        "anxiety": "anxiety",
        "panic": "anxiety",
        "nervous": "anxiety",
        "restless": "anxiety",
        "worry": "anxiety",
        "can't sleep": "anxiety",
        "insomnia": "anxiety",
        "racing thoughts": "anxiety",
        "overthinking": "anxiety",
        # Depression cluster
        "depressed": "depression",
        "depression": "depression",
        "sad": "depression",
        "hopeless": "depression",
        "empty": "depression",
        "no energy": "depression",
        "fatigue": "depression",
        "unmotivated": "depression",
        # Anger cluster
        "angry": "anger",
        "anger": "anger",
        "rage": "anger",
        "irritable": "anger",
        "frustrated": "anger",
        "resentment": "anger",
        # Grief cluster
        "grief": "grief",
        "loss": "grief",
        "bereavement": "grief",
        "mourning": "grief",
        "heartbroken": "grief",
        # Fear cluster
        "fear": "fear",
        "scared": "fear",
        "afraid": "fear",
        "terrified": "fear",
        "insecure": "fear",
        "unsafe": "fear",
        # Physical
        "back pain": "lower_back_pain",
        "lower back": "lower_back_pain",
        "sciatica": "lower_back_pain",
        "digestion": "digestive_issues",
        "stomach": "digestive_issues",
        "bloating": "digestive_issues",
        "indigestion": "digestive_issues",
        "heart": "heart_disease",
        "chest pain": "heart_disease",
        "palpitations": "heart_disease",
        "thyroid": "thyroid",
        "headache": "headache",
        "migraine": "headache",
        "head pain": "headache",
    }

    def match(self, symptoms: list[str]) -> list[str]:
        """Match a list of symptom descriptions to condition names.

        Performs case-insensitive substring matching against the keyword index.

        Args:
            symptoms: List of free-text symptom descriptions.

        Returns:
            Deduplicated list of matching condition names.
        """
        matched = set()

        for symptom in symptoms:
            symptom_lower = symptom.lower().strip()
            # Exact match
            if symptom_lower in self.KEYWORD_MAP:
                matched.add(self.KEYWORD_MAP[symptom_lower])
                continue
            # Substring match
            for keyword, condition in self.KEYWORD_MAP.items():
                if keyword in symptom_lower:
                    matched.add(condition)

        return sorted(matched)

    def get_keywords(self) -> list[str]:
        """Return all known symptom keywords.

        Returns:
            Sorted list of keyword strings.
        """
        return sorted(self.KEYWORD_MAP.keys())


def get_current_meridian(dt: datetime | None = None) -> str:
    """Return the name of the meridian active at a given time (Chinese Medicine Clock).

    Args:
        dt: Datetime to check (defaults to now). Must have a ``.hour`` attribute.

    Returns:
        Meridian key string (e.g. ``"lung"``, ``"heart"``), or ``"unknown"``
        if the healing systems module is unavailable.
    """
    if dt is None:
        dt = datetime.now()

    try:
        from core.healing_systems import MeridianSystem

        ms = MeridianSystem()
        return ms.get_meridian_for_time(dt.hour)
    except ImportError:
        return "unknown"


if __name__ == "__main__":
    print("Testing Assessment Tools")
    print("=" * 60)

    # --- Chakra Assessment ---
    ca = ChakraAssessment()
    print("\nChakra questions for anahata:")
    for i, q in enumerate(ca.get_questions("anahata"), 1):
        print(f"  {i}. {q}")

    # Simulate answers
    sample_answers = {
        "muladhara": [3, 4, 3, 2, 3, 4, 3],
        "anahata": [5, 4, 3, 5, 4, 4, 5],
        "vishuddha": [2, 2, 3, 2, 1, 3, 2],
    }
    results = ca.evaluate(sample_answers)
    print("\nChakra results:")
    for r in results:
        print(f"  {r.english_name}: {r.score}/10 — {r.interpretation}")

    # --- Dosha Assessment ---
    da = DoshaAssessment()
    dosha_answers = {
        "vata": [4, 4, 5, 4, 4, 3, 3, 4, 5, 4],
        "pitta": [3, 3, 3, 2, 3, 3, 2, 3, 2, 3],
        "kapha": [2, 2, 2, 3, 2, 3, 2, 3, 2, 2],
    }
    dosha_result = da.evaluate(dosha_answers)
    print(f"\nDosha: Dominant = {dosha_result['dominant']}")
    print(f"  Vata: {dosha_result['vata_pct']}%")
    print(f"  Pitta: {dosha_result['pitta_pct']}%")
    print(f"  Kapha: {dosha_result['kapha_pct']}%")

    # --- Symptom Tracker ---
    st = SymptomTracker()
    symptoms = ["anxious", "can't sleep", "head pain", "bloating and stomach issues"]
    matched = st.match(symptoms)
    print(f"\nSymptoms: {symptoms}")
    print(f"Matched conditions: {matched}")

    # --- Meridian Clock ---
    current = get_current_meridian()
    print(f"\nCurrent active meridian: {current}")
