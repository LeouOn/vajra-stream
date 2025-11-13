"""
Vajra.Stream - LLM Integration Module
Supports both API-based LLMs (OpenAI, Anthropic) and local GGUF models
For generating prayers, dharma teachings, and wisdom content
"""

import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import glob


class LLMIntegration:
    """
    Unified interface for both API and local LLM models
    """

    def __init__(self, model_type: str = 'auto', model_name: Optional[str] = None,
                 api_key: Optional[str] = None, local_models_dir: str = './models'):
        """
        Initialize LLM integration

        Args:
            model_type: 'openai', 'anthropic', 'local', or 'auto' (tries local first, then API)
            model_name: Specific model name or path to GGUF file
            api_key: API key for cloud providers
            local_models_dir: Directory to scan for GGUF models
        """
        self.model_type = model_type
        self.model_name = model_name
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        self.local_models_dir = local_models_dir

        self.client = None
        self.local_model = None

        # Initialize based on type
        if model_type == 'auto':
            self._initialize_auto()
        elif model_type == 'local':
            self._initialize_local()
        elif model_type == 'openai':
            self._initialize_openai()
        elif model_type == 'anthropic':
            self._initialize_anthropic()

    def _initialize_auto(self):
        """Try local first, fall back to API"""
        print("Auto-detecting available LLM...")

        # Try local first
        try:
            self._initialize_local()
            if self.local_model:
                print(f"✓ Using local model: {self.model_name}")
                return
        except Exception as e:
            print(f"  Local model not available: {e}")

        # Fall back to API
        if os.getenv('ANTHROPIC_API_KEY'):
            try:
                self._initialize_anthropic()
                print("✓ Using Anthropic API")
                return
            except:
                pass

        if os.getenv('OPENAI_API_KEY'):
            try:
                self._initialize_openai()
                print("✓ Using OpenAI API")
                return
            except:
                pass

        print("⚠ No LLM available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY, or add GGUF models to ./models/")

    def _initialize_local(self):
        """Initialize local GGUF model"""
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError("llama-cpp-python not installed. Run: pip install llama-cpp-python")

        # Find GGUF models
        if self.model_name and os.path.exists(self.model_name):
            model_path = self.model_name
        else:
            model_path = self._find_gguf_model()

        if not model_path:
            raise FileNotFoundError(f"No GGUF models found in {self.local_models_dir}")

        print(f"Loading local model: {model_path}")

        # Load model with reasonable defaults
        self.local_model = Llama(
            model_path=model_path,
            n_ctx=2048,  # Context window
            n_threads=4,  # CPU threads
            n_gpu_layers=0,  # Set > 0 if you have GPU
            verbose=False
        )

        self.model_type = 'local'
        self.model_name = os.path.basename(model_path)

    def _find_gguf_model(self) -> Optional[str]:
        """Scan directory for GGUF models"""
        os.makedirs(self.local_models_dir, exist_ok=True)

        # Search for .gguf files
        patterns = [
            os.path.join(self.local_models_dir, "*.gguf"),
            os.path.join(self.local_models_dir, "**/*.gguf"),
        ]

        for pattern in patterns:
            models = glob.glob(pattern, recursive=True)
            if models:
                # Prefer models with 'instruct' or 'chat' in name
                for model in models:
                    if 'instruct' in model.lower() or 'chat' in model.lower():
                        return model
                # Otherwise return first found
                return models[0]

        return None

    def _initialize_openai(self):
        """Initialize OpenAI API"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        self.client = OpenAI(api_key=self.api_key or os.getenv('OPENAI_API_KEY'))
        self.model_type = 'openai'
        if not self.model_name:
            self.model_name = 'gpt-4o-mini'  # Default to smaller, cheaper model

    def _initialize_anthropic(self):
        """Initialize Anthropic API"""
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        self.client = Anthropic(api_key=self.api_key or os.getenv('ANTHROPIC_API_KEY'))
        self.model_type = 'anthropic'
        if not self.model_name:
            self.model_name = 'claude-3-5-haiku-20241022'  # Default to Haiku

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Generate text from prompt

        Args:
            prompt: User prompt
            system_prompt: System instructions
            max_tokens: Maximum response length
            temperature: Creativity (0-1)
        """
        if self.model_type == 'local':
            return self._generate_local(prompt, system_prompt, max_tokens, temperature)
        elif self.model_type == 'openai':
            return self._generate_openai(prompt, system_prompt, max_tokens, temperature)
        elif self.model_type == 'anthropic':
            return self._generate_anthropic(prompt, system_prompt, max_tokens, temperature)
        else:
            return "No LLM initialized. Please configure an API key or local model."

    def _generate_local(self, prompt: str, system_prompt: Optional[str],
                       max_tokens: int, temperature: float) -> str:
        """Generate using local GGUF model"""
        # Format prompt with system message if provided
        if system_prompt:
            formatted_prompt = f"### System:\n{system_prompt}\n\n### User:\n{prompt}\n\n### Assistant:\n"
        else:
            formatted_prompt = prompt

        # Generate
        response = self.local_model(
            formatted_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["###", "\n\n\n"],
            echo=False
        )

        return response['choices'][0]['text'].strip()

    def _generate_openai(self, prompt: str, system_prompt: Optional[str],
                        max_tokens: int, temperature: float) -> str:
        """Generate using OpenAI API"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )

        return response.choices[0].message.content

    def _generate_anthropic(self, prompt: str, system_prompt: Optional[str],
                           max_tokens: int, temperature: float) -> str:
        """Generate using Anthropic API"""
        kwargs = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)

        return response.content[0].text

    def list_available_models(self) -> Dict[str, List[str]]:
        """List all available models"""
        available = {
            'local': [],
            'api': []
        }

        # Check for local models
        patterns = [
            os.path.join(self.local_models_dir, "*.gguf"),
            os.path.join(self.local_models_dir, "**/*.gguf"),
        ]

        for pattern in patterns:
            models = glob.glob(pattern, recursive=True)
            available['local'].extend([os.path.basename(m) for m in models])

        # Check for API keys
        if os.getenv('OPENAI_API_KEY'):
            available['api'].append('OpenAI (gpt-4o, gpt-4o-mini, etc.)')

        if os.getenv('ANTHROPIC_API_KEY'):
            available['api'].append('Anthropic (claude-3-5-sonnet, claude-3-5-haiku)')

        return available


class DharmaLLM:
    """
    Specialized LLM interface for dharma content generation
    """

    def __init__(self, llm: LLMIntegration):
        self.llm = llm

        # System prompt for dharma content
        self.dharma_system = """You are a wise dharma teacher versed in Buddhist philosophy,
