"""
Blessings Module
Adapter for blessing generation
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.interfaces import BlessingGenerator, BlessingGenerated, EventBus


class BlessingService(BlessingGenerator):
    """Blessing generation service"""

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus

    def generate_blessing(
        self,
        target_name: str,
        intention: str = "peace and happiness",
        tradition: str = "universal",
        include_mantra: bool = True,
        include_dedication: bool = True
    ) -> Dict[str, Any]:
        """Generate a blessing"""

        templates = {
            'universal': f"""
May {target_name} be filled with loving-kindness.
May {target_name} be well.
May {target_name} be peaceful and at ease.
May {target_name} be happy.

May {intention} be fulfilled for the highest good.

May all beings everywhere share in these blessings.
            """,
            'buddhist': f"""
May {target_name} be free from suffering and the causes of suffering.
May {target_name} find happiness and the causes of happiness.
May {target_name} never be separated from supreme bliss.
May {target_name} abide in equanimity.

With the intention of {intention}, may all beings benefit.

Om Mani Padme Hum
            """
        }

        blessing_text = templates.get(tradition, templates['universal']).strip()

        mantra = None
        if include_mantra:
            mantra = {
                'universal': 'Om Shanti',
                'buddhist': 'Om Mani Padme Hum',
                'tibetan': 'Om Ah Hum Vajra Guru Padma Siddhi Hum'
            }.get(tradition, 'Om')

        dedication = None
        if include_dedication:
            dedication = "By this merit, may all beings find peace, happiness, and liberation."

        result = {
            'blessing_text': blessing_text,
            'target_name': target_name,
            'intention': intention,
            'tradition': tradition,
            'mantra': mantra,
            'dedication': dedication
        }

        # Publish event
        if self.event_bus:
            event = BlessingGenerated(
                timestamp=datetime.now(),
                event_id=str(uuid.uuid4()),
                target_name=target_name,
                blessing_text=blessing_text,
                tradition=tradition
            )
            self.event_bus.publish(event)

        return result

    def generate_mass_liberation(
        self,
        event_name: str,
        location: str,
        souls_count: int = 1000,
        duration_minutes: int = 108
    ) -> Dict[str, Any]:
        """Generate mass liberation blessing"""

        blessing_text = f"""
For all those affected by {event_name} in {location},

May the {souls_count} souls find immediate peace and liberation.
May all suffering cease in this very moment.
May the light of wisdom guide each being to the highest rebirth.

May those who remain find solace, healing, and strength.
May compassion arise in all hearts.

Namo Amitabha Buddha
Om Mani Padme Hum

May all beings benefit.
        """

        return {
            'event_name': event_name,
            'location': location,
            'souls_count': souls_count,
            'blessing_text': blessing_text.strip(),
            'primary_mantra': 'Namo Amitabha Buddha',
            'duration_minutes': duration_minutes,
            'recitation_count': duration_minutes * 10  # ~10 mantras per minute
        }

    def get_available_traditions(self) -> List[Dict[str, Any]]:
        """Get available blessing traditions"""
        return [
            {
                'id': 'universal',
                'name': 'Universal / Interfaith',
                'mantra': 'Om Shanti'
            },
            {
                'id': 'buddhist',
                'name': 'Buddhist',
                'mantra': 'Om Mani Padme Hum'
            },
            {
                'id': 'tibetan',
                'name': 'Tibetan Buddhist',
                'mantra': 'Om Ah Hum Vajra Guru Padma Siddhi Hum'
            },
            {
                'id': 'zen',
                'name': 'Zen Buddhist',
                'mantra': 'Namu Amida Butsu'
            }
        ]
