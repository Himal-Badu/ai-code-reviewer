"""Configuration management."""

import os
import json
from pathlib import Path
from typing import Any, Optional


class Config:
    """Manage configuration for AI Code Reviewer."""

    DEFAULT_CONFIG = {
        "api_key": None,
        "model": "gpt-4",
        "severity_threshold": "low",
        "output_format": "text",
    }

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Load from file
        self._load()
        
        # Override with provided values
        if api_key:
            self.config["api_key"] = api_key
        if model:
            self.config["model"] = model
        
        # Also check environment variable
        if not self.config.get("api_key"):
            env_key = os.environ.get("OPENAI_API_KEY")
            if env_key:
                self.config["api_key"] = env_key

    def _load(self):
        """Load configuration from file."""
        config_path = self._get_config_path()
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
            except Exception:
                pass

    def _get_config_path(self) -> Path:
        """Get the path to the config file."""
        home = Path.home()
        config_dir = home / ".config" / "ai-code-reviewer"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.json"

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set a configuration value."""
        self.config[key] = value

    def save(self):
        """Save configuration to file."""
        config_path = self._get_config_path()
        with open(config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def get_all(self) -> dict:
        """Get all configuration values."""
        return self.config.copy()


def get_config() -> Config:
    """Get the global configuration instance."""
    return Config()