"""Benchmark of the lead pipeline stages, run against live services.

Usage, from the repo root with services/fast-scan/requirements.txt installed:

    python benchmarks/run_benchmark.py "dental clinic Quezon City" --leads 20

Writes one JSON record per lead to benchmarks/<date>-lead-run.jsonl and prints
a summary. Records hold no names, phone numbers, addresses, emails or page
content; each business is identified by a short hash of its Maps place id.

A preflight step checks every external service first. Stages whose service is
unavailable are recorded as blocked instead of being run. The LLM stages
(chain filter, Facebook/Instagram footprint, qualitative audit, website vision
scoring, lead scoring) are not run by this script yet: none of their providers
were reachable when it was written, so no code for them could be checked.
"""
import argparse
import asyncio
import hashlib
import json
import os
import platform
import re
import statistics
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "fast-scan" / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import httpx
from importlib.metadata import version
from playwright.async_api import async_playwright

from services.scrapper import scrape_google_maps
from services.web_scraper.core.analyzer import run_audit
from services.web_scraper.core.browser_manager import BrowserManager
from services.web_scraper.models import ScrapeRequest

BATCH_SIZE = 5  # the n8n workflow asks /scan-maps for 5 leads per call
EVALUATOR_MODEL = "llama-3.3-70b-versatile"  # core/config.py GROQ_MODEL
GEMINI_MODEL = "gemini-2.5-flash"  # core/config.py GEMINI_MODEL


def lead_hash(place_id: str, name: str) -> str:
    return hashlib.sha256((place_id or name).encode()).hexdigest()[:12]


def norm_url(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url.strip())
    return (parts.netloc.lower().removeprefix("www.").removeprefix("m.") + parts.path.rstrip("/")).lower()


def workflow_models() -> dict:
    nodes = json.loads((ROOT / "n8n-workflow.json").read_text(encoding="utf-8"))["nodes"]
    body = {n["name"]: n["parameters"].get("jsonBody", "") for n in nodes}
    model = lambda node: re.search(r'"model":\s*"([^"]+)"', body[node]).group(1)
    return {
        "chain_filter": model("AI Evaluator - Groq Llama 3"),
        "website_vision": model("Groq Vision Analysis1"),
    }


def preflight() -> dict:
    """Check each external service without spending tokens. Never records key values."""
    status = {}

    groq_key = os.getenv("GROQ_API_KEY")
    models = {**workflow_models(), "lead_scoring": EVALUATOR_MODEL, "qualitative_fallback": EVALUATOR_MODEL}
    if not groq_key:
        status.update({f"groq:{stage}": "key missing" for stage in models})
    else:
        try:
            r = httpx.get("https://api.groq.com/openai/v1/models",
                          headers={"Authorization": f"Bearer {groq_key}"}, timeout=30)
            served = {m["id"] for m in r.json().get("data", [])} if r.status_code == 200 else set()
            for stage, model in models.items():
                if r.status_code != 200:
                    status[f"groq:{stage}"] = f"key rejected (HTTP {r.status_code})"
                else:
                    status[f"groq:{stage}"] = "ok" if model in served else f"model {model} not served for this key"
        except httpx.HTTPError as e:
            status.update({f"groq:{stage}": f"unreachable ({type(e).__name__})" for stage in models})

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        status["gemini:qualitative"] = "key missing"
    else:
        try:
            r = httpx.get(f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}",
                          headers={"x-goog-api-key": gemini_key}, timeout=30)
            reason = ""
            if r.status_code != 200:
                details = r.json().get("error", {}).get("details", [{}])
                reason = ", " + details[0].get("reason", "") if details else ""
            status["gemini:qualitative"] = "ok" if r.status_code == 200 else f"key rejected (HTTP {r.status_code}{reason})"
        except httpx.HTTPError as e:
            status["gemini:qualitative"] = f"unreachable ({type(e).__name__})"

    supabase_url, supabase_key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        status["supabase:rag_and_dedupe"] = "key missing"
    else:
        try:
            r = httpx.get(f"{supabase_url}/rest/v1/", headers={"apikey": supabase_key}, timeout=30)
            status["supabase:rag_and_dedupe"] = "ok" if r.status_code < 400 else f"rejected (HTTP {r.status_code})"
        except httpx.ConnectError:
            status["supabase:rag_and_dedupe"] = "unreachable (project host does not resolve or refuses connections)"
        except httpx.HTTPError as e:
            status["supabase:rag_and_dedupe"] = f"unreachable ({type(e).__name__})"

    apify_key = os.getenv("APIFY_TOKEN") or os.getenv("APIFY_API_TOKEN")
    status["apify:facebook_instagram"] = "key present" if apify_key else "key missing (the token lives only in n8n credentials)"
    return status


async def scrape(target: str, leads: int) -> list[dict]:
    rows, seen = [], set()
    for batch, offset in enumerate(range(0, leads, BATCH_SIZE)):
        started = time.perf_counter()
        results = await scrape_google_maps(target, BATCH_SIZE, offset)
        wall = time.perf_counter() - started
        print(f"batch {batch}: {len(results)} leads in {wall:.1f}s")
        for lead in results:
            key = lead.place_id or lead.name
            if key in seen:
                continue
            seen.add(key)
            rows.append({"lead": lead, "batch": batch, "batch_wall_s": wall, "batch_size": len(results)})
    return rows


