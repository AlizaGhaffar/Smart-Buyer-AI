"""Tests for the Phase 5 verification tools (audit + real-world labelling)."""

import json

import pytest

from app.pipeline.runner import PipelineRequest, run_pipeline
from evaluation import audit as audit_mod
from evaluation import real_world
from tests.fakes import FakeFetcher, FakeProvider
from tests.test_pipeline import HITS, SITES


@pytest.fixture
def snapshots(tmp_path):
    run_pipeline(PipelineRequest("duck_down", "Japan"), search_provider=FakeProvider(HITS),
                 fetcher=FakeFetcher(SITES), search_sleep=lambda s: None, snapshot_dir=tmp_path)
    return tmp_path


def test_audit_passes_on_a_clean_run(snapshots):
    report, failures = audit_mod.audit(snapshots)
    assert failures == [] and "PASS" in report and "DD-P1" in report


def test_audit_detects_a_tampered_quote(snapshots):
    # Simulate an extractor that invents a quote: the audit must catch it.
    original = audit_mod.run_pipeline

    def tampered(req, snapshot_dir):
        result = original(req, snapshot_dir=snapshot_dir)
        for lead in result["leads"]:
            for fact in lead["facts"]:
                for ev in fact["evidence"]:
                    ev["quote"] = "We buy 500 tonnes of duck down every year."  # invented
        return result

    audit_mod.run_pipeline = tampered
    try:
        _, failures = audit_mod.audit(snapshots)
    finally:
        audit_mod.run_pipeline = original
    assert any("quote not found" in f for f in failures)


def test_labelling_sheet_is_blind_and_scoring_works(snapshots, tmp_path, monkeypatch):
    out = tmp_path / "rw"
    monkeypatch.setattr(real_world, "HERE", out)
    monkeypatch.setattr(real_world, "SHEET", out / "labelling_sheet.csv")
    monkeypatch.setattr(real_world, "OUTPUTS", out / "system_outputs.json")
    monkeypatch.setattr(real_world, "RESULTS", out / "RESULTS.md")
    real_world.make_sheet(snapshots)
    sheet = (out / "labelling_sheet.csv").read_text(encoding="utf-8-sig")
    assert "strong_potential_buyer" not in sheet and "not_relevant" not in sheet  # blind
    header, *rows = sheet.strip().splitlines()
    assert header.startswith("id,product,company,website")

    # label like Excel in a ';' locale: northwind = buyer, the restaurant = not buyer, dead site = ?
    outputs = json.loads((out / "system_outputs.json").read_text(encoding="utf-8"))
    labelled = ["id;label;notes"]
    for rid, r in outputs.items():
        label = {"northwind.test": "y", "osaka-duck.test": "n"}.get(r["website"].split("/")[2], "?")
        labelled.append(f"{rid};{label};")
    labelled_path = tmp_path / "labelled.csv"
    labelled_path.write_text("\n".join(labelled), encoding="cp1252")
    report = real_world.score(labelled_path)
    assert "False-positive rate" in report and "| Precision | " in report
    assert "unsure" in report


def test_unknown_label_is_rejected(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("id,label\nW01,maybe\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown label"):
        real_world._read_labels(path)


def test_cohen_kappa_known_values():
    perfect = [("buyer", "buyer"), ("not_buyer", "not_buyer"), ("buyer", "buyer")]
    assert real_world.cohen_kappa(perfect) == 1.0
    chance = [("buyer", "buyer"), ("buyer", "not_buyer"), ("not_buyer", "buyer"), ("not_buyer", "not_buyer")]
    assert abs(real_world.cohen_kappa(chance)) < 1e-9


def test_check_sheet_and_agreement(snapshots, tmp_path, monkeypatch):
    out = tmp_path / "rw"
    for name, value in {"HERE": out, "SHEET": out / "labelling_sheet.csv", "OUTPUTS": out / "system_outputs.json",
                        "RESULTS": out / "RESULTS.md", "CHECK_SHEET": out / "check.csv",
                        "AI_LABELS": out / "ai.csv"}.items():
        monkeypatch.setattr(real_world, name, value)
    monkeypatch.setattr(real_world, "CHECK_SIZE", {"raw_sheep_wool": 0, "duck_down": 2, "cashmere": 0})
    real_world.make_sheet(snapshots)
    chosen = real_world.make_check_sheet()
    assert len(chosen) == 2 and chosen == real_world.make_check_sheet()  # reproducible sample
    check = (out / "check.csv").read_text(encoding="utf-8-sig").splitlines()
    assert len(check) == 3 and all(line.endswith(",,") for line in check[1:])  # blank labels
    (out / "ai.csv").write_text("id,label,notes\n" + "\n".join(f"{i},buyer,x" for i in chosen), encoding="utf-8")
    (out / "check.csv").write_text("id,label,notes\n" + f"{chosen[0]},buyer,\n{chosen[1]},not_buyer,\n", encoding="utf-8")
    report = real_world.agreement(out / "ai.csv", out / "check.csv")
    assert "Exact agreement (buyer / not_buyer / unsure): 50%" in report and "(differs)" in report
