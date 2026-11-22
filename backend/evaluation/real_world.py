"""Real-world evaluation on companies found by live searches.

Step 1 - make a BLIND labelling sheet (the system's answer is not shown):
    python -m evaluation.real_world sheet
    -> evaluation/real_world/labelling_sheet.csv   (open in Excel, fill the `label` column)
    -> evaluation/real_world/system_outputs.json   (hidden answers, do not open while labelling)

Step 2 - after labelling, compare the system and the old keyword baseline with your labels:
    python -m evaluation.real_world score
    -> evaluation/REAL_WORLD_RESULTS.md

Labels: buyer | not_buyer | unsure   (y / n / ? are accepted too)

AI-assisted labelling (blind AI annotators + a human-verified random sample):
    python -m evaluation.real_world merge-ai      # ai_labels_*.csv -> ai_labels.csv
    python -m evaluation.real_world check-sheet   # 20 random rows -> human_check_sheet.csv
    python -m evaluation.label_tool check         # label those 20 rows yourself
    python -m evaluation.real_world agreement     # AI vs human agreement (Cohen's kappa)
    python -m evaluation.real_world score ai      # metrics using the AI labels
"""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

from app.finder import score_lead
from app.pipeline.runner import PipelineRequest, run_pipeline
from app.reasoning.qualification import POSITIVE_CLASSES

from .dataset import PRODUCT_NAMES
from .run_eval import binary_metrics

HERE = Path(__file__).parent / "real_world"
# Frozen copies of the live runs used for evaluation. The app writes its own
# runs to data/snapshots, so a new search can never overwrite labelled data.
SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
SHEET = HERE / "labelling_sheet.csv"
OUTPUTS = HERE / "system_outputs.json"
RESULTS = Path(__file__).parent / "REAL_WORLD_RESULTS.md"
PREFIX = {"raw_sheep_wool": "W", "duck_down": "D", "cashmere": "C"}
LABEL_ALIASES = {"buyer": "buyer", "y": "buyer", "yes": "buyer",
                 "not_buyer": "not_buyer", "n": "not_buyer", "no": "not_buyer", "not buyer": "not_buyer",
                 "unsure": "unsure", "?": "unsure", "u": "unsure"}


# The first labelled set (90 companies). Later snapshots belong to other sets.
ORIGINAL_SET = ("cashmere__any", "cashmere__italy", "duck_down__any", "duck_down__germany",
                "duck_down__japan", "raw_sheep_wool__any", "raw_sheep_wool__united-kingdom")
# Fresh validation set: new countries, searched after v2 was frozen (git tag v2-tuned).
FRESH_SET = ("raw_sheep_wool__italy", "duck_down__poland", "cashmere__united-kingdom", "duck_down__hungary")
FRESH = HERE / "fresh"


def collect(snapshot_dir: Path = SNAPSHOT_DIR, names=None, exclude=frozenset(), id_prefix: str = "") -> list[dict]:
    """Re-analyse saved live snapshots; one row per (product, company).

    names: snapshot file stems to use (None = every snapshot in the folder).
    exclude: (product, company_key) pairs to leave out, e.g. companies already labelled.
    """
    rows, seen = [], set(exclude)
    paths = sorted(snapshot_dir.glob("*.json"))
    if names is not None:
        paths = [p for p in paths if p.stem in names]
    for path in paths:
        snap = json.loads(path.read_text(encoding="utf-8"))
        texts = {c["candidate"]["key"]: " ".join(p["text"] for p in c["pages"]) for c in snap["companies"]}
        result = run_pipeline(PipelineRequest(snap["product"], snap["country"], mode="replay"), snapshot_dir=snapshot_dir)
        for lead in result["leads"]:
            key = (snap["product"], lead["company_key"])
            if key in seen:
                continue
            seen.add(key)
            baseline_text = " ".join([lead["found_via"]["title"], lead["found_via"]["snippet"], texts.get(lead["company_key"], "")])
            rows.append({
                "key": lead["company_key"],
                "product": snap["product"],
                "search_country": snap["country"] or "any",
                "company": lead["company_name"],
                "website": lead["official_website"] or f"https://{lead['company_key']}/ (not reachable)",
                "pages": [p["url"] for p in lead["pages_checked"]],
                "system": lead["classification"],
                "score": lead["score"]["value"] if lead["score"] else None,
                "rules": [r["id"] for r in lead["trace"]["rules_fired"]],
                "reason": lead["reason_code"],
                "baseline_positive": score_lead(PRODUCT_NAMES[snap["product"]], baseline_text)[0] > 0,
            })
    rows.sort(key=lambda r: (list(PREFIX).index(r["product"]), r["company"].casefold()))
    counters = {p: 0 for p in PREFIX}
    for r in rows:
        counters[r["product"]] += 1
        r["id"] = f"{id_prefix}{PREFIX[r['product']]}{counters[r['product']]:02d}"
    return rows


