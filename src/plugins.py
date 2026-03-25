"""Plugin system for AI Code Reviewer."""

from typing import Dict, Any, List, Callable, Optional
from abc import ABC, abstractmethod


class ScannerPlugin(ABC):
    """Base class for scanner plugins."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description."""
        pass
    
    @abstractmethod
    def scan(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Scan file and return issues."""
        pass


class PluginRegistry:
    """Registry for scanner plugins."""
    
    def __init__(self):
        self._plugins: Dict[str, ScannerPlugin] = {}
    
    def register(self, plugin: ScannerPlugin) -> None:
        """Register a plugin."""
        self._plugins[plugin.name] = plugin
    
    def unregister(self, name: str) -> None:
        """Unregister a plugin."""
        if name in self._plugins:
            del self._plugins[name]
    
    def get_plugin(self, name: str) -> Optional[ScannerPlugin]:
        """Get plugin by name."""
        return self._plugins.get(name)
    
    def get_all_plugins(self) -> List[ScannerPlugin]:
        """Get all registered plugins."""
        return list(self._plugins.values())
    
    def scan_with_plugins(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Scan with all plugins."""
        all_issues = []
        for plugin in self._plugins.values():
            issues = plugin.scan(file_path, content)
            all_issues.extend(issues)
        return all_issues


# Global registry
_registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    """Get global plugin registry."""
    return _registry


def register_plugin(plugin: ScannerPlugin) -> None:
    """Register a plugin globally."""
    _registry.register(plugin)


class CustomRulePlugin(ScannerPlugin):
    """Plugin for custom scanning rules."""
    
    def __init__(self, name: str, rules: List[Callable]):
        self._name = name
        self._rules = rules
        self._description = "Custom rule-based scanner"
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    def scan(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Scan using custom rules."""
        issues = []
        for rule in self._rules:
            result = rule(content, file_path)
            if result:
                issues.append(result)
        return issues