from typing import Dict, Any
from pydantic import BaseModel

class SessionData(BaseModel):
    session_id: str
    file_path: str
    file_name: str
    domain: str          # resolved domain for this file
    meta: Dict[str, Any] = {}
