import os
import logging
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
from supabase import create_client, Client

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Supabase credentials not set")
    
    print(f"DEBUG: Connecting to Supabase at {SUPABASE_URL}")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@router.get("/blacklist")
def get_blacklist():
    try:
        supabase = get_supabase()
        response = supabase.table("blacklist").select("*").execute()
        names = [item['name'] for item in response.data]
        return {"blacklist": names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScanRequest(BaseModel):
    target: str
    max_result: int = 20

class LeadResult(BaseModel):
    name: str
    place_id: str
    phone: str | None = None
    address: str | None = None
    website: str | None = None

class ScanResponse(BaseModel):
    results: list[LeadResult]

@router.get("/health")
def health_check():
    return {"status": "fast-scan is alive"}

@router.post("/scan-maps", response_model=ScanResponse)
async def scan_maps(request: ScanRequest):
    logger.info(f"Starting scan for : {request.target} with max results {request.max_result}")
    results = []
    raw_json_responses = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        async def handle_response(response):
            if "search" in response.url and response.status == 200:
                try:
                    text = await response.text()
                    raw_json_responses.append(text)
                except:
                    pass

        page.on("response", handle_response)

        await page.goto(f"https://www.google.com/maps/search/{request.target}")
        await page.wait_for_selector('div[role="feed"]', timeout=10000)

        scrollable = page.locator('div[role="feed"]')
        previous_count = 0

        while True:
            await scrollable.evaluate("el => el.scrollTop += 3000")
            await page.wait_for_timeout(2000)

            cards = await page.locator('div[role="feed"] > div > div > a').all()
            if len(cards) <= previous_count or len(cards) >= request.max_result:
                break
            previous_count = len(cards)


        cards = await page.locator('div[role="feed"] > div > div > a').all()
        for card in cards[:request.max_result]:
            try:
                name = await card.get_attribute('aria-label') or "N/A"
                href = await card.get_attribute('href') or ""

                place_id = ""
                if "!19s" in href:
                    place_id = href.split("!19s")[1].split("?")[0]

                await card.click()
                await page.wait_for_timeout(2000)

                phone = None

                try:
                    phone_el = page.locator('button[data-item-id^="phone"]')
                    if await phone_el.count() > 0:
                        raw_phone = await phone_el.first.get_attribute('data-item-id')
                        if raw_phone:
                            phone = raw_phone.replace("phone:tel:", "").strip()
                except Exception as e:
                    logger.warning(f"[{name}] Phone extraction failed: {e}")

                address = None
                try:
                    address_el = page.locator('button[data-item-id^="address"]')
                    if await address_el.count() > 0:
                        raw_address = await address_el.first.inner_text()
                        if raw_address:
                            address = raw_address.replace("", "").replace("\n", " ").strip()
                except Exception as e:
                    logger.warning(f"[{name}] Address extraction failed: {e}")

                website = None

                try:
                    website_el = page.locator('a[data-item-id^="authority"]')
                    if await website_el.count() > 0:
                        raw_website = await website_el.first.get_attribute('href')
                        if raw_website:
                            website = raw_website.strip()
                except Exception:
                    logger.warning(f"[{name}] Website extraction failed: {e}")

                results.append(LeadResult(
                    name=name,
                    place_id=place_id,
                    phone=phone,
                    address=address,
                    website=website
                ))
                logger.info(f"Extracted lead: {name} | Place ID: {place_id} | Phone: {phone} | Address: {address} | Website: {website}")
            except Exception as e:
                logger.error(f"Failed to process card {name if 'name' in locals() else 'unknown'}: {e}")
                continue
        

        await browser.close()

    return ScanResponse(results=results)