async def listing_facebook_links(rows: list[dict]) -> str:
    """Ground truth: open each listing on its own page (no results feed) and collect its Facebook links."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        for row in rows:
            lead = row["lead"]
            row["truth"] = None
            if not lead.place_id:
                continue
            try:
                await page.goto("https://www.google.com/maps/search/?api=1"
                                f"&query={quote(lead.name)}&query_place_id={quote(lead.place_id)}")
                await page.get_by_role("main", name=lead.name, exact=True).first.wait_for(timeout=15000)
                await page.wait_for_timeout(2000)
                if await page.locator('div[role="feed"]').count() > 0:
                    continue  # landed on a result list, so page-wide links are not this listing's
                hrefs = await page.locator('a[href^="http"]').evaluate_all("els => els.map(e => e.href)")
                row["truth"] = {norm_url(h) for h in hrefs if "facebook.com" in h.lower()}
            except Exception as e:
                print(f"listing check failed for {lead_hash(lead.place_id, lead.name)}: {type(e).__name__}")
        chromium = browser.version
        await browser.close()
    return chromium


async def capture_websites(rows: list[dict]) -> None:
    manager = BrowserManager()
    await manager.start()
    try:
        for row in rows:
            row["website_capture"] = None
            if not row["lead"].website:
                continue
            context = await manager.acquire_context()
            started = time.perf_counter()
            try:
                result = await run_audit(context, ScrapeRequest(url=row["lead"].website).url)
                shots = sum(1 for v in (result.get("screenshots") or {}).values() if v)
                row["website_capture"] = {"status": result["status"],
                                          "wall_s": round(time.perf_counter() - started, 2),
                                          "screenshots": shots}
            except Exception as e:
                row["website_capture"] = {"status": f"error ({type(e).__name__})",
                                          "wall_s": round(time.perf_counter() - started, 2),
                                          "screenshots": 0}
            finally:
                await context.close()
                manager.release_context()
    finally:
        await manager.stop()


def stat(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    return {"n": len(values), "mean": round(statistics.mean(values), 2),
            "median": round(statistics.median(values), 2),
            "min": round(min(values), 2), "max": round(max(values), 2)}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("--leads", type=int, default=20)
    parser.add_argument("--out", default=str(ROOT / "benchmarks" / f"{date.today():%Y-%m}-lead-run.jsonl"))
    args = parser.parse_args()

    services = preflight()
    blocked = sorted(k for k, v in services.items() if v not in ("ok", "key present"))
    print(json.dumps(services, indent=2))

    run_started = time.perf_counter()
    rows = await scrape(args.target, args.leads)
    scrape_done = time.perf_counter()
    chromium = await listing_facebook_links(rows)
    check_done = time.perf_counter()
    await capture_websites(rows)
    capture_done = time.perf_counter()

    fb_counts: dict[str, int] = {}
    for row in rows:
        fb = norm_url(row["lead"].facebook_url)
        if fb:
            fb_counts[fb] = fb_counts.get(fb, 0) + 1

    records = []
    for row in rows:
        lead, truth = row["lead"], row["truth"]
        fb = norm_url(lead.facebook_url)
        matches = None if truth is None else (fb in truth if fb else not truth)
        records.append({
            "lead": lead_hash(lead.place_id, lead.name),
            "batch": row["batch"],
            "scrape_s": round(row["batch_wall_s"] / row["batch_size"], 2),
            "has_website": bool(lead.website),
            "has_facebook_url": bool(fb),
            "has_instagram_url": bool(lead.instagram_url),
            "facebook_url_distinct": None if not fb else fb_counts[fb] == 1,
            "facebook_url_matches_listing": matches,
            "website_capture": row["website_capture"],
            "llm_calls": 0,
            "llm_tokens": 0,
            "stages_blocked": blocked,
        })

    Path(args.out).write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")

    checked = [r for r in records if r["facebook_url_matches_listing"] is not None]
    with_fb = [r for r in records if r["has_facebook_url"]]
    captures = [r["website_capture"] for r in records if r["website_capture"]]
    summary = {
        "date": date.today().isoformat(),
        "target": args.target,
        "leads": len(records),
        "batches": len({r["batch"] for r in records}),
        "scrape_total_s": round(scrape_done - run_started, 2),
        "scrape_per_lead_s": round((scrape_done - run_started) / max(len(records), 1), 2),
        "scrape_per_lead_by_batch_s": stat([r["scrape_s"] for r in records]),
        "leads_with_facebook_url": len(with_fb),
        "facebook_urls_distinct": sum(1 for r in with_fb if r["facebook_url_distinct"]),
        "listings_checked": len(checked),
        "listings_matching": sum(1 for r in checked if r["facebook_url_matches_listing"]),
        "listing_check_total_s": round(check_done - scrape_done, 2),
        "websites": sum(1 for r in records if r["has_website"]),
        "website_capture_success": sum(1 for c in captures if c["status"] == "success"),
        "website_capture_status": {s: sum(1 for c in captures if c["status"] == s) for s in {c["status"] for c in captures}},
        "website_capture_s": stat([c["wall_s"] for c in captures]),
        "website_capture_total_s": round(capture_done - check_done, 2),
        "services": services,
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "playwright": version("playwright"),
            "chromium": chromium,
        },
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
