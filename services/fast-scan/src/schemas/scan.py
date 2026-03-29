from pydantic import BaseModel

class ScanRequest(BaseModel):
    target: str
    max_result: int = 20
    offset: int = 0

class LeadResult(BaseModel):
    name: str
    place_id: str
    phone: str | None = None
    address: str | None = None
    website: str | None = None
    facebook_url: str | None = None
    instagram_url: str | None = None

class ScanResponse(BaseModel):
    results: list[LeadResult]


