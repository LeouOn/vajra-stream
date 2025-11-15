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
    
    class Config:
        env_file = ".env"

settings = Settings()