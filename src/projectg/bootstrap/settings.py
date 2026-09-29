"""Compatibility exports for runtime configuration.

The canonical settings adapter lives in infrastructure; bootstrap may depend on
it, while infrastructure modules must not depend on the composition root.
"""

from projectg.infrastructure.configuration.settings import PROJECT_ROOT, ROOT, Settings, settings

__all__ = ["PROJECT_ROOT", "ROOT", "Settings", "settings"]
