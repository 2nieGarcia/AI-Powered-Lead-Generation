import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from playwright.async_api import async_playwright
from services.scrapper import _extract_links, _listing_panel

# Minimal copy of the Maps layout: the results feed lists other businesses
# (one of them links to its Facebook page) next to the opened listing's panel.
MAPS_FIXTURE = """
<div role="main" aria-label="Results for dental clinic">
  <div role="feed">
    <div><div><a aria-label="Other Dental" href="https://www.google.com/maps/place/other"></a></div></div>
    <a href="https://www.facebook.com/otherdental">Website</a>
  </div>
</div>
<div role="main" aria-label="Clinic A">
  <a data-item-id="authority" href="https://clinica.example.com/">clinica.example.com</a>
</div>
<div role="main" aria-label="Clinic B">
  <a data-item-id="authority" href="https://www.facebook.com/clinicb">facebook.com</a>
  <a href="https://www.instagram.com/clinicb/">Instagram</a>
</div>
"""


async def _links_for(name: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(MAPS_FIXTURE)
        try:
            return await _extract_links(_listing_panel(page, name))
        finally:
            await browser.close()


def test_links_from_other_listings_are_ignored():
    website, facebook, instagram = asyncio.run(_links_for("Clinic A"))
    assert website == "https://clinica.example.com/"
    assert facebook is None
    assert instagram is None


def test_listing_own_social_links_are_kept():
    website, facebook, instagram = asyncio.run(_links_for("Clinic B"))
    assert website is None
    assert facebook == "https://www.facebook.com/clinicb"
    assert instagram == "https://www.instagram.com/clinicb/"
