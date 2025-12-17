from typing import List, Optional, Union
from pydantic import BaseModel, HttpUrl, field_validator, ValidationError, conlist
from drillapi.cantons_configuration.cantons import CANTONS


class PropertyValue(BaseModel):
    name: str
    target_harmonized_value: int


class Layer(BaseModel):
    name: str
    property_name: str
    property_values: Optional[List[PropertyValue]] = None
    target_harmonized_value: Optional[int] = None


class Cantonconfig(BaseModel):
    active: bool
    name: str
    ground_control_point: List[List[Union[int, float, str]]]
    wms_url: HttpUrl
    query_url: HttpUrl
    thematic_geoportal_url: Optional[HttpUrl]
    cantonal_energy_service_url: Optional[HttpUrl]
    legend_url: str
    info_format: str
    style: Optional[str]
    layers: List[Layer]

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
    for canton_name, canton_data in CANTONS["cantons_configurations"].items():
        # Pydantic validation
        region = Cantonconfig(**canton_data)


if __name__ == "__main__":
    test_cantons_configuration_integrity()
