import sys
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from services.web_scraper.core.browser_manager import BrowserManager
from services.web_scraper.config import MAX_CONCURRENT_BROWSERS, MAX_AUDITS_BEFORE_RESTART, MAX_UPTIME_SECONDS

logger = logging.getLogger(__name__)

browser_manager = BrowserManager(
    max_concurrent_browsers=MAX_CONCURRENT_BROWSERS,
    max_audits_before_restart=MAX_AUDITS_BEFORE_RESTART,
    max_uptime_seconds=MAX_UPTIME_SECONDS,
)

# Move routing imports below browser_manager declaration to avoid circular import issues
from api.routes import health, blacklist, scan, audit

@asynccontextmanager
async def lifespan(app: FastAPI):
    await browser_manager.start()
    logger.info("Playwright Browser Manager is ready")
    yield
    await browser_manager.stop()
    logger.info("Playwright Browser Manager has been shut down")

app = FastAPI(title="AI Lead Hunter Fast Scan Service", lifespan=lifespan)

from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="AI-Powered Lead Generation Pipeline",
        version="1.0.0",
        description="""
        ## Features
        - **Real-time Web Scraping** via Playwright (Google Maps)
        - **Vector RAG Retrieval** with Supabase pgvector
        - **Batched LLM Evaluation** (Groq Llama-3.1)
        - **Self-Learning Pipeline** (auto-blacklist corporate chains)
        - **Production-Ready** Docker + n8n orchestration
        
        ## Core Endpoints
        - `/api/scan` - Scrape and extract leads
        - `/api/audit/evaluate` - Evaluate lead quality with RAG
        - `/api/blacklist` - Manage corporate blacklist
        - `/health` - System status
        """,
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/")
def read_root():
    return {"message": "Welcome to the Autonomous AI Lead Hunter Fast Scan Service"}

app.include_router(health.router, tags=["Health"])
app.include_router(blacklist.router, tags=["Blacklist"])
app.include_router(scan.router, tags=["Scanner"])
app.include_router(audit.router, tags=["Digital Footprint Audit"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


