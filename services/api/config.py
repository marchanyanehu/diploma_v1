"""
DEPRECATED: Configuration moved to shared.config

This module is maintained for backward compatibility only.
Import from shared.config instead.
"""

# Re-export everything from shared.config for backward compatibility
from shared.config import Settings, settings, DEFAULT_REDIS_URL

__all__ = ['Settings', 'settings', 'DEFAULT_REDIS_URL']
