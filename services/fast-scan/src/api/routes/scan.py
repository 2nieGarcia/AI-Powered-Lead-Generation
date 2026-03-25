from fastapi import APIRouter
from schemas.scan import ScanRequest, ScanResponse
from services.scrapper import scrape_google_maps

router = APIRouter()

@router.post("/scan-maps", response_model=ScanResponse)
async def scan_maps(request: ScanRequest):
    # Call the service layer to do the heavy lifting
    scraped_leads = await scrape_google_maps(request.target, request.max_result)
    return ScanResponse(results=scraped_leads)


