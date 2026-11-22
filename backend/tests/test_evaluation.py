"""Dataset integrity + regression guard on the labelled evaluation set.

The thresholds below record the current measured level (see
evaluation/RESULTS.md) so that a future change cannot silently make
false positives worse. They are not a claim of real-world accuracy.
"""

from collections import Counter

import pytest

from app.reasoning.qualification import LABELS
from evaluation.dataset import CASES
from evaluation.run_eval import evaluate, summarise


@pytest.fixture(scope="module")
def summary():
    rows = evaluate()
    return rows, summarise(rows)


def test_dataset_is_balanced_and_well_formed():
    assert len({c["id"] for c in CASES}) == len(CASES)
    assert Counter(c["product"] for c in CASES) == {"duck_down": 16, "raw_sheep_wool": 16, "cashmere": 16}
    assert all(c["expected"] in LABELS for c in CASES)
    assert {c["split"] for c in CASES} == {"dev", "test"}
    categories = {c["category"] for c in CASES}
    for needed in ("relevant", "irrelevant", "alternative_material", "insufficient",
                   "conflicting", "unreachable", "retailer", "supplier"):
        assert needed in categories


def test_system_has_far_fewer_false_positives_than_baseline(summary):
    _, s = summary
    for split in ("all", "test"):
        assert s[split]["system"]["fpr"] < s[split]["baseline"]["fpr"]
    assert s["all"]["system"]["fpr"] <= 0.05


def test_system_precision_and_recall_do_not_regress(summary):
    _, s = summary
    assert s["all"]["system"]["precision"] >= 0.90
    assert s["all"]["system"]["recall"] >= 0.90


def test_every_positive_lead_has_grounded_material_evidence(summary):
    rows, _ = summary
    for r in rows:
        if r["system_pos"]:
            assert r["evidence"], r["case"]["id"]


def test_unreachable_sites_are_never_positive(summary):
    rows, _ = summary
    for r in rows:
        if r["case"]["category"] in {"unreachable", "non_english", "insufficient"}:
            assert not r["system_pos"], r["case"]["id"]


def test_the_restaurant_example_is_rejected(summary):
    rows, _ = summary
    restaurant = next(r for r in rows if r["case"]["id"] == "DD07")
    assert restaurant["baseline_pos"] and restaurant["system"] == "not_relevant"
