# Constitution: Smart Buyer AI

*A Knowledge Base Intelligent Potential Customer Detection System*

## Principles
- **Spec-driven:** Every feature has a spec in `specs/`. The spec is the single source of truth.
- **Evidence before claims:** Every qualification must trace back to a verbatim quote and
  the URL of the company's own website. Search snippets, directories and news pages are
  never evidence. Nothing is invented: a missing email or phone is shown as "Not found".
- **Knowledge-based reasoning:** Each product (Raw Sheep Wool, Duck Down, Cashmere) has its
  own knowledge base and rules. Decisions come from explicit rules with an inference trace,
  not from keyword counts.
- **Honest labels:** A potential buyer is not a confirmed purchaser. "Confirmed Purchaser"
  needs a direct buying or sourcing statement on the company's own site. The evidence score
  is not a probability.
- **Free by default:** Works with free search (`ddgs`), HTTP fetching and offline NLP. Any
  LLM integration must be optional, extract-only, and pass the same grounding check.
- **Responsible crawling:** Respect robots.txt, rate-limit each site, fetch public hosts only.
- **Measured reliability:** Reliability claims must be supported by the labelled evaluation
  set (with a held-out test split), never by successful searches alone.

## Constraints
- **Stack:** Python (FastAPI), BeautifulSoup, `ddgs`, Next.js (App Router), Tailwind CSS,
  Framer Motion.
- **Scope:** Only Raw Sheep Wool, Duck Down and Cashmere.
