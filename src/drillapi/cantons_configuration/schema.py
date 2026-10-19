"""Pydantic schema for cantonal geoservice configuration.

This module defines the typed contract for a single canton's configuration.
Each canton is stored as a YAML file under ``data/`` and validated against
:class:`CantonConfig` at load time (see :mod:`.loader`), so malformed data
fails fast at startup / in CI instead of mid-request against a live WMS.

The schema is intentionally strict (``extra="forbid"``) so that a typo in a
field name is rejected rather than silently ignored. It is, however, lenient
exactly where the existing production data requires it (optional ``desc``,
layer-level ``target_harmonized_value`` / ``id``, empty-string URLs, and
ground-control-point rows of 3 to 5 elements). See the field docstrings for
why each allowance exists.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from drillapi.models.models import GroundSuitability

# A permissive URL alias. We deliberately do NOT use pydantic's HttpUrl here:
# several production entries use an empty string to mean "no legend/geoportal"
# and HttpUrl would both reject that and rewrite/normalise valid URLs (adding
# trailing slashes), which would change the bytes we serialise back to clients.
# URL *shape* is validated by `_looks_like_url` below instead.
Url = Annotated[str, Field(description="Absolute http(s) URL, or empty string if none")]


def _looks_like_url(value: str) -> str:
    """Validate that a non-empty URL field is an absolute http(s) URL."""
    if value == "":
        return value
    if not value.startswith(("http://", "https://")):
        raise ValueError(
            f"expected an absolute http(s) URL or empty string, got: {value!r}"
        )
    return value


class PropertyValue(BaseModel):
    """A single mappable attribute value within a layer.

    ``name`` is matched against the feature attribute returned by the
    geoservice; ``target_harmonized_value`` is the normalised category it maps
    to. ``desc`` is a human-readable label and is optional because a number of
    cantons omit it (e.g. VD "Limitation", AR "zulässig").
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    target_harmonized_value: GroundSuitability
    # Optional: several cantons omit it entirely. Defaults to None (not "") so
    # that serialising back excludes the key where it was absent, preserving the
    # exact API response bytes. processing.py reads it via .get() and tolerates None.
    desc: str | None = None


class Layer(BaseModel):
    """A geoservice layer queried for a canton.

    Most cantons use ``property_values`` to map an attribute value to a
    harmonized category. Some (ZH's zone layers) instead rely on mere feature
    presence and carry a layer-level ``target_harmonized_value`` with no
    ``property_values``. ESRI/arcgis cantons (GE, FR) additionally carry a
    numeric ``id`` used to build the REST query URL.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    property_name: str
    property_values: list[PropertyValue] | None = None
    # Layer-level fallback used when `property_values` is absent (ZH zones).
    target_harmonized_value: GroundSuitability | None = None
    # ESRI REST layer id (GE, FR). Required by processing for the ESRI branch.
    id: int | None = None
    # Optional human-readable layer description (FR only today).
    desc: str | None = None


# A ground-control-point row: [east, north, expected_harmonized, label?, extra?]
# Only indices 0..2 are consumed (by the checker). Rows legally have 3, 4 or 5
# elements and coordinates may be int or float, so we validate the invariant
# (length + leading numeric coords + integer category) without over-constraining.
GroundControlPoint = Annotated[
    list[float | int | str],
    Field(min_length=3, max_length=5),
]


class HarmonyMapEntry(BaseModel):
    """Legacy sum→value mapping entry (currently only present on LU).

    Not consumed by any code path today; retained so the configuration
    round-trips exactly and no data is silently dropped during migration.
    """

    model_config = ConfigDict(extra="forbid")

    sum: int
    value: GroundSuitability


class CantonConfig(BaseModel):
    """Full configuration for one canton.

    ``extra="forbid"`` means any unknown key (typically a typo) is rejected at
    load time. Every optional field below corresponds to a real variation in
    the existing data; required fields are present for every canton.
    """

    model_config = ConfigDict(extra="forbid")

    active: bool
    name: str = Field(min_length=2, max_length=2)
    ground_control_point: list[GroundControlPoint]

    cantonal_energy_service_url: Url = ""
    wms_url: Url
    query_url: Url
    thematic_geoportal_url: Url = ""
    legend_url: Url = ""

    info_format: str
    # Pixel/CRS buffer around the clicked point for WMS GetFeatureInfo bbox.
    # All existing values are integers (10, 30); kept as int to preserve the
    # exact JSON type served to clients.
    bbox_delta: int = 10
    style: str = ""
    layers: list[Layer] = Field(min_length=1)

    # Legacy / currently-unused fields (LU only). Retained for lossless
    # round-tripping; see HarmonyMapEntry.
    harmonyMap: list[HarmonyMapEntry] | None = None
    loopLayers: bool | None = None

    @field_validator(
        "cantonal_energy_service_url",
        "wms_url",
        "query_url",
        "thematic_geoportal_url",
        "legend_url",
    )
    @classmethod
    def _validate_url(cls, value: str) -> str:
        return _looks_like_url(value)

    @field_validator("ground_control_point")
    @classmethod
    def _validate_gcp_rows(
        cls, rows: list[list[float | int | str]]
    ) -> list[list[float | int | str]]:
        """Each row must start with two numeric coords and an int category."""
        # NOTE: pydantic field validators must raise ValueError (not TypeError)
        # for the failure to be collected into a ValidationError, hence noqa TRY004.
        for idx, row in enumerate(rows):
            east, north, category = row[0], row[1], row[2]
            if not isinstance(east, (int, float)) or isinstance(east, bool):
                raise ValueError(  # noqa: TRY004
                    f"ground_control_point[{idx}][0] (east) must be numeric"
                )
            if not isinstance(north, (int, float)) or isinstance(north, bool):
                raise ValueError(  # noqa: TRY004
                    f"ground_control_point[{idx}][1] (north) must be numeric"
                )
            if not isinstance(category, int) or isinstance(category, bool):
                raise ValueError(  # noqa: TRY004
                    f"ground_control_point[{idx}][2] (category) must be an int"
                )
        return rows


class CantonsConfiguration(BaseModel):
    """Top-level container mirroring the legacy ``CANTONS`` dict shape.

    Keeps the public API contract intact: endpoints serialise this back to
    ``{"cantons_configurations": {<CODE>: {...}}}``.
    """

    model_config = ConfigDict(extra="forbid")

    cantons_configurations: dict[str, CantonConfig]
