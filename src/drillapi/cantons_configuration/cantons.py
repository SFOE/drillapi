"""Backwards-compatible access to the cantonal configuration.

The canonical source of truth is now the per-canton YAML files under ``data/``,
loaded and validated by :mod:`drillapi.cantons_configuration.loader`.

This module is kept so existing imports (``from drillapi.cantons_configuration
import cantons`` / ``cantons.CANTONS``) continue to work. ``CANTONS`` is the
legacy-shaped dict (``{"cantons_configurations": {<CODE>: {...}}}``) produced
from the validated YAML, so every consumer keeps receiving plain dicts with the
exact same keys and values as before.

Importing this module triggers validation of all YAML files; a malformed
configuration raises
:class:`~drillapi.cantons_configuration.loader.ConfigError` at import time
(fail fast), so the app never starts serving broken data.
"""

from __future__ import annotations

from .loader import CANTONS

__all__ = ["CANTONS"]
