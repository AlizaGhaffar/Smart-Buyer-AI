# Spec 03: Knowledge-Based Lead Qualification (supersedes the scoring in Spec 01)

## Goal
Replace the OR-based keyword score (`+25 buyer term`, `+25 product term`) with an
explainable pipeline that qualifies companies from evidence on their own websites.

## Requirements
1. **Product knowledge bases** (`backend/app/knowledge/products/`): definition, aliases,
   materials by role (target / related / ambiguous / alternative / distractor), business
   activities (core / adjacent / non-buyer), applications, buyer categories, required
   evidence, positive and negative rules, search queries.
2. **Facts:** `Fact(predicate, object, polarity, attrs, evidence)`. Evidence = URL, verbatim
   quote, page type, retrieval time, extractor. A fact without evidence cannot exist.
3. **Three separate evidence layers:** relevance (none/weak/moderate/strong), material
   usage (none/mentioned/supported/contradicted), purchasing (none/direct/contradicted).
4. **Reasoning:** forward chaining to a fixpoint. Derived roles (retailer, supplier),
   vetoes, caps, conflicts, near misses and missing information are all reported.
   Unreadable (non-English) text is never treated as evidence of an unrelated business.
5. **Qualification decision table** (first match wins): insufficient text -> Insufficient;
   veto -> Not Relevant; direct purchase + supported usage -> Confirmed Purchaser;
   strong relevance + supported usage -> Strong; conflict -> Insufficient; partial ->
   Possible; relevant without material evidence -> Insufficient; else Not Relevant.
6. **Evidence score (0-100):** material usage 30, activity 20, buyer category 10, source
   reliability 10, completeness 10, purchasing 20; penalties for conflicts (-10) and mixed
   materials (-8); capped at 30 without material evidence. It ranks leads within a class
   and is labelled "not a probability".
7. **API:** `POST /api/v2/search` (job), `GET /api/v2/search/{id}`, `GET /api/v2/knowledge/{product}`.
8. **Evaluation:** a labelled dataset with dev/test split; compare against the original
   keyword baseline on precision, recall, F1, false-positive rate, evidence coverage and
   5-class accuracy.
