import json
import threading
import urllib.error
import urllib.request

import pytest

from evaluation.label_tool import load_rows, serve
from evaluation.real_world import _read_labels

SHEET = (
    "id,product,company,website,pages_the_system_read,label,notes\n"
    "W01,Raw Sheep Wool,Mill A,https://a.test,https://a.test/ https://a.test/about,,\n"
    "D01,Duck Down,Shop B,https://b.test,https://b.test/,,\n"
)


@pytest.fixture
def server(tmp_path):
    sheet = tmp_path / "labelling_sheet.csv"
    sheet.write_text(SHEET, encoding="utf-8-sig")
    srv = serve(sheet, port=18765, open_browser=False)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", sheet
    srv.shutdown()
    srv.server_close()


def post(base, payload):
    req = urllib.request.Request(f"{base}/api/label", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def test_page_and_rows_are_served_without_system_answers(server):
    base, _ = server
    page = urllib.request.urlopen(base + "/").read().decode()
    assert "blind labelling" in page
    rows = json.loads(urllib.request.urlopen(base + "/api/rows").read())
    assert [r["id"] for r in rows] == ["W01", "D01"]
    assert rows[0]["pages"] == ["https://a.test/", "https://a.test/about"]
    assert "system" not in json.dumps(rows) and "score" not in json.dumps(rows)


def test_labels_are_saved_to_the_sheet_and_readable_by_the_scorer(server):
    base, sheet = server
    assert post(base, {"id": "W01", "label": "buyer", "notes": "makes yarn"})["labelled"] == 1
    assert post(base, {"id": "D01", "label": "not_buyer", "notes": "only a shop"})["labelled"] == 2
    assert {r["id"]: r["label"] for r in load_rows(sheet)} == {"W01": "buyer", "D01": "not_buyer"}
    assert _read_labels(sheet)["W01"] == {"label": "buyer", "notes": "makes yarn"}


@pytest.mark.parametrize("payload", [{"id": "W01", "label": "maybe"}, {"id": "ZZZ", "label": "buyer"}])
def test_bad_requests_are_rejected(server, payload):
    base, _ = server
    with pytest.raises(urllib.error.HTTPError):
        post(base, payload)
