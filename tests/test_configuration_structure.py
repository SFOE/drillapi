from pydantic import BaseModel, HttpUrl, field_validator

from drillapi.cantons_configuration.cantons import CANTONS


class PropertyValue(BaseModel):
    name: str
    target_harmonized_value: int


class Layer(BaseModel):
    name: str
    property_name: str
    property_values: list[PropertyValue] | None = None
    target_harmonized_value: int | None = None


class Cantonconfig(BaseModel):
    active: bool
    name: str
    ground_control_point: list[list[int | float | str]]
    wms_url: HttpUrl
    query_url: HttpUrl
    thematic_geoportal_url: HttpUrl | None
    cantonal_energy_service_url: HttpUrl | None
    legend_url: str
    info_format: str
    style: str | None
    layers: list[Layer]

    @field_validator("layers")
    @classmethod
    def check_at_least_one_layer(cls, v):
        if not v:
            raise ValueError("There must be at least one layer")
        return v

    @field_validator(
        "wms_url",
        "thematic_geoportal_url",
        "cantonal_energy_service_url",
        "query_url",
        mode="before",
    )
    @classmethod
    def allow_empty_urls(cls, v):
        if v == "":
            return None
        return v


def test_cantons_configuration_integrity():
    """
    Ensure all cantons configuration entries respect the Region structure
    and no structural damage has been caused.
    """
    for canton_data in CANTONS["cantons_configurations"].values():
        # Pydantic validation
        Cantonconfig(**canton_data)


if __name__ == "__main__":
    test_cantons_configuration_integrity()
