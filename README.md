# Smart Buyer AI

**Smart Buyer AI: A Knowledge Base Intelligent Potential Customer Detection System**

Smart Buyer AI finds international companies that may need one of three export raw
materials: **Raw Sheep Wool**, **Duck Down** and **Cashmere**. For every company it
shows *why* the company was or was not selected: the quotes from its own website,
the knowledge-base rules that fired, what evidence is missing, and an explainable
evidence score.

## How it works

```
Product + country
  -> 1. Product-specific web search      (ddgs metasearch, retry/backoff, cache)
  -> 2. Candidate collection             (URL normalisation, de-duplication,
                                          directory / marketplace / news blocklist)
  -> 3. Website verification            (homepage + About/Products/Contact/Sourcing pages,
                                          robots.txt, 1 request/s per site, SSRF-safe)
  -> 4. AI/NLP extraction                (facts with a verbatim quote + source URL;
                                          negation, buy/sell direction, exclusivity)
  -> 5. Grounding check                  (a fact whose quote is not on the page is dropped)
  -> 6. KRR reasoning                    (forward chaining over product-specific rules,
                                          derived roles, vetoes, caps, conflicts)
  -> 7. Qualification + evidence score   (decision table -> 5 classes; score 0-100,
                                          not a probability)
  -> Dashboard + CSV export
```

Classes:

| Class | Meaning |
|---|---|
| Confirmed Purchaser | The company's own site states that it buys or sources the raw material (self-declared, not a verified transaction). |
| Strong Potential Buyer | A relevant activity and use of the exact material are both supported by the company's site. |
| Possible Potential Buyer | A relevant business, but use of the exact material is only partly evidenced. |
| Insufficient Evidence | The site was unreachable, not in English, too thin, or contradictory. |
| Not Relevant | Rejected by a negative rule (unrelated business, retailer/brand, supplier, alternative material). |

Search snippets are only used to find candidates; they are never used as evidence.

## Project structure

```
backend/app/
  knowledge/        schema.py (entities, facts, rule language), generic_rules.py,
                    products/{sheep_wool,duck_down,cashmere}.py  - one KB per product
  extraction/       nlp_extractor.py (offline NLP), grounding.py
  reasoning/        engine.py (forward chaining), qualification.py, scoring.py
  pipeline/         search_service.py, candidates.py, website.py, contacts.py, runner.py
  company_analysis.py, jobs.py, main.py
  finder.py         original keyword finder (legacy /api/search and evaluation baseline)
backend/evaluation/ dataset.py (48 labelled cases), run_eval.py, RESULTS.md
backend/tests/      pytest suite
frontend/           Next.js dashboard (app/, components/, lib/)
```

## Run the backend

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`.

| Endpoint | Purpose |
|---|---|
| `POST /api/v2/search` | Start a search job: `{"product": "duck_down", "country": "Japan", "mode": "live"}`. `mode` is `live`, `seed` (with `seed_urls`) or `replay`. Returns `202` and a `job_id`. |
| `GET /api/v2/search/{job_id}` | Job status, stage, progress and (when done) the full result. |
| `GET /api/v2/knowledge/{product}` | The product's knowledge base, relations and rules. |
| `GET /api/v2/products` | The three supported products. |
| `POST /api/search` | Legacy keyword finder (kept for comparison only). |

**Replay mode.** Every live or seed run saves the fetched page text to
`backend/data/snapshots/`. Replay re-analyses that saved data without internet access,
for example for a demo. The response and the dashboard clearly mark it as a replay.

## Run the frontend

```powershell
cd frontend
npm install
npm run dev
```

`frontend/.env` sets `BACKEND_API_URL` (default `http://127.0.0.1:8000`). Open
`http://localhost:3000`.

## Tests and evaluation

```powershell
cd backend
python -m pytest -q                 # unit, pipeline and API tests (offline)
python -m evaluation.run_eval       # baseline vs. KRR metrics -> evaluation/RESULTS.md
cd ..\frontend
npm run typecheck
npm run build
```

The evaluation dataset contains 48 hand-written fictional companies (16 per product),
split into a development set and a held-out test set. The results show the rule logic
works as designed; they are **not** a measurement of real-world accuracy. See
`backend/evaluation/RESULTS.md`.

## Known limitations

- Extraction is English-only. Sites mostly in another language are marked Insufficient
  Evidence (the crawler does look for an English version first).
- The offline extractor uses patterns, not full language understanding. For example,
  "made by partner workshops" can be mistaken for the company's own manufacturing.
- Sites whose SSL certificate cannot be verified are not fetched.
- The free search provider can return empty results while it is throttling. Searches
  are retried; seed URLs and replay mode are available as fallbacks.