def make_sheet(snapshot_dir: Path = SNAPSHOT_DIR, names=None, sheet: Path | None = None,
               outputs: Path | None = None, exclude=frozenset(), id_prefix: str = "") -> None:
    sheet, outputs = sheet or SHEET, outputs or OUTPUTS
    rows = collect(snapshot_dir, names, exclude, id_prefix)
    sheet.parent.mkdir(parents=True, exist_ok=True)
    with sheet.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "product", "company", "website", "pages_the_system_read", "label", "notes"])
        for r in rows:
            writer.writerow([r["id"], PRODUCT_NAMES[r["product"]], r["company"], r["website"],
                             " ".join(r["pages"][:4]), "", ""])
    outputs.write_text(json.dumps({r["id"]: r for r in rows}, indent=1, ensure_ascii=False), encoding="utf-8")
    per = {PRODUCT_NAMES[p]: sum(r["product"] == p for r in rows) for p in PREFIX}
    print(f"Wrote {len(rows)} companies to {sheet}  ({per})")


def make_fresh_sheet(snapshot_dir: Path = SNAPSHOT_DIR) -> None:
    """Blind sheet for the fresh validation set, leaving out every already-labelled company."""
    seen = {(r["product"], r["key"]) for r in collect(snapshot_dir, ORIGINAL_SET)}
    make_sheet(snapshot_dir, FRESH_SET, FRESH / "labelling_sheet.csv", FRESH / "system_outputs.json",
               exclude=seen, id_prefix="F")


def _read_labels(path: Path) -> dict[str, dict]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;\t")  # Excel may save with ';'
    labels = {}
    for row in csv.DictReader(io.StringIO(text), dialect=dialect):
        value = (row.get("label") or "").strip().lower()
        if value:
            if value not in LABEL_ALIASES:
                raise ValueError(f"Row {row.get('id')}: unknown label {value!r}. Use buyer / not_buyer / unsure.")
            labels[row["id"].strip()] = {"label": LABEL_ALIASES[value], "notes": row.get("notes", "")}
    return labels


