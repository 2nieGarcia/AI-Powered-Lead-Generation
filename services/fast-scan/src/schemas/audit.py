from pydantic import BaseModel

class VectorUpdateRequest(BaseModel):
    id: int
    table_name: str
    reason_text: str


