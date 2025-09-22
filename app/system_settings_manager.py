"""
System settings management utilities for reading and writing system configuration
"""
import json
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from .github_storage import GitHubStorage
except ImportError:
    from github_storage import GitHubStorage


class SystemSettingsManager:
    def __init__(self):
        self.github_storage = GitHubStorage()
        self.settings_file = "system_settings.json"
    
    def load_settings(self) -> Dict[str, Any]:
        """Load system settings from GitHub repository"""
        try:
            settings = self.github_storage.read_file(self.settings_file)
            return settings if settings is not None else self._get_default_settings()
        except Exception as e:
            print(f"Error loading system settings from GitHub: {e}")
            return self._get_default_settings()
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save system settings to GitHub repository"""
        try:
            # Add timestamp for tracking changes
            settings["last_updated"] = datetime.now().isoformat()
            return self.github_storage.write_file(self.settings_file, settings, "Update system settings")
        except Exception as e:
            print(f"Error saving system settings to GitHub: {e}")
            return False
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default system settings"""
        return {
            "automatic_delivery_enabled": False,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
    
    def get_automatic_delivery_enabled(self) -> bool:
        """Get the current state of automatic delivery system"""
        settings = self.load_settings()
        return settings.get("automatic_delivery_enabled", False)
    
    def set_automatic_delivery_enabled(self, enabled: bool) -> bool:
        """Set the automatic delivery system state"""
        settings = self.load_settings()
        settings["automatic_delivery_enabled"] = enabled
        return self.save_settings(settings)
    
    def get_setting(self, key: str, default_value: Any = None) -> Any:
        """Get a specific setting value"""
        settings = self.load_settings()
        return settings.get(key, default_value)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """Set a specific setting value"""
        settings = self.load_settings()
        settings[key] = value
        return self.save_settings(settings)