def score(sheet: Path = SHEET, source: str = "by hand", outputs_path: Path | None = None,
          results_path: Path | None = None, title: str = "Real-world evaluation") -> str:
    outputs = json.loads((outputs_path or OUTPUTS).read_text(encoding="utf-8"))
    labels = _read_labels(sheet)
    rows = [{**outputs[i], **labels[i]} for i in outputs if i in labels]
    if not rows:
        raise SystemExit("No labels found. Fill the `label` column in the sheet first.")
    decided = [r for r in rows if r["label"] != "unsure"]
    pct = lambda v: f"{v * 100:.0f}%"
    lines = [f"# {title}", "",
             f"{len(rows)} companies from live searches were labelled {source}, without seeing the system's answer "
             f"({len(decided)} buyer / not_buyer, {len(rows) - len(decided)} unsure; unsure rows are left out of the metrics).",
             "", "Positive = the system says Confirmed / Strong / Possible. Baseline = the original keyword rule.", ""]
    for name, subset in [("All products", decided)] + [(PRODUCT_NAMES[p], [r for r in decided if r["product"] == p]) for p in PREFIX]:
        if not subset:
            continue
        s = binary_metrics([(r["label"] == "buyer", r["system"] in POSITIVE_CLASSES) for r in subset])
        b = binary_metrics([(r["label"] == "buyer", r["baseline_positive"]) for r in subset])
        lines += [f"## {name} (n={len(subset)})", "", "| Metric | Old keyword baseline | KRR system |", "|---|---|---|",
                  f"| Precision | {pct(b['precision'])} | {pct(s['precision'])} |",
                  f"| Recall | {pct(b['recall'])} | {pct(s['recall'])} |",
                  f"| F1 | {pct(b['f1'])} | {pct(s['f1'])} |",
                  f"| False-positive rate | {pct(b['fpr'])} ({b['fp']}/{b['fp'] + b['tn']}) | {pct(s['fpr'])} ({s['fp']}/{s['fp'] + s['tn']}) |", ""]
    buyers = [r for r in decided if r["label"] == "buyer"]
    if buyers:
        insufficient = sum(r["system"] == "insufficient_evidence" for r in buyers)
        lines += [f"Of the {len(buyers)} real buyers, the system marked {insufficient} as *Insufficient Evidence* "
                  "(mostly non-English or unreachable sites). These count as missed buyers in the recall above.", ""]
    disagreements = [r for r in decided if (r["label"] == "buyer") != (r["system"] in POSITIVE_CLASSES)]
    lines += [f"## Disagreements ({len(disagreements)})", "", "| ID | Company | Your label | System | Rules | Notes |", "|---|---|---|---|---|---|"]
    for r in disagreements:
        lines.append(f"| {r['id']} | {r['company']} | {r['label']} | {r['system']} | {', '.join(r['rules']) or '-'} | {r['notes']} |")
    report = "\n".join(lines) + "\n"
    (results_path or RESULTS).write_text(report, encoding="utf-8")
    return report


def refresh_outputs(snapshot_dir: Path = SNAPSHOT_DIR) -> None:
    """Re-run the current system on the same companies; keeps the sheet and its labels."""
    old = json.loads(OUTPUTS.read_text(encoding="utf-8"))
    new = {r["id"]: r for r in collect(snapshot_dir, ORIGINAL_SET)}
    mismatched = [i for i in old if i not in new or new[i]["website"] != old[i]["website"]]
    if mismatched:
        raise SystemExit(f"Company ids changed ({mismatched[:5]}); not overwriting the outputs.")
    OUTPUTS.write_text(json.dumps(new, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Refreshed system outputs for {len(new)} companies (labels untouched).")


AI_LABELS = HERE / "ai_labels.csv"
CHECK_SHEET = HERE / "human_check_sheet.csv"
CHECK_SHEET_2 = HERE / "human_check_sheet_round2.csv"  # after the buyer definition was clarified
# Companies whose classification was discussed with the human labeller before round 2.
# They are left out so that round 2 stays blind.
DISCUSSED_WITH_LABELLER = frozenset(
    "W03 W04 W05 W06 W08 W10 W11 W12 W15 W19 W20 W25 W27 W32 W33 "
    "D02 D11 D13 D14 D15 D16 D18 D27 D28 D29 "
    "C02 C03 C04 C06 C08 C09 C10 C11 C16 C18".split()
)
CHECK_SIZE = {"raw_sheep_wool": 7, "duck_down": 7, "cashmere": 6}


def merge_ai(base: Path | None = None) -> None:
    base = base or HERE
    target = base / "ai_labels.csv"
    rows = []
    for name in ("wool", "down", "cashmere"):
        part = base / f"ai_labels_{name}.csv"
        if not part.exists():
            raise SystemExit(f"{part.name} is missing; the AI annotator for it has not finished.")
        rows += [(i, v["label"], v["notes"]) for i, v in _read_labels(part).items()]
    with target.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "label", "notes"])
        writer.writerows(sorted(rows))
    print(f"Merged {len(rows)} AI labels into {target}")


