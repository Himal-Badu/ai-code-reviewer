"""Configuration management for AI Code Reviewer."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import os


class Config:
    """Configuration manager for AI Code Reviewer."""
    
    DEFAULT_CONFIG = {
        "version": "1.0.0",
        "scanner": {
            "enabled": True,
            "security_scan": True,
            "ai_analysis": True,
            "max_file_size": 1048576,
            "exclude_patterns": ["*.pyc", "__pycache__", ".git", "venv"]
        },
        "ai": {
            "model": "gpt-4",
            "temperature": 0.3,
            "max_tokens": 2000
        },
        "security": {
            "bandit_severity": "medium",
            "check_sql_injection": True,
            "check_hardcoded_secrets": True
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get default config path."""
        home = Path.home()
        return str(home / ".ai-code-reviewer" / "config.json")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if Path(self.config_path).exists():
            with open(self.config_path) as f:
                return json.load(f)
        return self.DEFAULT_CONFIG.copy()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by key."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def set(self, key: str, value: Any) -> None:
        """Set config value."""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def save(self) -> None:
        """Save configuration to file."""
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def reset(self) -> None:
        """Reset to default configuration."""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save()


# Global config instance
_config = None


def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config