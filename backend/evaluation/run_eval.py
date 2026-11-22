"""Evaluate the old keyword baseline vs. the KRR system on the labelled dataset.

Run from backend/:   python -m evaluation.run_eval            (prints + writes RESULTS.md)
                     python -m evaluation.run_eval --details  (per-case table)
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

from app.company_analysis import analyze_company
from app.extraction.nlp_extractor import PageText
from app.finder import score_lead
from app.knowledge.products import get_kb
from app.reasoning.qualification import POSITIVE_CLASSES

from .dataset import CASES, PRODUCT_NAMES

CLASSES = [
    "confirmed_purchaser",
    "strong_potential_buyer",
    "possible_potential_buyer",
    "insufficient_evidence",
    "not_relevant",
]


def baseline_positive(case) -> bool:
    """The original finder.py rule: lead if score_lead(...) > 0 (product OR buyer term)."""
    text = " ".join([case["title"], case["snippet"], *(t for _, _, t in case["pages"])])
    score, _ = score_lead(PRODUCT_NAMES[case["product"]], text)
    return score > 0


def system_result(case):
    kb = get_kb(case["product"])
    pages = [PageText(url, ptype, text) for url, ptype, text in case["pages"]]
    # the live pipeline passes the name from the page title; do the same here
    name = re.split(r"\s+[|–—-]\s+", case["title"], maxsplit=1)[0].strip()
    return analyze_company(kb, case["id"], pages, company_name=name or None)


def has_grounded_usage_evidence(analysis) -> bool:
    used = {f.id: f for f in analysis.data.facts}
    for fired in analysis.inference.fired:
        if fired.kind == "positive" and fired.effect.get("usage"):
            if all(e["url"] and e["quote"] for e in fired.evidence) and fired.evidence:
                return any(used.get(e["fact"]) and used[e["fact"]].predicate == "uses_material"
                           for e in fired.evidence)
    return False


def binary_metrics(pairs):
    """pairs: list of (truth_positive, predicted_positive)."""
    tp = sum(t and p for t, p in pairs)
    fp = sum((not t) and p for t, p in pairs)
    fn = sum(t and (not p) for t, p in pairs)
    tn = sum((not t) and (not p) for t, p in pairs)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision,
            "recall": recall, "f1": f1, "fpr": fpr, "n": len(pairs)}


def evaluate(cases=CASES):
    rows = []
    for case in cases:
        analysis = system_result(case)
        predicted = analysis.qualification.classification
        rows.append({
            "case": case,
            "truth": case["expected"],
            "truth_pos": case["expected"] in POSITIVE_CLASSES,
            "baseline_pos": baseline_positive(case),
            "system": predicted,
            "system_pos": predicted in POSITIVE_CLASSES,
            "evidence": has_grounded_usage_evidence(analysis),
            "analysis": analysis,
        })
    return rows


def summarise(rows):
    out = {}
    for label, subset in (("all", rows), ("dev", [r for r in rows if r["case"]["split"] == "dev"]),
                          ("test", [r for r in rows if r["case"]["split"] == "test"])):
        base = binary_metrics([(r["truth_pos"], r["baseline_pos"]) for r in subset])
        system = binary_metrics([(r["truth_pos"], r["system_pos"]) for r in subset])
        positives = [r for r in subset if r["system_pos"]]
        system["evidence_coverage"] = (
            sum(r["evidence"] for r in positives) / len(positives) if positives else 0.0
        )
        base["evidence_coverage"] = 0.0  # the baseline returns no supporting quotes at all
        system["accuracy_5class"] = sum(r["system"] == r["truth"] for r in subset) / len(subset)
        out[label] = {"baseline": base, "system": system, "n": len(subset)}
    out["confusion"] = Counter((r["truth"], r["system"]) for r in rows)
    out["per_product"] = {
        p: binary_metrics([(r["truth_pos"], r["system_pos"]) for r in rows if r["case"]["product"] == p])
        for p in PRODUCT_NAMES
    }
    return out


def render(rows, summary, details=False) -> str:
    pct = lambda v: f"{v * 100:.0f}%"
    lines = ["# Evaluation results", "",
             f"Dataset: {len(rows)} hand-labelled fictional companies "
             f"(dev {summary['dev']['n']}, held-out test {summary['test']['n']}).", "",
             "Positive = Confirmed / Strong / Possible. Baseline = original finder.py "
             "`score_lead() > 0` rule on the same text.", ""]
    for split in ("all", "dev", "test"):
        b, s = summary[split]["baseline"], summary[split]["system"]
        lines += [f"## {split} (n={summary[split]['n']})", "",
                  "| Metric | Old keyword baseline | KRR system |", "|---|---|---|",
                  f"| Precision | {pct(b['precision'])} | {pct(s['precision'])} |",
                  f"| Recall | {pct(b['recall'])} | {pct(s['recall'])} |",
                  f"| F1 | {pct(b['f1'])} | {pct(s['f1'])} |",
                  f"| False-positive rate | {pct(b['fpr'])} ({b['fp']}/{b['fp'] + b['tn']}) | "
                  f"{pct(s['fpr'])} ({s['fp']}/{s['fp'] + s['tn']}) |",
                  f"| Evidence coverage of positives | n/a (no quotes) | {pct(s['evidence_coverage'])} |",
                  f"| 5-class accuracy | n/a (no classes) | {pct(s['accuracy_5class'])} |", ""]
    lines += ["## Per product (KRR system, all cases)", "", "| Product | Precision | Recall | FPR |", "|---|---|---|---|"]
    for p, m in summary["per_product"].items():
        lines.append(f"| {PRODUCT_NAMES[p]} | {pct(m['precision'])} | {pct(m['recall'])} | {pct(m['fpr'])} |")
    lines += ["", "## Confusion matrix (rows = manual label, columns = system)", "",
              "| label \\ system | " + " | ".join(c.split("_")[0] for c in CLASSES) + " |",
              "|---" * (len(CLASSES) + 1) + "|"]
    for t in CLASSES:
        lines.append(f"| {t} | " + " | ".join(str(summary['confusion'][(t, s)]) for s in CLASSES) + " |")
    errors = [r for r in rows if r["system"] != r["truth"]]
    lines += ["", f"## Misclassified cases ({len(errors)})", "",
              "| Case | Split | Note | Label | System | Rules fired |", "|---|---|---|---|---|---|"]
    for r in errors:
        fired = ", ".join(r["analysis"].inference.fired_ids) or "-"
        lines.append(f"| {r['case']['id']} | {r['case']['split']} | {r['case']['note']} | "
                     f"{r['truth']} | {r['system']} | {fired} |")
    if details:
        lines += ["", "## All cases", "", "| Case | Label | Baseline | System | Score |", "|---|---|---|---|---|"]
        for r in rows:
            s = r["analysis"].score
            lines.append(f"| {r['case']['id']} | {r['truth']} | {'lead' if r['baseline_pos'] else '-'} | "
                         f"{r['system']} | {s['value'] if s else '-'} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> None:
    argv = argv or sys.argv[1:]
    rows = evaluate()
    report = render(rows, summarise(rows), details="--details" in argv)
    Path(__file__).with_name("RESULTS.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
