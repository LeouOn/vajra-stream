"""
LLM Integration Module
Wraps LLM integration for AI-powered content generation
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.interfaces import EventBus


class LLMService:
    """LLM integration service for AI-powered content"""

    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus
        self._llm = None

    @property
    def llm(self):
        """Get LLM integration"""
        if self._llm is None:
            try:
                from core.llm_integration import LLMIntegration
                self._llm = LLMIntegration()
            except ImportError:
                self._llm = None
        return self._llm

    def generate_prayer(
        self,
        intention: str,
        tradition: str = "universal",
        length: str = "medium"
    ) -> Dict[str, Any]:
        """Generate a prayer using LLM"""
        if self.llm is None:
            return {'error': 'LLM not available'}

        try:
            prayer = self.llm.generate_prayer(
                intention=intention,
                tradition=tradition,
                length=length
            )
            return {
                'status': 'success',
                'prayer': prayer,
                'intention': intention,
                'tradition': tradition
            }
        except Exception as e:
            return {'error': str(e)}

    def generate_teaching(
        self,
        topic: str,
        tradition: str = "buddhist",
        depth: str = "moderate"
    ) -> Dict[str, Any]:
        """Generate a dharma teaching"""
        if self.llm is None:
            return {'error': 'LLM not available'}

        try:
            teaching = self.llm.generate_teaching(
                topic=topic,
                tradition=tradition,
                depth=depth
            )
            return {
                'status': 'success',
                'teaching': teaching,
                'topic': topic,
                'tradition': tradition
            }
        except Exception as e:
            return {'error': str(e)}

    def generate_meditation_script(
        self,
        meditation_type: str,
        duration_minutes: int = 20,
        experience_level: str = "beginner"
    ) -> Dict[str, Any]:
        """Generate a guided meditation script"""
        if self.llm is None:
            return {'error': 'LLM not available'}

        try:
            script = self.llm.generate_meditation(
                meditation_type=meditation_type,
                duration=duration_minutes,
                experience=experience_level
            )
            return {
                'status': 'success',
                'script': script,
                'type': meditation_type,
                'duration_minutes': duration_minutes
            }
        except Exception as e:
            return {'error': str(e)}

    def analyze_intention(
        self,
        text: str
    ) -> Dict[str, Any]:
        """Analyze the intention in a text"""
        if self.llm is None:
            return {'error': 'LLM not available'}

        try:
            analysis = self.llm.analyze_intention(text)
            return {
                'status': 'success',
                'analysis': analysis,
                'text_length': len(text)
            }
        except Exception as e:
            return {'error': str(e)}

    def generate_affirmations(
        self,
        intention: str,
        count: int = 7
    ) -> Dict[str, Any]:
        """Generate positive affirmations"""
        if self.llm is None:
            return {'error': 'LLM not available'}

        try:
            affirmations = self.llm.generate_affirmations(
                intention=intention,
                count=count
            )
            return {
                'status': 'success',
                'affirmations': affirmations,
                'intention': intention,
                'count': len(affirmations)
            }
        except Exception as e:
            return {'error': str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Get LLM service status"""
        return {
            'llm_available': self.llm is not None,
            'capabilities': [
                'prayer_generation',
                'teaching_generation',
                'meditation_scripts',
                'intention_analysis',
                'affirmations'
            ] if self.llm else []
        }
