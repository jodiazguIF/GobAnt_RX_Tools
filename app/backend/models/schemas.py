from pydantic import BaseModel
from typing import Optional, Dict, List, Any

class AskRequest(BaseModel):
    question: str
    filters: Optional[Dict[str, Any]] = None

class AskResponse(BaseModel):
    data: List[Dict[str, Any]]
    spec: Dict[str, Any]
    summary: str
