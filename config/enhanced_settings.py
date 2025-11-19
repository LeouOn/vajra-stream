"""
Enhanced Configuration Management
Supports environment-specific configs, validation, and runtime updates
"""

import os
import json
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class EnhancedConfig:
    def __init__(self, env: str = 'development'):
        self.env = env
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from multiple sources"""
        # Default config
        config = {
            'audio': {
                'sample_rate': 44100,
                'max_volume': 0.8,
                'prayer_bowl_mode': True,
                'prayer_bowl_harmonics': True,
                'prayer_bowl_envelopes': True,
                'prayer_bowl_modulation': True
            },
            'hardware': {
                'level': 2,
                'amplifier_connected': False,
                'bass_shaker_connected': False,
                'crystal_count': 6,
                'grid_pattern': 'hexagon'
            },
            'events': {
                'persistence_enabled': True,
                'max_history': 10000,
                'persistence_path': 'logs/events.jsonl'
            },
            'session': {
                'default_duration': 300,
                'default_intention': "May all beings be happy and free from suffering"
            },
            'paths': {
                'knowledge': './knowledge/',
                'generated': './generated/',
                'logs': './logs/'
            }
        }
        
        # Environment-specific overrides
        env_file = f'config/{self.env}.yaml'
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    env_config = yaml.safe_load(f)
                    if env_config:
                        self._deep_update(config, env_config)
            except Exception as e:
                logger.warning(f"Failed to load environment config {env_file}: {e}")
        
        # Runtime overrides from environment variable
        if os.environ.get('VAJRA_CONFIG'):
            try:
                runtime_config = json.loads(os.environ['VAJRA_CONFIG'])
                self._deep_update(config, runtime_config)
            except Exception as e:
                logger.warning(f"Failed to load runtime config from env var: {e}")
        
        return config
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """Recursively update dictionary"""
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _validate_config(self):
        """Validate configuration values"""
        if self.config['audio']['max_volume'] > 1.0:
            logger.warning("max_volume exceeds 1.0, clamping to 1.0")
            self.config['audio']['max_volume'] = 1.0
        
        if self.config['hardware']['level'] not in [2, 3]:
            raise ValueError("hardware.level must be 2 or 3")
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

# Global instance
settings = EnhancedConfig(os.environ.get('VAJRA_ENV', 'development'))