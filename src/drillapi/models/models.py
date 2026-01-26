from pydantic import BaseModel
from typing import Optional, List, Literal


class LayerResult(BaseModel):
    layer: str
    property_name: str
    value: str


class GroundCategory(BaseModel):
    layer_results: List[LayerResult]
    harmonized_value: Literal[1, 2, 3, 4, 5, 6, 99] = 4
    source_values: str


class ResultDetail(BaseModel):
    message: str = None
    full_url: Optional[str] = None
    detail: Optional[str] = None


class SuitabilityFeature(BaseModel):
    coord_x: float
    coord_y: float
    canton: str = None
    canton_config: Optional[dict] = None
    ground_category: GroundCategory
    result_detail: ResultDetail
