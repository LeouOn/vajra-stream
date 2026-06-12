"""
Practice catalog for the ritual engine.

A `Practice` is a single ritual/sadhana the autonomous engine can select
and execute. Fields are read via `getattr(practice, '<field>', default)`
throughout `core.ritual_engine` so the dataclass is intentionally
permissive — only the fields the selector/executor actually inspect
are declared as typed attributes; the rest are tolerated if present.

The fields the runtime reads:
  - id                              (str)        — unique identifier
  - name                            (str)        — display name
  - genre                           (str)        — used for timing lookup
  - merit_multiplier                (int|float)  — scoring & history weight
  - preferred_planetary_hours       (list[str])  — bonus if current hour matches
  - base_prompt_template            (str)        — injected into LLM narrative
  - duration_sec                    (int)        — how long the practice takes
  - mantra                          (str)        — used by TTS
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Practice:
    id: str
    name: str
    genre: str
    merit_multiplier: int = 10
    preferred_planetary_hours: list[str] = field(default_factory=list)
    base_prompt_template: str = ""
    duration_sec: int = 120
    mantra: str = ""

    @classmethod
    def get_default_practices(cls) -> list[Practice]:
        """Return the canonical Vajra.Stream practice catalog.

        Genres align with `core.auspicious_timing.GENRE_PLANETARY_HOURS`.
        Merit multipliers are tuned so the cap test (108x) has room to grow.
        """
        return [
            cls(
                id="metta",
                name="Loving-Kindness Meditation",
                genre="compassion",
                merit_multiplier=12,
                preferred_planetary_hours=["Venus", "Moon", "Jupiter"],
                base_prompt_template=(
                    "Compose a brief loving-kindness dedication for all beings, radiating warmth and equanimity."
                ),
                duration_sec=180,
                mantra="May all beings be happy and free from suffering.",
            ),
            cls(
                id="tonglen",
                name="Tonglen (Sending and Taking)",
                genre="compassion",
                merit_multiplier=25,
                preferred_planetary_hours=["Moon", "Venus", "Jupiter"],
                base_prompt_template=(
                    "Generate a tonglen visualization: breathe in the suffering "
                    "of all beings, breathe out peace, light, and liberation."
                ),
                duration_sec=240,
                mantra="Om gate gate paragate parasamgate bodhi svaha",
            ),
            cls(
                id="shantideva_recitation",
                name="Shantideva Recitation",
                genre="wisdom",
                merit_multiplier=30,
                preferred_planetary_hours=["Mercury", "Jupiter", "Moon"],
                base_prompt_template=(
                    "Compose a verse from the Bodhicharyavatara on the nature of "
                    "emptiness and the path of the bodhisattva."
                ),
                duration_sec=300,
                mantra="OM MANI PADME HUM",
            ),
            cls(
                id="green_tara",
                name="Green Tara Practice",
                genre="protection",
                merit_multiplier=21,
                preferred_planetary_hours=["Mars", "Saturn", "Sun"],
                base_prompt_template=(
                    "Invoke Green Tara, swift protectoress, who liberates from "
                    "the eight fears with the speed of a mother for her child."
                ),
                duration_sec=180,
                mantra="OM TARE TUTTARE TURE SOHA",
            ),
            cls(
                id="vajrasattva",
                name="Vajrasattva Purification",
                genre="purification",
                merit_multiplier=35,
                preferred_planetary_hours=["Saturn", "Mars", "Moon"],
                base_prompt_template=(
                    "Compose a Vajrasattva 100-syllable mantra context: "
                    "purifying the three poisons of body, speech, and mind."
                ),
                duration_sec=200,
                mantra="OM BENZAR SATO SAMAY MANU PALAYA / BENZAR SATO TENOPA TISHTHA / DRIDHO ME BHAWA / SUTO KAYO ME BHAWA / SUPO KAYO ME BHAWA / ANURAKTO ME BHAWA / SARWA SIDDHI ME PRAYATSA / SARWA KARMA SUTSA ME / TSITTAM SHRIYAM KURU HUM / HA HA HA HA HO / BHAGAWAN SARWA TATHAGATA BENZAR MA ME MUNTSA / BENZAR BHAWA / MAHA SAMAYA SATO / AH HUM PHAT",
            ),
            cls(
                id="manjushri",
                name="Manjushri Wisdom Recitation",
                genre="wisdom",
                merit_multiplier=18,
                preferred_planetary_hours=["Mercury", "Jupiter", "Sun"],
                base_prompt_template=(
                    "Invoke Manjushri, bodhisattva of transcendent wisdom, "
                    "to cut through delusion and illuminate the true nature of mind."
                ),
                duration_sec=150,
                mantra="OM AH RA PA TSA NA DHI",
            ),
            cls(
                id="avalokiteshvara",
                name="Avalokiteshvara Compassion Practice",
                genre="compassion",
                merit_multiplier=20,
                preferred_planetary_hours=["Moon", "Venus", "Jupiter"],
                base_prompt_template=(
                    "Compose an Avalokiteshvara sadhana: the thousand-armed, "
                    "thousand-eyed lord of compassion, hearing the cries of all beings."
                ),
                duration_sec=200,
                mantra="OM MANI PADME HUM",
            ),
            cls(
                id="prosperity_dana",
                name="Dana (Generosity) Practice",
                genre="prosperity",
                merit_multiplier=15,
                preferred_planetary_hours=["Venus", "Jupiter", "Mercury"],
                base_prompt_template=(
                    "Compose a dedication of merit through the practice of "
                    "dana — giving without attachment, for the benefit of all beings."
                ),
                duration_sec=120,
                mantra="Om vajrahum ah",
            ),
        ]
