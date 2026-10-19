"""Validate the per-canton YAML configuration.

These tests are the safety net that guarantees a malformed cantonal config can
never reach production: they load every ``data/<CODE>.yaml`` file through the
real loader + Pydantic schema, assert the invariants the app relies on, and
confirm fail-fast behaviour on bad input. CI runs this suite, so a broken YAML
fails the pipeline before deploy.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from drillapi.cantons_configuration import loader
from drillapi.cantons_configuration.loader import (
    DATA_DIR,
    ConfigError,
    as_legacy_dict,
    load_cantons,
)
from drillapi.cantons_configuration.schema import CantonConfig, CantonsConfiguration

ALL_YAML_FILES = sorted(DATA_DIR.glob("*.yaml"))
ALL_CODES = [p.stem for p in ALL_YAML_FILES]


def test_data_dir_has_canton_files():
    assert ALL_YAML_FILES, f"no canton YAML files found in {DATA_DIR}"


def test_all_cantons_load_and_validate():
    """The whole configuration loads and validates without error."""
    cantons = load_cantons()
    assert cantons, "expected at least one canton"
    for code, config in cantons.items():
        assert isinstance(config, CantonConfig)
        assert config.name == code


@pytest.mark.parametrize("yaml_file", ALL_YAML_FILES, ids=ALL_CODES)
def test_each_file_is_valid(yaml_file: Path):
    """Each file individually parses as a mapping and validates against the schema."""
    raw = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    assert isinstance(raw, dict), f"{yaml_file.name}: top level must be a mapping"
    config = CantonConfig.model_validate(raw)
    # Filename code must agree with the in-file name.
    assert config.name == yaml_file.stem


@pytest.mark.parametrize("yaml_file", ALL_YAML_FILES, ids=ALL_CODES)
def test_each_canton_has_usable_layers(yaml_file: Path):
    """Every layer is usable: it has either property_values or a layer-level target."""
    config = CantonConfig.model_validate(
        yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    )
    assert config.layers, f"{yaml_file.name}: must have at least one layer"
    for layer in config.layers:
        assert layer.property_values or layer.target_harmonized_value is not None, (
            f"{yaml_file.name}: layer {layer.name!r} has neither property_values "
            f"nor a layer-level target_harmonized_value"
        )


@pytest.mark.parametrize("yaml_file", ALL_YAML_FILES, ids=ALL_CODES)
def test_esri_layers_have_id(yaml_file: Path):
    """ESRI/arcgis cantons must provide a layer id (processing requires it)."""
    config = CantonConfig.model_validate(
        yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    )
    if "arcgis" in config.info_format.lower():
        for layer in config.layers:
            assert layer.id is not None, (
                f"{yaml_file.name}: ESRI layer {layer.name!r} is missing 'id'"
            )


def test_full_configuration_container_validates():
    """The aggregated container validates and preserves all codes."""
    container = CantonsConfiguration(cantons_configurations=load_cantons())
    assert set(container.cantons_configurations) == set(ALL_CODES)


def test_as_legacy_dict_shape():
    """The legacy-shaped dict is preserved for the public API contract."""
    legacy = as_legacy_dict()
    assert set(legacy) == {"cantons_configurations"}
    inner = legacy["cantons_configurations"]
    assert set(inner) == set(ALL_CODES)
    # absent optionals are omitted, not serialized as null
    for canton in inner.values():
        assert "active" in canton
        for layer in canton["layers"]:
            for pv in layer.get("property_values") or []:
                assert "desc" not in pv or isinstance(pv["desc"], str)


def test_names_match_filenames():
    for code, config in load_cantons().items():
        assert config.name == code, f"{code}.yaml declares name={config.name!r}"


# --- Fail-fast behaviour (the actual hardening guarantee) ---


def _write(dir_: Path, name: str, content: str) -> None:
    (dir_ / name).write_text(content, encoding="utf-8")


def test_missing_directory_raises():
    with pytest.raises(ConfigError, match="not found"):
        loader._load_from_dir(Path(tempfile.gettempdir()) / "definitely-not-here-xyz")


def test_empty_directory_raises():
    with (
        tempfile.TemporaryDirectory() as d,
        pytest.raises(ConfigError, match="no canton YAML files"),
    ):
        loader._load_from_dir(Path(d))


def test_invalid_yaml_syntax_raises():
    with tempfile.TemporaryDirectory() as d:
        _write(Path(d), "ZH.yaml", "active: true\n  bad: : indentation:")
        with pytest.raises(ConfigError, match="invalid YAML syntax|ZH.yaml"):
            loader._load_from_dir(Path(d))


def test_unknown_field_is_rejected():
    """A typo'd/extra key must fail (extra='forbid')."""
    valid = yaml.safe_load((DATA_DIR / "ZG.yaml").read_text(encoding="utf-8"))
    valid["unexpected_typo_key"] = 1
    with pytest.raises(ValidationError, match="unexpected_typo_key"):
        CantonConfig.model_validate(valid)


def test_name_filename_mismatch_raises():
    with tempfile.TemporaryDirectory() as d:
        # a syntactically valid canton, but name != filename
        _write(
            Path(d),
            "ZH.yaml",
            "active: true\nname: BE\nground_control_point: [[2600000, 1200000, 1]]\n"
            "wms_url: https://x\nquery_url: https://x\ninfo_format: text/plain\n"
            "layers:\n- {name: a, property_name: b, target_harmonized_value: 1}\n",
        )
        with pytest.raises(ConfigError, match="filename implies"):
            loader._load_from_dir(Path(d))


def test_bad_ground_control_point_raises():
    """A GCP row whose category is not an int must be rejected."""
    valid = yaml.safe_load((DATA_DIR / "ZG.yaml").read_text(encoding="utf-8"))
    valid["ground_control_point"] = [[2600000, 1200000, "not-an-int"]]
    with pytest.raises(ValidationError):
        CantonConfig.model_validate(valid)
