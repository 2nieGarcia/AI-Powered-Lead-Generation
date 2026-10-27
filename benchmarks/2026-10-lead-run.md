# Lead run benchmark, October 2026

Run on 2026-10-27 with the query `dental clinic Quezon City`, 20 leads.
Per-lead records: [`2026-10-lead-run.jsonl`](./2026-10-lead-run.jsonl).
Script: [`run_benchmark.py`](./run_benchmark.py).

**This run is partial.** Only the stages that need no API key could run.
Every LLM stage, the Facebook/Instagram footprint and the Supabase RAG lookup
were blocked by the services listed under [Blocked stages](#blocked-stages).
No LLM call was made, so there are no token, fallback or cost numbers.

## Summary

| Stage | Result |
| --- | --- |
| Google Maps scrape | 20 leads in 4 batches of 5, 83.6 s total |
| Scrape time per lead | 4.18 s mean, 4.02 s median (3.72 s to 4.95 s) |
| Leads with a Facebook URL | 3 of 20 |
| Facebook URLs that are distinct | 3 of 3 |
| Facebook field matches the listing's own page | 20 of 20 checked (17 of them have no Facebook link on either side) |
| Leads with a website | 8 of 20 |
| Website capture (DOM signals + 3 screenshots) | 7 of 8 succeeded, 1 domain did not resolve |
| Website capture time per site | 5.05 s mean, 4.98 s median (2.04 s to 7.90 s) |
| Chain/franchise filter | blocked |
| Facebook/Instagram footprint (Apify) | blocked |
| Qualitative audit (Gemini, Groq fallback) | blocked |
| Website vision scoring | blocked |
| RAG lookup + lead scoring | blocked |
| LLM calls and tokens per lead | 0 (nothing could run) |
| Cost per lead | not measured |
| End-to-end time per lead | not measured |

## Method

1. **Preflight.** Each external service is checked without spending tokens:
   the Groq model list for the key, the Gemini model endpoint, the Supabase
   REST root, and whether an Apify token is set. A stage whose service fails
   is recorded as blocked and is not run.
2. **Scrape.** `scrape_google_maps(target, 5, offset)` is called for offsets
   0, 5, 10 and 15, as the n8n workflow does through `/scan-maps`. Each call
   starts its own browser. Scrape time per lead is the batch wall time divided
   by the leads it returned.
3. **Facebook URL check.** Each lead is reopened on its own Maps page
   (`maps/search/?api=1&query=<name>&query_place_id=<id>`), which has no
   results feed. Every Facebook link on that page is collected. A lead passes
   if its scraped `facebook_url` is one of those links, or if both are empty.
   "Distinct" means no other lead in the run has the same URL.
4. **Website capture.** For each lead with a website, `run_audit` runs through
   `BrowserManager`, as `/api/audit/website` does. This covers navigation, DOM
   signals and three screenshots. The vision scoring that follows it in n8n
   was blocked.

No row was written to or deleted from Supabase: the project host did not
resolve, and none of the stages that ran touch the database.

## Blocked stages

| Service | Stage | Status on 2026-10-27 |
| --- | --- | --- |
| Groq | chain filter (`llama-3.1-8b-instant`) | key valid, model not served for this key |
| Groq | website vision (`meta-llama/llama-4-scout-17b-16e-instruct`) | key valid, model not served for this key |
| Groq | lead scoring and qualitative fallback (`llama-3.3-70b-versatile`) | key valid, model not served for this key |
| Gemini | qualitative audit (`gemini-2.5-flash`) | key rejected (HTTP 400, `API_KEY_INVALID`) |
| Supabase | RAG lookup and duplicate check | project host does not resolve |
| Apify | Facebook and Instagram scrapers | no token in `.env`; it is stored only in n8n credentials |

## Environment

| | |
| --- | --- |
| OS | Windows 11 (10.0.26300) |
| Python | 3.12.5 |
| Playwright | 1.64.1 |
| Chromium | 156.0.8078.4, headless |

## Privacy

The records hold no names, phone numbers, addresses, emails or page content.
Each business is a 12-character prefix of the SHA-256 of its Maps place id.
Facebook URLs are stored only as true/false checks.
