---
title: AI-Powered Lead Generation Pipeline
tagline: A Telegram bot that finds local businesses on Google Maps, audits their online presence, and scores them as agency leads.
area: ml
stack: [n8n, FastAPI, Playwright, Groq, Supabase pgvector, Sentence-Transformers]
note: 2-person team
---

Finding leads for a small digital agency is slow, repetitive work. You search Google Maps, skip the chains and franchises, check whether each place has a decent Facebook page or website, and then guess whether they'd actually need you. We wanted a pipeline to do that grunt work so we only spend time on the leads worth pitching.

The whole thing runs from a Telegram bot. You send `/scrape` with a keyword, and an n8n workflow calls our FastAPI service, which scrapes Google Maps with Playwright and drops anything already in the database. New leads get a digital footprint audit across Facebook, Instagram and their website, then a large language model (LLM) on Groq scores them in one batched call.

The scoring uses retrieval-augmented generation (RAG). Each lead is embedded with Sentence-Transformers and matched in Supabase pgvector against past successful and blacklisted leads, so the model sees why similar businesses were accepted or rejected before it decides. Corporate chains go straight to the blacklist, and the good leads land in a Telegram review queue with Add and Discard buttons.

I handled the AI side and the architecture: the evaluation prompts, the RAG retrieval, the Gemini-to-Groq fallback with rate limiting for the audits, and how the n8n stages fit together. Charles Cabatian handled backend development and infrastructure.

It works end to end: one Telegram command takes a keyword to audited, scored leads waiting for a yes or no.
