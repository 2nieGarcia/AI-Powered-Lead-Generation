from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
import logging

from schemas.audit import VectorUpdateRequest
from services.llm_scraper.models import AuditReport, AuditRequest
from services.llm_scraper.llm_client import get_audit_report
from services.evaluator.evaluator import evaluate_lead

from services.web_scraper.models import ScrapeRequest, AuditErrorResponse
from services.web_scraper.core.browser_manager import BrowserManager
from services.web_scraper.core.analyzer import run_audit

logger = logging.getLogger(__name__)

router = APIRouter()

# The global browser manager is usually attached to the app state or passed down.
# For simplicity, we can import it from the module that initiates it, or we create a getter.
# For now, let's keep it clean: We will assume it is passed in via dependencies or initialized here.
# Since browser_manager needs to be persistent, we will fetch it from main where we initialize it.
from main import browser_manager

@router.post("/api/audit/footprint", response_model=AuditReport)
async def audit_footprint(request: AuditRequest):
    try:
        report = await get_audit_report(request)
        return report
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"LLM output parsing failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")

@router.post("/api/audit/evaluate")
async def evaluate_footprint(payload: dict = Body(...)):
    try:
        if not payload.get("business_name"):
            raise HTTPException(status_code=400, detail="Missing business_name in payload")
        
        logger.info(f"Received evaluate request for: {payload.get('business_name')}")
        evaluation = await evaluate_lead(payload)
        return evaluation

    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@router.post("/api/audit/embed-and-update")
async def embed_and_update(request: VectorUpdateRequest):
    try:
        from services.evaluator.supabase_client import update_record_vector
        await update_record_vector(request.table_name, request.id, request.reason_text)
        return {"status": "success", "id": request.id, "table": request.table_name}
    except Exception as e:
        logger.error(f"Vector update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/audit/website")
async def analyze_website(request: ScrapeRequest):
    context = None
    try:
        # Assuming browser_manager is accessible globally.
        context = await browser_manager.acquire_context()
        result = await run_audit(context, request.url)
        return JSONResponse(content=result)

    except Exception as e:
        logger.exception("Unhandled error during audit for %s: %s", request.url, e)
        error_response = AuditErrorResponse(
            status="navigation_error",
            resolved_url=request.url,
            error_reason=f"Internal service error: {str(e)}",
        )
        return JSONResponse(content=error_response.model_dump())

    finally:
        if context:
            try:
                await context.close()
            except Exception as e:
                logger.warning("Error closing browser context: %s", e)
            browser_manager.release_context()


