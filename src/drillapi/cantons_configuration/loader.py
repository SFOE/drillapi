"""Load and validate cantonal configuration from per-canton YAML files.

Each canton lives in its own file at ``data/<CODE>.yaml`` (e.g. ``data/ZH.yaml``).
Files are parsed with ``yaml.safe_load`` and validated against
:class:`~drillapi.cantons_configuration.schema.CantonConfig`.

Design goals (fail fast, no silent breakage):

* **Validate everything at import time.** :data:`CANTONS` is built when this
  module is first imported (which happens during app startup via the route
  modules). An invalid or missing config raises :class:`ConfigError` immediately,
  so the process/container never comes up serving broken data.
* **Aggregate errors.** All files are checked and *every* problem is reported in
  a single exception, rather than failing on the first bad file.
* **Load once.** Results are cached; warm Lambda invocations and repeated calls
  pay nothing.
* **Package-relative paths.** The data directory is resolved from this file's
  location, not the process CWD, so it works identically under uvicorn, pytest,
  and AWS Lambda (Mangum).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from .schema import CantonConfig, CantonsConfiguration

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"

# Canton code must be exactly two uppercase ASCII letters (matches the API).
_CODE_LENGTH = 2


class ConfigError(RuntimeError):
    """Raised when the cantonal configuration cannot be loaded or validated.

    Carries a human-readable, aggregated message listing every problem found so
    the whole configuration can be fixed in one pass.
    """


def _parse_file(path: Path) -> dict:
    """Read and YAML-parse a single file, returning the raw mapping."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:  # malformed YAML syntax
        raise ConfigError(f"{path.name}: invalid YAML syntax: {exc}") from exc
    except OSError as exc:  # unreadable file
        raise ConfigError(f"{path.name}: cannot read file: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(
            f"{path.name}: expected a mapping at the top level, got {type(raw).__name__}"
        )
    return raw


def _load_from_dir(data_dir: Path) -> dict[str, CantonConfig]:
    """Load, validate and index every ``<CODE>.yaml`` file in ``data_dir``.

    Raises :class:`ConfigError` with an aggregated message if the directory is
    missing/empty or any file is invalid.
    """
    if not data_dir.is_dir():
        raise ConfigError(f"canton config directory not found: {data_dir}")

    files = sorted(data_dir.glob("*.yaml"))
    if not files:
        raise ConfigError(f"no canton YAML files found in {data_dir}")

    cantons: dict[str, CantonConfig] = {}
    errors: list[str] = []

    for path in files:
        code = path.stem
        if len(code) != _CODE_LENGTH or not code.isascii() or not code.isupper():
            errors.append(
                f"{path.name}: filename must be a 2-letter uppercase canton code "
                f"(e.g. ZH.yaml), got {code!r}"
            )
            continue

        try:
            raw = _parse_file(path)
        except ConfigError as exc:
            errors.append(str(exc))
            continue

        try:
            config = CantonConfig.model_validate(raw)
        except ValidationError as exc:
            errors.append(f"{path.name}: schema validation failed:\n{exc}")
            continue

        if config.name != code:
            # The in-file `name` must match the filename code so lookups by code
            # and the serialized `name` never disagree.
            errors.append(
                f"{path.name}: 'name' is {config.name!r} but filename implies {code!r}"
            )
            continue

        if code in cantons:
            errors.append(f"{path.name}: duplicate canton code {code!r}")
            continue

        cantons[code] = config

    if errors:
        joined = "\n\n".join(f"  - {e}" for e in errors)
        raise ConfigError(
            f"cantonal configuration failed validation ({len(errors)} problem(s)):\n{joined}"
        )

    return cantons


@lru_cache(maxsize=1)
def load_cantons() -> dict[str, CantonConfig]:
    """Return the validated canton configs keyed by code, loading once.

    Raises :class:`ConfigError` on any problem. Cached: subsequent calls return
    the same object without re-reading the filesystem.
    """
    cantons = _load_from_dir(DATA_DIR)
    logger.info("Loaded %d canton configuration(s) from %s", len(cantons), DATA_DIR)
    return cantons


def get_cantons_configuration() -> CantonsConfiguration:
    """Return the full validated configuration as a typed container."""
    return CantonsConfiguration(cantons_configurations=load_cantons())


def as_legacy_dict() -> dict:
    """Return the configuration in the legacy ``CANTONS`` dict shape.

    Produces ``{"cantons_configurations": {<CODE>: {...}}}`` with absent optional
    keys omitted, matching the exact payload the API has always returned.
    """
    return {
        "cantons_configurations": {
            # mode="json" renders GroundSuitability enums as plain ints, matching
            # the exact types the legacy CANTONS dict exposed to clients.
            code: config.model_dump(exclude_none=True, mode="json")
            for code, config in load_cantons().items()
        }
    }


# Validate at import time so a broken config fails fast at startup / in CI.
# `app.py` imports the route modules, which import this package, so any
# ConfigError surfaces before the server accepts traffic.
CANTONS: dict = as_legacy_dict()
