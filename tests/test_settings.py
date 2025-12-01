from typing import List, Optional, Union
from pydantic import BaseModel, HttpUrl, field_validator, ValidationError, conlist
from settings_values.cantons import CANTONS


class PropertyValue(BaseModel):
    name: str
    summand: int


class Layer(BaseModel):
    name: str
    propertyName: str
    propertyValues: Optional[List[PropertyValue]] = None
    summand: Optional[int] = None


class Cantonconfig(BaseModel):
    active: bool
    name: str
    exampleLocation: List[List[Union[int, float, str]]]
    wmsUrl: HttpUrl
    thematic_geoportal_url: Optional[HttpUrl]
    legendUrl: str
    infoFormat: str
    style: Optional[str]
    layers: List[Layer]

    @field_validator("layers")
    @classmethod
    def check_at_least_one_layer(cls, v):
        if not v:
            raise ValueError("There must be at least one layer")
        return v

    @field_validator("wmsUrl", "thematic_geoportal_url", mode="before")
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
