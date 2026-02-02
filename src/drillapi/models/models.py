from pydantic import BaseModel
from typing import Optional, List, Literal
from enum import IntEnum


class LayerResult(BaseModel):
    layer: str
    property_name: str
    value: str


class GroundSuitability(IntEnum):
    OK = 1
    WITH_RESTRICTIONS = 2
    FORBIDDEN = 3
    UNKNOWN = 4
    NOT_AVAILABLE = 5
    NOT_IN_SWITZERLAND = 6
    PROBLEM = 99


class GroundCategory(BaseModel):
    layer_results: List[LayerResult] = []
    harmonized_value: GroundSuitability = GroundSuitability.UNKNOWN
    source_values: str = ""


class ResultDetail(BaseModel):
    message: str = ""
    full_url: Optional[str] = ""
    detail: Optional[str] = ""


class SuitabilityFeature(BaseModel):
    coord_x: float
    coord_y: float
    canton: str = None
    canton_config: Optional[dict] = None
    ground_category: GroundCategory
    result_detail: ResultDetail


# For checker only
class CheckerResult(BaseModel):
    canton: str = ""
    url: str = ""
    content_for_template: GroundCategory = None
    control_status: Literal["error", "success"]
    control_status_message: str = ""
