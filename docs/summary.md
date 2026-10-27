---
title: AI-Powered Lead Generation Pipeline
tagline: A Telegram bot that finds local businesses on Google Maps, audits their online presence, and scores them as agency leads.
area: ml
stack: [n8n, FastAPI, Playwright, Groq, Supabase pgvector, Sentence-Transformers]
note: Scores each lead out of 100 after a Facebook, Instagram and website audit
---

Finding leads for a small digital agency is slow, repetitive work. You search Google Maps, skip the chains and franchises, check whether each place has a decent Facebook page or website, then guess whether they'd need you. We wanted a pipeline to do that grunt work so we only pitch the good ones.

It all runs from a Telegram bot. You send `/scrape` with a keyword, and an n8n workflow calls our FastAPI service, which scrapes Google Maps with Playwright five results at a time and drops anything already in the database. One batched large language model (LLM) call on Groq tags the chains and franchises, which go straight to the blacklist. The rest get a digital footprint audit across Facebook, Instagram and their website.

The scoring uses retrieval-augmented generation (RAG). Each lead is embedded with Sentence-Transformers and matched in Supabase pgvector against past successful and blacklisted leads, so the model sees why similar businesses were accepted or rejected.

I handled the AI side and the architecture: the evaluation prompts, the RAG retrieval, the Gemini-to-Groq fallback with rate limiting for the audits, and how the n8n stages fit together. Charles Cabatian handled backend development and infrastructure.

One Telegram command turns a keyword into audited local leads, each scored out of 100 across website need, ability to pay, reachability and upsell potential, with a pitch angle and the services to offer. The good ones wait in a Telegram review queue with Add and Discard buttons. Next on my list: the scraper sometimes grabs the wrong Facebook link from the Maps page, so I'm tightening that before anything else.
