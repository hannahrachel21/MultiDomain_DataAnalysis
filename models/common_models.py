from typing import List, Dict, Optional
from pydantic import BaseModel

class SheetInfo(BaseModel):
    sheet_name: str
    n_rows: int
    n_cols: int

class PreviewRequest(BaseModel):
    session_id: str
    sheet_name: str
    n_rows: int = 20

class StatsRequest(BaseModel):
    session_id: str
    sheet_name: str

class VizConfig(BaseModel):
    chart_type: str           # e.g. "bar", "line", "histogram", "box"
    x: Optional[str] = None
    y: Optional[str] = None
    hue: Optional[str] = None
    description: str
    image_base64: Optional[str] = None

class VizRequest(BaseModel):
    session_id: str
    sheet_name: str

class InsightRequest(BaseModel):
    session_id: str
    sheet_name: str
    domain: str  # "retail", "manufacturing", "education", or "auto"
