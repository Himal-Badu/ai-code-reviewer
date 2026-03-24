"""Configuration management for AI Code Reviewer.

This module handles all configuration aspects including:
- File-based configuration storage
- Environment variable support
- Default values and validation
- Configuration profiles
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ConfigProfile:
    """Configuration profile for different use cases."""
    name: str
    description: str
    settings: Dict[str, Any] = field(default_factory=dict)


class Config:
    """Manage configuration for AI Code Reviewer."""

    DEFAULT_CONFIG = {
        "api_key": None,
        "model": "gpt-4",
        "severity_threshold": "low",
        "output_format": "text",
        "max_file_size": 50000,
        "enable_cache": True,
        "cache_ttl_hours": 24,
        "rate_limit_calls": 100,
        "rate_limit_period": 60,
        "exclude_patterns": [".git", "__pycache__", "node_modules", ".venv"],
        "enable_security_scan": True,
        "enable_ai_analysis": True,
        "max_concurrent_files": 5,
        "analysis_timeout": 60,
        "language": "auto",
    }

    # Predefined profiles
    PROFILES = {
        "fast": ConfigProfile(
            name="fast",
            description="Fast analysis with minimal checks",
            settings={
                "enable_cache": True,
                "max_file_size": 30000,
                "enable_security_scan": True,
                "enable_ai_analysis": False,
            }
        ),
        "thorough": ConfigProfile(
            name="thorough",
            description="Complete analysis with all checks",
            settings={
                "enable_cache": True,
                "max_file_size": 100000,
                "enable_security_scan": True,
                "enable_ai_analysis": True,
                "max_concurrent_files": 2,
            }
        ),
        "security": ConfigProfile(
            name="security",
            description="Security-focused analysis",
            settings={
                "enable_security_scan": True,
                "enable_ai_analysis": True,
                "severity_threshold": "medium",
            }
        ),
    }

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4", 
                 profile: Optional[str] = None):
        self.config = self.DEFAULT_CONFIG.copy()
        logger.debug("Initializing configuration")
        
        # Apply profile if specified
        if profile and profile in self.PROFILES:
            logger.debug(f"Applying profile: {profile}")
            self.config.update(self.PROFILES[profile].settings)
        
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
                logger.debug("Using API key from environment variable")
                self.config["api_key"] = env_key
        
        # Validate configuration
        self._validate()

    def _validate(self) -> None:
        """Validate configuration values."""
        # Validate model
        valid_models = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o"]
        model = self.config.get("model")
        if model and model not in valid_models:
            logger.warning(f"Model {model} not in known models, proceeding anyway")
        
        # Validate severity threshold
        valid_severities = ["critical", "high", "medium", "low", "all"]
        severity = self.config.get("severity_threshold")
        if severity and severity not in valid_severities:
            logger.warning(f"Invalid severity threshold: {severity}, using 'low'")
            self.config["severity_threshold"] = "low"
        
        # Validate file size
        max_size = self.config.get("max_file_size", 0)
        if max_size < 1000:
            logger.warning("max_file_size too small, setting to 1000")
            self.config["max_file_size"] = 1000

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

    def get_available_profiles(self) -> List[str]:
        """Get list of available configuration profiles."""
        return list(self.PROFILES.keys())

    def apply_profile(self, profile_name: str) -> bool:
        """Apply a configuration profile."""
        if profile_name not in self.PROFILES:
            logger.error(f"Unknown profile: {profile_name}")
            return False
        
        profile = self.PROFILES[profile_name]
        self.config.update(profile.settings)
        logger.info(f"Applied profile: {profile_name}")
        return True

    def reset_to_defaults(self):
        """Reset configuration to default values."""
        self.config = self.DEFAULT_CONFIG.copy()
        logger.info("Configuration reset to defaults")

    def export_config(self, path: Path) -> None:
        """Export configuration to a file."""
        with open(path, "w") as f:
            json.dump(self.config, f, indent=2)
        logger.info(f"Configuration exported to {path}")

    def import_config(self, path: Path) -> bool:
        """Import configuration from a file."""
        try:
            with open(path, "r") as f:
                imported = json.load(f)
                self.config.update(imported)
            logger.info(f"Configuration imported from {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to import config: {e}")
            return False

    def masked_config(self) -> Dict[str, Any]:
        """Get configuration with sensitive values masked."""
        masked = self.config.copy()
        if masked.get("api_key"):
            key = masked["api_key"]
            if len(key) > 8:
                masked["api_key"] = f"{key[:4]}...{key[-4:]}"
            else:
                masked["api_key"] = "***"
        return masked


def get_config() -> Config:
    """Get the global configuration instance."""
    return Config()