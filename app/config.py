#!/usr/bin/env python3
"""
Configuration management for Streamlit Slack Delivery App
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env file from the project root
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    # python-dotenv not installed, skip loading
    pass

class Config:
    """Configuration management class"""
    
    def __init__(self):
        """Initialize configuration"""
        self.app_dir = Path(__file__).parent
        self.delivery_dir = self.app_dir.parent / "delivery"
        self.arguments_file = self.delivery_dir / "arguments.json"
    
    def get_environment_status(self) -> Dict[str, Any]:
        """Check environment variables status"""
        slack_token = os.getenv('SLACK_BOT_TOKEN') or os.getenv('SLACK_TOKEN')
        default_channel = os.getenv('DELIVERY_TEST_SLACK_DEFAULT_CHANNEL_ID')
        
        return {
            'slack_token_set': bool(slack_token),
            'slack_token_preview': f"{slack_token[:20]}..." if slack_token else None,
            'default_channel_set': bool(default_channel),
            'default_channel': default_channel
        }
    
    def load_default_arguments(self) -> Dict[str, Any]:
        """Load default arguments from JSON file"""
        try:
            if self.arguments_file.exists():
                with open(self.arguments_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Clean up empty strings
                    return {k: v for k, v in data.items() if v != ""}
            return {}
        except Exception:
            return {}
    
    def save_arguments(self, args: Dict[str, Any]) -> bool:
        """Save arguments to JSON file"""
        try:
            # Ensure directory exists
            self.arguments_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.arguments_file, 'w', encoding='utf-8') as f:
                json.dump(args, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def get_default_form_values(self) -> Dict[str, Any]:
        """Get default values for form fields"""
        defaults = self.load_default_arguments()
        
        return {
            'author': defaults.get('author', ''),
            'receiver': defaults.get('receiver', ''),
            'link': defaults.get('link', ''),
            'raw_data_link': defaults.get('raw_data_link', ''),
            'channel': defaults.get('channel', ''),
            'date': defaults.get('date', ''),
            'thread_content': defaults.get('thread_content', ''),
            'thread_ts': defaults.get('thread_ts', ''),
            'verbose': defaults.get('verbose', False)
        }

# Global config instance
config = Config()