meditation practices, and contemplative traditions. You speak with clarity, compassion,
and depth. Your teachings are rooted in the Buddhadharma but accessible to all beings.
You draw from Theravada, Mahayana, and Vajrayana traditions as appropriate."""

    def generate_prayer(self, intention: str, tradition: str = 'universal') -> str:
        """
        Generate a prayer/aspiration based on intention

        Args:
            intention: What the prayer is for (e.g., "healing", "peace", "wisdom")
            tradition: 'universal', 'buddhist', 'tibetan', 'zen'
        """
        prompt = f"""Generate a beautiful prayer or aspiration for {intention}.

Style: {tradition}
Length: 3-5 lines
Tone: Heartfelt, sincere, universal in scope

The prayer should:
- Be inclusive of all beings
- Express genuine aspiration
- Be poetic but not flowery
- Suitable for contemplation

Generate only the prayer text, no explanation."""

        return self.llm.generate(prompt, system_prompt=self.dharma_system,
                                max_tokens=200, temperature=0.8)

    def generate_teaching(self, topic: str, length: str = 'short') -> str:
        """
        Generate a dharma teaching on a topic

        Args:
            topic: Teaching topic (e.g., "impermanence", "compassion", "emptiness")
            length: 'short' (paragraph), 'medium' (2-3 paragraphs), 'long' (essay)
        """
        length_map = {
            'short': '1 paragraph',
            'medium': '2-3 paragraphs',
            'long': '4-6 paragraphs'
        }

        prompt = f"""Offer a teaching on {topic}.

Length: {length_map.get(length, '1 paragraph')}

The teaching should:
- Be clear and accessible
- Include practical application
- Be rooted in dharma wisdom
- Inspire practice

Generate the teaching:"""

        max_tokens_map = {'short': 300, 'medium': 600, 'long': 1200}

        return self.llm.generate(prompt, system_prompt=self.dharma_system,
                                max_tokens=max_tokens_map.get(length, 300),
                                temperature=0.7)

    def generate_meditation_instruction(self, practice: str) -> str:
        """
        Generate meditation instructions

        Args:
            practice: Type of meditation (e.g., "loving-kindness", "shamatha", "vipassana")
        """
        prompt = f"""Provide clear meditation instructions for {practice} practice.

Format:
1. Posture and preparation (brief)
2. Main practice instructions (detailed)
3. Closing (brief)

Keep it practical and clear. Suitable for beginners but also valuable for experienced practitioners.

Generate the instructions:"""

        return self.llm.generate(prompt, system_prompt=self.dharma_system,
                                max_tokens=800, temperature=0.6)

    def generate_dedication(self) -> str:
        """Generate a dedication of merit"""
        prompt = """Generate a brief dedication of merit to conclude a practice session.

2-4 lines that dedicate any benefit to all beings.

Generate only the dedication text:"""

        return self.llm.generate(prompt, system_prompt=self.dharma_system,
                                max_tokens=150, temperature=0.8)

    def generate_contemplation(self, theme: str) -> str:
        """
        Generate a contemplation prompt

        Args:
            theme: Theme to contemplate (e.g., "death", "interdependence", "buddha-nature")
        """
        prompt = f"""Create a contemplation exercise on {theme}.

Format:
- Opening reflection question
- 2-3 points to consider
- Closing invitation

Make it profound yet accessible.

Generate the contemplation:"""

        return self.llm.generate(prompt, system_prompt=self.dharma_system,
                                max_tokens=400, temperature=0.7)


if __name__ == "__main__":
    print("Testing LLM Integration")
    print("=" * 60)

    # List available models
    llm = LLMIntegration(model_type='auto')
    available = llm.list_available_models()

    print("\nAvailable Models:")
    print(f"  Local: {available['local'] if available['local'] else 'None found in ./models/'}")
    print(f"  API: {available['api'] if available['api'] else 'No API keys configured'}")

    # Test dharma content generation if LLM is available
    if llm.client or llm.local_model:
        print("\n" + "=" * 60)
        print("Testing Dharma Content Generation")
        print("=" * 60)

        dharma = DharmaLLM(llm)

        print("\n1. Generating prayer for peace...")
        prayer = dharma.generate_prayer("peace and healing for all beings")
        print(f"\n{prayer}\n")

        print("=" * 60)
        print("\n2. Generating short teaching on compassion...")
        teaching = dharma.generate_teaching("compassion", length='short')
        print(f"\n{teaching}\n")

        print("=" * 60)
        print("\n✓ LLM integration test complete")
    else:
        print("\nℹ No LLM available for content generation test")
        print("  To enable:")
        print("  - Add GGUF models to ./models/ directory")
        print("  - OR set ANTHROPIC_API_KEY environment variable")
        print("  - OR set OPENAI_API_KEY environment variable")
