"""Grounding check: a fact survives only if its evidence really exists.

Applied to every extractor (offline NLP and the optional LLM). An evidence
quote must be a verbatim substring (whitespace-normalised, case-insensitive)
of the text of a page that was actually fetched, at the same URL.
"""

from __future__ import annotations

import logging

from ..knowledge.schema import Fact

logger = logging.getLogger(__name__)


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def ground_facts(facts: list[Fact], pages) -> tuple[list[Fact], list[dict]]:
    texts = {p.url: _norm(p.text) for p in pages}
    kept: list[Fact] = []
    rejected: list[dict] = []
    for fact in facts:
        good = tuple(
            e for e in fact.evidence
            if e.url in texts and _norm(e.quote) and _norm(e.quote) in texts[e.url]
        )
        if good:
            fact.evidence = good
            kept.append(fact)
        else:
            reason = "evidence quote not found on any fetched page"
            logger.warning("Dropped ungrounded fact %s %s: %s", fact.predicate, fact.object, reason)
            rejected.append({"predicate": fact.predicate, "object": fact.object,
                             "quotes": fact.quotes, "reason": reason})
    return kept, rejected
