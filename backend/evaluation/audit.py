"""Automatic audit of every saved live run (no labels needed).

    python -m evaluation.audit   -> evaluation/AUDIT.md

Checks the guarantees the system claims:
  1. No invented evidence: every quote is a verbatim substring of a fetched page.
  2. No evidence from search snippets, directories or third-party pages.
  3. Every qualified lead has at least one fired positive rule backed by a material quote.
  4. Every 'Confirmed Purchaser' has a sourcing/buying fact with a quote.
  5. Every 'Not Relevant' lead names the rule (veto) or reason that rejected it.
  6. Every 'Insufficient Evidence' lead has a stated reason.
  7. Every contact's source URL is one of the pages that was checked.
  8. Missing evidence is never treated as positive: no qualified lead has usage 'none'.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.knowledge.schema import NON_OFFICIAL_PAGE_TYPES
from app.pipeline.runner import PipelineRequest, run_pipeline
from app.reasoning.qualification import CONFIRMED, INSUFFICIENT, NOT_RELEVANT, POSITIVE_CLASSES

OUT = Path(__file__).with_name("AUDIT.md")
SNAPSHOT_DIR = Path(__file__).parent / "snapshots"  # frozen evaluation runs


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def audit(snapshot_dir: Path = SNAPSHOT_DIR) -> tuple[str, list[str]]:
    failures: list[str] = []
    counts = Counter()
    rules = Counter()
    classes = Counter()
    for path in sorted(snapshot_dir.glob("*.json")):
        snap = json.loads(path.read_text(encoding="utf-8"))
        pages = {p["url"]: _norm(p["text"]) for c in snap["companies"] for p in c["pages"]}
        result = run_pipeline(PipelineRequest(snap["product"], snap["country"], mode="replay"), snapshot_dir=snapshot_dir)
        for lead in result["leads"]:
            who = f"{path.stem}/{lead['company_key']}"
            classes[lead["classification"]] += 1
            counts["leads"] += 1
            for r in lead["trace"]["rules_fired"]:
                rules[r["id"]] += 1
            for fact in lead["facts"]:
                for ev in fact["evidence"]:
                    counts["quotes"] += 1
                    if ev["url"] not in pages or _norm(ev["quote"]) not in pages[ev["url"]]:
                        failures.append(f"{who}: quote not found on its page: {ev['quote'][:80]!r}")
                    if ev["page_type"] in NON_OFFICIAL_PAGE_TYPES:
                        failures.append(f"{who}: evidence from a non-official page ({ev['page_type']})")
            counts["rejected_facts"] += len(lead["rejected_facts"])
            fact_by_id = {f["id"]: f for f in lead["facts"]}
            cls = lead["classification"]
            if cls in POSITIVE_CLASSES:
                vetoes = {v["id"] for v in lead["trace"]["vetoes"]}
                backed = any(
                    r["id"] not in vetoes and any(fact_by_id.get(e["fact"], {}).get("predicate") == "uses_material"
                                                  for e in r["evidence"])
                    for r in lead["trace"]["rules_fired"]
                )
                if not backed:
                    failures.append(f"{who}: qualified ({cls}) without a material-backed positive rule")
                if lead["layers"]["usage"] == "none":
                    failures.append(f"{who}: qualified although material usage is 'none'")
            if cls == CONFIRMED and not any(f["predicate"] == "sources" and f["evidence"] for f in lead["facts"]):
                failures.append(f"{who}: Confirmed Purchaser without a sourcing fact")
            if cls == NOT_RELEVANT and not (lead["trace"]["vetoes"] or lead["reason_code"] == "LOW_RELEVANCE"):
                failures.append(f"{who}: rejected without a veto rule or reason")
            if cls == INSUFFICIENT and not (lead["trace"]["insufficiency_reasons"] or lead["reason_code"] in {"CONFLICT", "MISSING_MATERIAL"}):
                failures.append(f"{who}: insufficient without a reason")
            checked = {p["url"] for p in lead["pages_checked"]}
            for contact in lead["contacts"]["emails"] + lead["contacts"]["phones"]:
                counts["contacts"] += 1
                if contact["source_url"] not in checked:
                    failures.append(f"{who}: contact {contact['value']} has a source outside the checked pages")

    lines = ["# Automatic audit of live runs", "",
             f"{counts['leads']} companies from {len(list(snapshot_dir.glob('*.json')))} saved live searches, "
             f"{counts['quotes']} evidence quotes, {counts['contacts']} contacts.", "",
             f"**Result: {'PASS' if not failures else f'{len(failures)} problem(s)'}**", "",
             "| Check | Result |", "|---|---|"]
    checks = [
        ("Every quote is verbatim text from a fetched company page", "quote not found"),
        ("No evidence from snippets / directories / third-party pages", "non-official"),
        ("Every qualified lead has a rule backed by a material quote", "material-backed"),
        ("No qualified lead with material usage 'none'", "usage is 'none'"),
        ("Every Confirmed Purchaser has a sourcing fact", "sourcing fact"),
        ("Every Not Relevant lead names its veto rule / reason", "without a veto"),
        ("Every Insufficient lead states why", "insufficient without"),
        ("Every contact's source is a checked page", "contact"),
    ]
    for title, needle in checks:
        n = sum(needle in f for f in failures)
        lines.append(f"| {title} | {'pass' if n == 0 else f'FAIL ({n})'} |")
    lines += ["", f"Facts dropped by the grounding check before reasoning: {counts['rejected_facts']}.", "",
              "## Classes", "", "| Class | Companies |", "|---|---|"]
    lines += [f"| {c} | {n} |" for c, n in classes.most_common()]
    lines += ["", "## Rules that fired (shows the KRR rules actually run)", "", "| Rule | Times fired |", "|---|---|"]
    lines += [f"| {r} | {n} |" for r, n in sorted(rules.items())]
    if failures:
        lines += ["", "## Problems", ""] + [f"- {f}" for f in failures]
    report = "\n".join(lines) + "\n"
    OUT.write_text(report, encoding="utf-8")
    return report, failures


if __name__ == "__main__":
    print(audit()[0])