def make_check_sheet(seed: int = 2026, target: Path | None = None, exclude=()) -> list[str]:
    """A fixed random sample per product for the human to label (reproducible)."""
    import random

    target = target or CHECK_SHEET
    outputs = json.loads(OUTPUTS.read_text(encoding="utf-8"))
    rng = random.Random(seed)
    chosen = []
    for product, n in CHECK_SIZE.items():
        ids = sorted(i for i, r in outputs.items() if r["product"] == product and i not in exclude)
        chosen += sorted(rng.sample(ids, min(n, len(ids))))
    with SHEET.open(encoding="utf-8-sig") as src, target.open("w", encoding="utf-8-sig", newline="") as dst:
        reader, writer = csv.reader(src), csv.writer(dst)
        writer.writerow(next(reader))
        for row in reader:
            if row[0] in chosen:
                writer.writerow(row[:5] + ["", ""])  # always blank labels
    print(f"Wrote {len(chosen)} rows to {target}")
    return chosen


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    if not pairs:
        return float("nan")
    cats = sorted({x for p in pairs for x in p})
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    expected = sum((sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n) for c in cats)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def agreement(ai_path: Path = AI_LABELS, human_path: Path = CHECK_SHEET, out_name: str = "LABEL_AGREEMENT.md") -> str:
    ai, human = _read_labels(ai_path), _read_labels(human_path)
    common = sorted(set(ai) & set(human))
    if not common:
        raise SystemExit("No overlapping labelled rows. Label the check sheet first.")
    three = [(ai[i]["label"], human[i]["label"]) for i in common]
    binary = [(a == "buyer", h == "buyer") for a, h in three]
    pct = sum(a == h for a, h in three) / len(three)
    kappa3 = cohen_kappa(three)
    kappa2 = cohen_kappa([(str(a), str(h)) for a, h in binary])
    lines = ["# AI vs human labels (agreement check)", "",
             f"Rows labelled by both: {len(common)}", "",
             f"- Exact agreement (buyer / not_buyer / unsure): {pct * 100:.0f}%",
             f"- Cohen's kappa, 3 labels: {kappa3:.2f}",
             f"- Cohen's kappa, buyer vs. not buyer: {kappa2:.2f}", "",
             "Kappa guide (Landis & Koch): < 0.40 weak, 0.41-0.60 moderate, 0.61-0.80 substantial, > 0.80 almost perfect.", "",
             "| ID | AI label | Human label | AI note | Human note |", "|---|---|---|---|---|"]
    for i in common:
        mark = "" if ai[i]["label"] == human[i]["label"] else " **(differs)**"
        lines.append(f"| {i} | {ai[i]['label']} | {human[i]['label']}{mark} | {ai[i]['notes']} | {human[i]['notes']} |")
    report = "\n".join(lines) + "\n"
    (HERE.parent / out_name).write_text(report, encoding="utf-8")
    return report


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "sheet"
    if command == "sheet":
        make_sheet()
    elif command == "score":
        if len(sys.argv) > 2 and sys.argv[2] == "ai":
            print(score(AI_LABELS, source="by blind AI annotators (see LABEL_AGREEMENT.md for the human check)"))
        else:
            print(score(Path(sys.argv[2]) if len(sys.argv) > 2 else SHEET))
    elif command == "refresh":
        refresh_outputs()
    elif command == "merge-ai":
        merge_ai()
    elif command == "check-sheet":
        make_check_sheet()
    elif command == "fresh-sheet":
        make_fresh_sheet()
    elif command == "fresh-merge":
        merge_ai(FRESH)
    elif command == "fresh-score":
        # labels from the blind AI annotators for the fresh set
        print(score(FRESH / "ai_labels.csv", source="by blind AI annotators",
                    outputs_path=FRESH / "system_outputs.json",
                    results_path=Path(__file__).parent / "FRESH_VALIDATION_RESULTS.md",
                    title="Fresh validation: new companies, system frozen at git tag v2-tuned"))
    elif command == "agreement":
        print(agreement())
    elif command == "check-sheet-2":
        first = set(_read_labels(CHECK_SHEET))  # never reuse round-1 companies
        make_check_sheet(seed=2027, target=CHECK_SHEET_2, exclude=first | DISCUSSED_WITH_LABELLER)
    elif command == "agreement-2":
        print(agreement(human_path=CHECK_SHEET_2, out_name="LABEL_AGREEMENT_ROUND2.md"))
    else:
        raise SystemExit(__doc__)
