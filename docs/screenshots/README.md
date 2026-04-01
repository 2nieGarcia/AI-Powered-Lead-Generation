# Pipeline Screenshots

This directory contains screenshots demonstrating each stage of the n8n workflow pipeline.

## File Structure

```
docs/screenshots/
├── 01-entry-point.png          # Telegram webhook and message routing
├── 02-command-routing.png       # Command parsing (/scrape, /review, /start)
├── 03-lead-scraping.png         # FastAPI scraper with pagination
├── 04-ai-evaluation.png         # Groq LLM classification (Valid/Corporate)
├── 05-batch-controller.png      # Lead count validation & flow control
├── 06-footprint-and-storage.png # Digital audit + Supabase persistence (combined)
├── 07-human-review-loop.png     # Interactive Telegram approval interface
└── README.md                    # This file
```

## Screenshot Guidelines

- **Zoom Level**: Focus on the specific stage nodes, not the entire workflow
- **Annotations**: Add colored boxes or arrows to highlight key components
- **Quality**: High resolution PNG format (1920x1080 recommended)
- **Naming**: Use the exact filenames above for automatic README linking

## Stage Descriptions

| Stage                        | Focus Areas                                        | Key Nodes                                              |
| ---------------------------- | -------------------------------------------------- | ------------------------------------------------------ |
| **01-entry-point**           | Telegram Trigger, Message/Callback Router          | `Telegram Trigger`, `Call_back or Message`             |
| **02-command-routing**       | Command switch, Target validation                  | `Commands`, `Target exist?`, `Original Prompts`        |
| **03-lead-scraping**         | Scraper API, Duplicate filtering, Pagination       | `Scraper API`, `Supabase DB Check`, `Scrape new batch` |
| **04-ai-evaluation**         | Groq LLM call, JSON parsing, Valid/Corporate split | `AI Evaluator - Groq Llama 3`, `Valid or Corporate?`   |
| **05-batch-controller**      | Count validation, Flow control tool                | `Count 'duplicate'`, `More than 5?`, batch flow logic  |
| **06-footprint-and-storage** | FB/IG/Website audit + Database saves               | Apify scrapers, Website audit, `save as 'new' in db`   |
| **07-human-review-loop**     | Telegram interface, Approval buttons               | `New Lead`, `Which callback?`, approval workflow       |
