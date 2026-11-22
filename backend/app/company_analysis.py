"""One company, one product: extraction -> grounding -> reasoning -> qualification -> score."""

from __future__ import annotations

from dataclasses import dataclass, field

from .extraction.grounding import ground_facts
from .extraction.nlp_extractor import NLPExtractor, PageText
from .knowledge.schema import ProductKB
from .reasoning.engine import CompanyFacts, InferenceResult, infer
from .reasoning.qualification import Qualification, qualify
from .reasoning.scoring import score


@dataclass
class CompanyAnalysis:
    data: CompanyFacts
    inference: InferenceResult
    qualification: Qualification
    score: dict | None
    rejected_facts: list[dict] = field(default_factory=list)


def analyze_company(kb: ProductKB, company_key: str, pages: list[PageText], extractor=None,
                    company_name: str | None = None) -> CompanyAnalysis:
    extractor = extractor or NLPExtractor(kb)
    data = extractor.extract(company_key, pages, company_name=company_name)
    data.facts, rejected = ground_facts(data.facts, pages)
    inference = infer(kb, data)
    qualification = qualify(kb, inference)
    return CompanyAnalysis(data, inference, qualification, score(kb, data, inference, qualification), rejected)
