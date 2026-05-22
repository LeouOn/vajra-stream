"""
Vajra.Stream - Personal Healing Module
Comprehensive chakra and meridian energy work
"""

import json
import os
from enum import Enum


class Chakra(Enum):
    """Chakra definitions with associated frequencies and colors"""

    ROOT = "root"
    SACRAL = "sacral"
    SOLAR_PLEXUS = "solar_plexus"
    HEART = "heart"
    THROAT = "throat"
    THIRD_EYE = "third_eye"
    CROWN = "crown"


class HealingIntention(Enum):
    """Common healing intentions"""

    BALANCE = "balance"
    CLEAR = "clear"
    ACTIVATE = "activate"
    HARMONIZE = "harmonize"
    GROUND = "ground"
    EXPAND = "expand"


class PersonalHealingModule:
    """
    Comprehensive personal healing system
    Supports chakra healing, meridian work, and energy clearing
    """

    def __init__(self, audio_generator=None):
        """
        Initialize healing module

        Args:
            audio_generator: AudioGenerator instance for frequency production
        """
        self.audio = audio_generator
        self.knowledge_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge")

        self.chakra_data = self._load_chakra_data()
        self.meridian_data = self._load_meridian_data()

    def _load_chakra_data(self) -> dict:
        """Load chakra knowledge base"""
        return {
            "root": {
                "name": "Root Chakra (Muladhara)",
                "sanskrit": "मूलाधार",
                "element": "Earth",
                "color": "Red",
                "color_rgb": (255, 0, 0),
                "location": "Base of spine",
                "governs": "Survival, grounding, stability, basic needs",
                "frequencies": {"root": 396, "activating": 42, "releasing": 93, "balancing": 72},
                "affirmations": ["I am safe", "I have enough", "I belong", "I am grounded in the eternal"],
                " crystals": ["Red Jasper", "Black Tourmaline", "Smoky Quartz", "Hematite"],
                "essential_oils": ["Cedarwood", "Patchouli", "Vetiver", "Ground Redwood"],
            },
            "sacral": {
                "name": "Sacral Chakra (Svadhisthana)",
                "sanskrit": "स्वाधिष्ठान",
                "element": "Water",
                "color": "Orange",
                "color_rgb": (255, 140, 0),
                "location": "Below navel",
                "governs": "Creativity, sexuality, emotions, relationships",
                "frequencies": {"root": 417, "activating": 90, "emotional": 128, "balancing": 81},
                "affirmations": ["I feel", "I create flow", "My emotions are sacred", "I honor my feelings"],
                "crystals": ["Carnelian", "Orange Calcite", "Moonstone", "Sunstone"],
                "essential_oils": ["Sweet Orange", "Ylang Ylang", "Geranium", "Rose"],
            },
            "solar_plexus": {
                "name": "Solar Plexus Chakra (Manipura)",
                "sanskrit": "मणिपूर",
                "element": "Fire",
                "color": "Yellow",
                "color_rgb": (255, 255, 0),
                "location": "Upper abdomen",
                "governs": "Personal power, will, digestion, metabolism",
                "frequencies": {"root": 528, "empowering": 45, "digestion": 62, "balancing": 69},
                "affirmations": ["I am powerful", "I trust myself", "I act with integrity", "My will serves the good"],
                "crystals": ["Citrine", "Tiger Eye", "Yellow Jasper", "Pyrite"],
                "essential_oils": ["Lemon", "Ginger", "Peppermint", "Chamomile"],
            },
            "heart": {
                "name": "Heart Chakra (Anahata)",
                "sanskrit": "अनाहत",
                "element": "Air",
                "color": "Green",
                "color_rgb": (0, 255, 0),
                "location": "Center of chest",
                "governs": "Love, compassion, forgiveness, immunity",
                "frequencies": {"root": 639, "unconditional_love": 528, "healing": 741, "releasing": 396},
                "affirmations": [
                    "I am love",
                    "I forgive myself and others",
                    "Compassion flows through me",
                    "My heart is open",
                ],
                "crystals": ["Rose Quartz", "Emerald", "Jade", "Malachite"],
                "essential_oils": ["Rose", "Jasmine", "Lavender", "Melissa"],
            },
            "throat": {
                "name": "Throat Chakra (Vishuddha)",
                "sanskrit": "विशुद्ध",
                "element": "Ether",
                "color": "Blue",
                "color_rgb": (0, 191, 255),
                "location": "Throat",
                "governs": "Communication, expression, truth, creativity",
                "frequencies": {"root": 741, "expression": 192, "truth": 528, "balancing": 96},
                "affirmations": ["I speak my truth", "My voice matters", "I express with clarity", "I listen deeply"],
                "crystals": ["Blue Lace Agate", "Aqua Aura", "Celestite", "Turquoise"],
                "essential_oils": ["Peppermint", "Eucalyptus", "Marjoram", "Tea Tree"],
            },
            "third_eye": {
                "name": "Third Eye Chakra (Ajna)",
                "sanskrit": "आज्ञा",
                "element": "Light",
                "color": "Indigo",
                "color_rgb": (75, 0, 130),
                "location": "Between eyebrows",
                "governs": "Intuition, perception, insight, imagination",
                "frequencies": {"root": 852, "intuition": 711, "vision": 531, "third_eye": 444},
                "affirmations": [
                    "I see clearly",
                    "I trust my intuition",
                    "I perceive with wisdom",
                    "My vision is clear",
                ],
                "crystals": ["Amethyst", "Lapis Lazuli", "Sugilite", "Charoite"],
                "essential_oils": ["Frankincense", "Myrrh", "Sandalwood", "Spikenard"],
            },
            "crown": {
                "name": "Crown Chakra (Sahasrara)",
                "sanskrit": "सहस्रार",
                "element": "Cosmic",
                "color": "Violet",
                "color_rgb": (148, 0, 211),
                "location": "Top of head",
                "governs": "Spirituality, connection to divine, enlightenment",
                "frequencies": {"root": 963, "unity": 432, "enlightenment": 768, "divine": 999},
                "affirmations": [
                    "I am connected to source",
                    "Divine wisdom flows through me",
                    "I am spiritual being",
                    "I surrender to the divine",
                ],
                "crystals": ["Clear Quartz", "Selenite", "Danburite", "Spirit Quartz"],
                "essential_oils": ["White Sage", "Lotus", "Violet Leaf", "Absolute"],
            },
        }

    def _load_meridian_data(self) -> dict:
        """Load meridian/acupuncture point data"""
        return {
            "lung": {"element": "Metal", "emotion": "Grief", "frequency": 176, "color": "White"},
            "large_intestine": {"element": "Metal", "emotion": "Rigidity", "frequency": 190, "color": "White"},
            "stomach": {"element": "Earth", "emotion": "Worry", "frequency": 62, "color": "Yellow"},
            "spleen": {"element": "Earth", "emotion": "Anxiety", "frequency": 69, "color": "Yellow"},
            "heart": {"element": "Fire", "emotion": "Joy", "frequency": 528, "color": "Red"},
            "small_intestine": {"element": "Fire", "emotion": "Insecurity", "frequency": 305, "color": "Red"},
            "bladder": {"element": "Water", "emotion": "Fear", "frequency": 52, "color": "Blue"},
            "kidney": {"element": "Water", "emotion": "Terror", "frequency": 41, "color": "Blue"},
            "pericardium": {"element": "Fire", "emotion": "Broken heart", "frequency": 428, "color": "Red"},
            "triple_burner": {"element": "Fire", "emotion": "Confusion", "frequency": 235, "color": "Red"},
            "gallbladder": {"element": "Wood", "emotion": "Bitterness", "frequency": 97, "color": "Green"},
            "liver": {"element": "Wood", "emotion": "Anger", "frequency": 76, "color": "Green"},
        }

    def get_chakra_info(self, chakra_name: str) -> dict | None:
        """Get information about a specific chakra"""
        return self.chakra_data.get(chakra_name.lower())

    def get_all_chakras(self) -> dict:
        """Return all chakra data"""
        return self.chakra_data.copy()

    def get_healing_frequencies(self, chakra_name: str, intention: str = "balance") -> list[tuple[float, float]]:
        """
        Get healing frequencies for a chakra with specific intention

        Args:
            chakra_name: Name of chakra
            intention: 'balance', 'clear', 'activate', 'harmonize', 'ground', 'expand'

        Returns:
            List of (frequency, amplitude) tuples
        """
        chakra = self.chakra_data.get(chakra_name.lower())
        if not chakra:
            return []

        freq_map = {
            "balance": chakra["frequencies"]["balancing"],
            "clear": chakra["frequencies"]["root"],
            "activate": chakra["frequencies"]["root"] * 2,
            "harmonize": chakra["frequencies"]["root"] * 1.5,
            "ground": 396,
            "expand": 528,
        }

        freq = freq_map.get(intention, chakra["frequencies"]["root"])
        return [(freq, 1.0), (7.83, 0.3)]

    def create_chakra_healing_sequence(self, sequence_type: str = "full", duration_per: int = 60) -> dict:
        """
        Create a complete chakra healing session

        Args:
            sequence_type: 'full' (all), 'ascending', 'descending', 'heart_centered'
            duration_per: Seconds per chakra

        Returns:
            Dictionary with sequence information
        """
        if sequence_type == "full":
            order = ["root", "sacral", "solar_plexus", "heart", "throat", "third_eye", "crown"]
        elif sequence_type == "ascending":
            order = ["root", "sacral", "solar_plexus", "heart", "throat", "third_eye", "crown"]
        elif sequence_type == "descending":
            order = ["crown", "third_eye", "throat", "heart", "solar_plexus", "sacral", "root"]
        elif sequence_type == "heart_centered":
            order = [
                "heart",
                "third_eye",
                "throat",
                "solar_plexus",
                "sacral",
                "root",
                "crown",
                "third_eye",
                "throat",
                "solar_plexus",
                "sacral",
            ]
        else:
            order = ["root", "sacral", "solar_plexus", "heart", "throat", "third_eye", "crown"]

        sequence = {
            "type": sequence_type,
            "duration_per": duration_per,
            "total_duration": len(order) * duration_per,
            "chakras": [],
        }

        for chakra_name in order:
            chakra = self.chakra_data.get(chakra_name)
            if chakra:
                sequence["chakras"].append(
                    {
                        "name": chakra["name"],
                        "sanskrit": chakra["sanskrit"],
                        "frequencies": chakra["frequencies"],
                        "element": chakra["element"],
                        "color": chakra["color"],
                        "affirmations": chakra["affirmations"],
                    }
                )

        return sequence

    def get_affirmations(self, chakra_name: str) -> list[str]:
        """Get affirmations for a chakra"""
        chakra = self.chakra_data.get(chakra_name.lower())
        if chakra:
            return chakra["affirmations"]
        return []

    def get_crystals_for_chakra(self, chakra_name: str) -> list[str]:
        """Get recommended crystals for a chakra"""
        chakra = self.chakra_data.get(chakra_name.lower())
        if chakra:
            return chakra["crystals"]
        return []

    def get_elemental_healing_frequencies(self, element: str) -> list[float]:
        """Get frequencies for an element"""
        elements = {
            "earth": [432, 256, 320],
            "water": [417, 432, 528],
            "fire": [540, 594, 672],
            "air": [384, 480, 576],
            "ether": [768, 864, 960],
        }
        return elements.get(element.lower(), [432])

    def generate_healing_session_audio(self, chakra_name: str, intention: str = "balance", duration: int = 300) -> any:
        """
        Generate audio for chakra healing session

        Args:
            chakra_name: Name of chakra to heal
            intention: Healing intention
            duration: Duration in seconds

        Returns:
            Audio waveform (numpy array)
        """
        if not self.audio:
            return None

        freqs = self.get_healing_frequencies(chakra_name, intention)
        if freqs:
            return self.audio.layer_frequencies(freqs, duration=duration)
        return None

    def get_meridian_info(self, meridian_name: str) -> dict | None:
        """Get information about a meridian"""
        return self.meridian_data.get(meridian_name.lower())

    def get_all_meridians(self) -> dict:
        """Return all meridian data"""
        return self.meridian_data.copy()

    def get_emotional_frequencies(self, emotion: str) -> list[float]:
        """Get frequencies for processing specific emotions"""
        emotional_freqs = {
            "fear": [396, 52, 41],
            "grief": [639, 176, 417],
            "anger": [76, 417, 528],
            "worry": [62, 69, 741],
            "anxiety": [69, 528, 741],
            "depression": [528, 639, 396],
            "stress": [528, 417, 741],
            "joy": [528, 639, 963],
            "peace": [528, 639, 432],
            "love": [528, 639, 741],
        }
        return emotional_freqs.get(emotion.lower(), [528])

    def save_healing_session_log(self, session_data: dict, filepath: str = "./logs/healing_sessions.jsonl"):
        """Save healing session to log"""
        from datetime import datetime

        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else "./logs", exist_ok=True)

        log_entry = {"timestamp": datetime.now().isoformat(), **session_data}

        with open(filepath, "a") as f:
            f.write(json.dumps(log_entry) + "\n")


if __name__ == "__main__":
    print("Vajra.Stream Personal Healing Module")
    print("=" * 60)

    healing = PersonalHealingModule()

    print("\n--- Chakra Healing Sessions ---")
    for session_type in ["full", "ascending", "descending", "heart_centered"]:
        seq = healing.create_chakra_healing_sequence(session_type)
        print(f"\n{session_type.title()} Healing:")
        print(f"  Total duration: {seq['total_duration']} seconds")
        print(f"  Chakras: {len(seq['chakras'])}")

    print("\n--- Chakra Information ---")
    for chakra in ["root", "heart", "crown"]:
        info = healing.get_chakra_info(chakra)
        print(f"\n{info['name']}:")
        print(f"  Element: {info['element']}")
        print(f"  Color: {info['color']}")
        print(f"  Frequencies: {info['frequencies']}")

    print("\n--- Emotional Healing ---")
    for emotion in ["fear", "grief", "anger", "peace", "love"]:
        freqs = healing.get_emotional_frequencies(emotion)
        print(f"  {emotion.title()}: {freqs} Hz")

    print("\n" + "=" * 60)
    print("Personal Healing Module ready")
