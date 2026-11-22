"""Helpers for building facts/companies in tests."""

from itertools import count

from app.knowledge.schema import Evidence, Fact
from app.reasoning.engine import CompanyFacts

_ids = count(1)


def fact(predicate, obj, quote="Example statement.", page="about", polarity=True, **attrs):
    n = next(_ids)
    return Fact(
        id=f"F{n}",
        predicate=predicate,
        object=obj,
        polarity=polarity,
        attrs=attrs,
        evidence=(Evidence(url=f"https://example.test/{page}", quote=quote, page_type=page),),
    )


def company(*facts, pages=2, chars=2000, english=True, key="example.test"):
    return CompanyFacts(
        company_key=key,
        facts=list(facts),
        pages_fetched=pages,
        text_chars=chars,
        english=english,
    )
