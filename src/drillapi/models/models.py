from pydantic import BaseModel
from typing import Optional, List


class LayerResult(BaseModel):
    layer: str
    property_name: str
    value: str


class GroundCategory(BaseModel):
    layer_results: List[LayerResult]
    harmonized_value: int = 4
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
    status: str
    result_detail: ResultDetail
