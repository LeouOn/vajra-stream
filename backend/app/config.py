"""
Vajra.Stream Backend Configuration
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Vajra.Stream API"

    # Database
    DATABASE_URL: str = "sqlite:///./vajra_stream.db"

    # Audio Settings
    SAMPLE_RATE: int = 44100
    AUDIO_DEVICE: str = "default"
    MAX_VOLUME: float = 0.8

    # Prayer Bowl Settings
    PRAYER_BOWL_MODE: bool = True
    PRAYER_BOWL_HARMONICS: bool = True
    PRAYER_BOWL_ENVELOPES: bool = True

    # Hardware
    HARDWARE_LEVEL: int = 2
    AMPLIFIER_CONNECTED: bool = False

    # Default Frequencies
    BLESSING_FREQUENCIES: list = [7.83, 136.1, 528, 639, 741]

    # CORS
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # LLM API Keys (optional — used by core/llm_integration.py)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    OPENAI_MODEL: str = ""
    ANTHROPIC_API_KEY: str = ""
    LM_STUDIO_BASE_URL: str = "http://127.0.0.1:1234"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = ""

    # TTS API Keys (optional)
    ELEVENLABS_API_KEY: str = ""
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # Usage Tracking
    LLM_USAGE_TRACKING: str = "true"
    LLM_USAGE_LOG_PATH: str = "./logs/llm_usage.jsonl"

    # ComfyUI
    COMFYUI_BASE_URL: str = "http://127.0.0.1:8188"

    model_config = {
        "env_file": ".env",
        "extra": "ignore",  # Allow extra env vars not defined here
    }


settings = Settings()
