---
title: Smart Buyer AI API
emoji: 🧶
colorFrom: gray
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
short_description: Knowledge-based buyer detection API (FastAPI)
---

# Smart Buyer AI: backend API

FastAPI service for **Smart Buyer AI: A Knowledge Base Intelligent Potential Customer
Detection System**. It searches the web for companies that may buy raw sheep wool, duck
down or cashmere, reads their own websites, extracts source-grounded facts and qualifies
each company with product-specific knowledge-base rules.

The block at the top of this file is the configuration Hugging Face Spaces reads when this
folder is used as a Docker Space. The full project README is in the repository root.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Health check |
| `POST /api/v2/search` | Start a search job (`product`, `country`, `mode`: `live` / `seed` / `replay`) |
| `GET /api/v2/search/{job_id}` | Job status and result |
| `GET /api/v2/knowledge/{product}` | Knowledge base and rules |
| `GET /api/v2/snapshots` | Saved searches that can be replayed |

Interactive docs: `/docs`.
