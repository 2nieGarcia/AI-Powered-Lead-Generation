import logging
from playwright.async_api import async_playwright
from schemas.scan import LeadResult

logger = logging.getLogger(__name__)

async def scrape_google_maps(target: str, max_result: int, offset: int = 0) -> list[LeadResult]:
    logger.info(f"Starting scan for : {target} with max results {max_result} | offset of {offset}")
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

        await page.goto(f"https://www.google.com/maps/search/{target}")
        await page.wait_for_selector('div[role="feed"]', timeout=10000)

        scrollable = page.locator('div[role="feed"]')
        previous_count = 0

        while True:
            await scrollable.evaluate("el => el.scrollTop += 3000")
            await page.wait_for_timeout(2000)

            cards = await page.locator('div[role="feed"] > div > div > a').all()
            if len(cards) <= previous_count or len(cards) >= (max_result + offset):
                break
            previous_count = len(cards)


        cards = await page.locator('div[role="feed"] > div > div > a').all()

        target_cards = cards[offset:offset + max_result]

        
        for card in target_cards:
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
                facebook = None
                instagram = None

                try:
                    website_el = page.locator('a[data-item-id^="authority"]')
                    if await website_el.count() > 0:
                        raw_website = await website_el.first.get_attribute('href')
                        if raw_website:
                            raw_website = raw_website.strip()
                            if "facebook.com" in raw_website.lower():
                                facebook = raw_website
                            elif "instagram.com" in raw_website.lower():
                                instagram = raw_website
                            else:
                                website = raw_website



                    all_links = await page.locator('a[href^="http"]').all()
                    for link in all_links:
                        href = await link.get_attribute('href') or ""
                        href_lower = href.lower()

                        if "facebook.com" in href_lower and not facebook:
                            facebook = href.strip()
                        elif "instagram.com" in href_lower and not instagram:
                            instagram = href.strip()
                except Exception as e:
                    logger.warning(f"[{name}] Website extraction failed: {e}")

                results.append(LeadResult(
                    name=name,
                    place_id=place_id,
                    phone=phone,
                    address=address,
                    website=website,
                    facebook_url=facebook,
                    instagram_url=instagram
                ))
                logger.info(f"Extracted lead: {name} | Place ID: {place_id} | Phone: {phone} | Address: {address} | Website: {website}")
            except Exception as e:
                logger.error(f"Failed to process card {name if 'name' in locals() else 'unknown'}: {e}")
                continue
        

        await browser.close()

    return results





