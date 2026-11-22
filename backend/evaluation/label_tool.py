"""Local labelling page for the blind real-world evaluation.

    cd backend
    venv\\Scripts\\python.exe -m evaluation.label_tool          (all 90 rows)
    venv\\Scripts\\python.exe -m evaluation.label_tool check    (only the 20-row human check sheet)

Opens http://127.0.0.1:8765 in your browser. Every click is saved straight into
evaluation/real_world/labelling_sheet.csv. The system's answers are never shown.
Only listens on 127.0.0.1 (your own computer). Stop it with Ctrl+C.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .real_world import CHECK_SHEET, LABEL_ALIASES, SHEET

COLUMNS = ["id", "product", "company", "website", "pages_the_system_read", "label", "notes"]
VALID = {"buyer", "not_buyer", "unsure", ""}
_lock = threading.Lock()


def load_rows(sheet: Path) -> list[dict]:
    raw = sheet.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")  # saved by Excel
    dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;\t")
    rows = []
    for row in csv.DictReader(io.StringIO(text), dialect=dialect):
        label = (row.get("label") or "").strip().lower()
        rows.append({
            "id": row["id"].strip(),
            "product": row.get("product", ""),
            "company": row.get("company", ""),
            "website": row.get("website", ""),
            "pages": [p for p in (row.get("pages_the_system_read") or "").split() if p.startswith("http")],
            "label": LABEL_ALIASES.get(label, ""),
            "notes": row.get("notes") or "",
        })
    return rows


def save_rows(sheet: Path, rows: list[dict]) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(COLUMNS)
    for r in rows:
        writer.writerow([r["id"], r["product"], r["company"], r["website"], " ".join(r["pages"]), r["label"], r["notes"]])
    tmp = sheet.with_suffix(".tmp")
    tmp.write_text(buffer.getvalue(), encoding="utf-8-sig", newline="")
    os.replace(tmp, sheet)  # atomic: the sheet is never half-written


def make_handler(sheet: Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the console quiet
            pass

        def _send(self, status, body: bytes, content_type: str):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status, payload):
            self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json")

        def do_GET(self):
            if self.path == "/":
                self._send(HTTPStatus.OK, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif self.path == "/api/rows":
                with _lock:
                    self._json(HTTPStatus.OK, load_rows(sheet))
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self):
            if self.path != "/api/label":
                return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            try:
                length = min(int(self.headers.get("Content-Length", 0)), 20_000)
                data = json.loads(self.rfile.read(length))
                label = str(data.get("label", ""))
                notes = str(data.get("notes", ""))[:500].replace("\n", " ")
                if label not in VALID:
                    raise ValueError("bad label")
            except (ValueError, json.JSONDecodeError):
                return self._json(HTTPStatus.BAD_REQUEST, {"error": "Invalid request."})
            with _lock:
                rows = load_rows(sheet)
                row = next((r for r in rows if r["id"] == data.get("id")), None)
                if row is None:
                    return self._json(HTTPStatus.NOT_FOUND, {"error": "Unknown id."})
                row["label"], row["notes"] = label, notes
                try:
                    save_rows(sheet, rows)
                except PermissionError:
                    return self._json(HTTPStatus.CONFLICT, {
                        "error": "The sheet is open in Excel. Close Excel, then click again."})
            self._json(HTTPStatus.OK, {"ok": True, "labelled": sum(bool(r["label"]) for r in rows)})

    return Handler


def serve(sheet: Path = SHEET, port: int = 8765, open_browser: bool = True) -> ThreadingHTTPServer:
    if not sheet.exists():
        raise SystemExit(f"{sheet} not found. Run `python -m evaluation.real_world sheet` first.")
    for candidate in range(port, port + 10):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), make_handler(sheet))
            break
        except OSError:
            continue
    else:
        raise SystemExit("No free port between 8765 and 8774.")
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Labelling page: {url}\nAnswers are saved to {sheet}\nPress Ctrl+C here to stop.")
    if open_browser:
        webbrowser.open(url)
    return server


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Buyer AI - Labelling</title>
<style>
:root{--bg:#0f172a;--panel:#162033;--line:rgba(148,163,184,.16);--text:#e2e8f0;--muted:#8a99ae;--cyan:#67e8f9;--green:#34d399;--red:#fb7185;--amber:#fbbf24}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 Inter,"Segoe UI",system-ui,sans-serif}
header{position:sticky;top:0;z-index:2;background:#0b1220ee;border-bottom:1px solid var(--line);padding:12px 20px;display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
h1{font-size:15px;margin:0}.muted{color:var(--muted)}.bar{height:6px;width:220px;background:rgba(255,255,255,.08);border-radius:9px;overflow:hidden}.bar>i{display:block;height:100%;background:linear-gradient(90deg,var(--cyan),#a5b4fc)}
.tabs{display:flex;gap:6px;flex-wrap:wrap}.tab{border:1px solid var(--line);background:none;color:var(--muted);border-radius:99px;padding:4px 11px;cursor:pointer;font:inherit;font-size:12px}.tab.on{border-color:var(--cyan);color:var(--cyan)}
main{display:grid;grid-template-columns:300px 1fr;gap:18px;max-width:1200px;margin:18px auto;padding:0 16px}
@media(max-width:800px){main{grid-template-columns:1fr}#list{max-height:220px}}
#list{background:var(--panel);border:1px solid var(--line);border-radius:12px;max-height:calc(100vh - 110px);overflow:auto}
.item{display:flex;gap:8px;align-items:center;padding:8px 12px;border-bottom:1px solid var(--line);cursor:pointer;font-size:12px}.item:hover{background:rgba(255,255,255,.03)}.item.cur{background:rgba(103,232,249,.09)}
.dot{width:9px;height:9px;border-radius:9px;flex-shrink:0;background:#334155}.dot.buyer{background:var(--green)}.dot.not_buyer{background:var(--red)}.dot.unsure{background:var(--amber)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px}
.pill{display:inline-block;border:1px solid var(--line);border-radius:7px;padding:2px 8px;font-size:12px;color:var(--cyan)}
h2{font-size:22px;margin:10px 0 4px}.open{display:inline-flex;gap:8px;align-items:center;margin:14px 0 6px;background:linear-gradient(100deg,var(--cyan),#a5b4fc);color:#0b1220;font-weight:700;text-decoration:none;padding:11px 18px;border-radius:10px}
.pages a{display:block;color:var(--muted);font-size:12px;word-break:break-all}.pages a:hover{color:var(--cyan)}
.q{margin:22px 0 10px;font-weight:600}.answers{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.ans{border:2px solid var(--line);background:rgba(255,255,255,.02);color:var(--text);border-radius:12px;padding:14px 8px;font:inherit;font-weight:700;cursor:pointer}.ans small{display:block;font-weight:400;color:var(--muted);margin-top:3px}
.ans.buyer.on{border-color:var(--green);background:rgba(52,211,153,.12)}.ans.not_buyer.on{border-color:var(--red);background:rgba(251,113,133,.1)}.ans.unsure.on{border-color:var(--amber);background:rgba(251,191,36,.1)}
textarea{width:100%;margin-top:14px;background:#0b1220;border:1px solid var(--line);border-radius:9px;color:var(--text);padding:9px;font:inherit;font-size:13px;resize:vertical}
.nav{display:flex;justify-content:space-between;margin-top:14px}.nav button{background:none;border:1px solid var(--line);color:var(--text);border-radius:9px;padding:8px 14px;cursor:pointer;font:inherit}
.status{min-height:20px;font-size:12px;margin-top:8px}.err{color:var(--red)}.ok{color:var(--green)}
details{margin-top:18px;font-size:13px;color:var(--muted)}details li{margin:3px 0}kbd{border:1px solid var(--line);border-radius:4px;padding:0 5px;font-size:11px}
</style></head><body>
<header><div><h1>Smart Buyer AI - blind labelling</h1><span class="muted" id="count"></span></div>
<div class="bar"><i id="progress" style="width:0"></i></div>
<div class="tabs" id="tabs"></div></header>
<main><nav id="list" aria-label="Companies"></nav><section class="card" id="card"></section></main>
<script>
let rows=[], filter="All", idx=0;
const $=s=>document.querySelector(s), esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const view=()=>rows.filter(r=>filter==="All"||r.product===filter);
async function load(){rows=await (await fetch("/api/rows")).json(); const first=view().findIndex(r=>!r.label); idx=first<0?0:first; render();}
function render(){
  const v=view(), done=rows.filter(r=>r.label).length;
  $("#count").textContent=`${done} / ${rows.length} labelled`; $("#progress").style.width=(100*done/rows.length)+"%";
  const products=["All",...new Set(rows.map(r=>r.product))];
  $("#tabs").innerHTML=products.map(p=>`<button class="tab ${p===filter?"on":""}" data-p="${esc(p)}">${esc(p)} (${rows.filter(r=>p==="All"||r.product===p).filter(r=>r.label).length}/${rows.filter(r=>p==="All"||r.product===p).length})</button>`).join("");
  document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{filter=b.dataset.p; const f=view().findIndex(r=>!r.label); idx=f<0?0:f; render();});
  $("#list").innerHTML=v.map((r,i)=>`<div class="item ${i===idx?"cur":""}" data-i="${i}"><span class="dot ${r.label}"></span><b>${esc(r.id)}</b> ${esc(r.company)}</div>`).join("");
  document.querySelectorAll(".item").forEach(el=>el.onclick=()=>{idx=+el.dataset.i; render();});
  document.querySelector(".item.cur")?.scrollIntoView({block:"nearest"});
  const r=v[idx]; if(!r){$("#card").innerHTML="<p>No companies.</p>";return;}
  const ok=/^https?:\/\//.test(r.website), site=r.website.split(" ")[0];
  $("#card").innerHTML=`<span class="pill">${esc(r.product)}</span> <span class="muted">${esc(r.id)} &middot; ${idx+1} of ${v.length}</span>
  <h2>${esc(r.company)}</h2><div class="muted">${esc(r.website)}</div>
  ${ok?`<a class="open" href="${esc(site)}" target="_blank" rel="noopener noreferrer">Open website &#8599;</a>`:""}
  ${r.pages.length?`<div class="pages"><span class="muted" style="font-size:12px">Pages the system read (optional):</span>${r.pages.map(p=>`<a href="${esc(p)}" target="_blank" rel="noopener noreferrer">${esc(p)}</a>`).join("")}</div>`:""}
  <p class="q">Would this company plausibly buy <u>${esc(r.product)}</u> as a raw material?</p>
  <div class="answers">
   <button class="ans buyer ${r.label==="buyer"?"on":""}" data-l="buyer">Buyer<small>makes / processes / trades it &middot; key 1</small></button>
   <button class="ans not_buyer ${r.label==="not_buyer"?"on":""}" data-l="not_buyer">Not buyer<small>shop, farm, directory, unrelated &middot; key 2</small></button>
   <button class="ans unsure ${r.label==="unsure"?"on":""}" data-l="unsure">Unsure<small>can't tell from the site &middot; key 3</small></button>
  </div>
  <textarea id="notes" rows="2" placeholder="Optional note, e.g. 'makes wool carpets' or 'only an online shop'">${esc(r.notes)}</textarea>
  <div class="status" id="status"></div>
  <div class="nav"><button id="prev">&larr; Previous</button><button id="next">Next &rarr;</button></div>
  <details><summary>Labelling rules</summary><ul>
   <li>Judge only from the company's own website. Do not search elsewhere.</li>
   <li><b>Buyer</b>: spins, weaves, knits, scours, fills or manufactures products from this material, or trades the raw material.</li>
   <li><b>Not buyer</b>: retailer/brand selling finished goods only; farm or producer that sells the material; directory, news site, association; unrelated business; synthetic only.</li>
   <li><b>Unsure</b>: site does not open, not in a language you read, or says too little.</li>
   <li>Keys: <kbd>1</kbd> <kbd>2</kbd> <kbd>3</kbd> answer &middot; <kbd>&larr;</kbd> <kbd>&rarr;</kbd> move &middot; <kbd>O</kbd> open website.</li></ul></details>`;
  document.querySelectorAll(".ans").forEach(b=>b.onclick=()=>answer(b.dataset.l));
  $("#prev").onclick=()=>move(-1); $("#next").onclick=()=>move(1);
  $("#notes").onchange=()=>r.label&&save(r,r.label,false);
}
function move(d){const v=view(); idx=Math.max(0,Math.min(v.length-1,idx+d)); render();}
async function save(r,label,advance){
  const notes=$("#notes")?.value||"";
  const res=await fetch("/api/label",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id:r.id,label,notes})});
  const data=await res.json().catch(()=>({}));
  if(!res.ok){$("#status").innerHTML=`<span class="err">Not saved: ${esc(data.error||res.status)}</span>`;return;}
  r.label=label; r.notes=notes;
  if(advance){const v=view(); const nxt=v.findIndex((x,i)=>i>idx&&!x.label); idx=nxt<0?Math.min(idx+1,v.length-1):nxt;}
  render(); $("#status").innerHTML='<span class="ok">Saved</span>';
}
function answer(label){const r=view()[idx]; if(r) save(r,label,true);}
document.addEventListener("keydown",e=>{
  if(e.target.tagName==="TEXTAREA")return;
  if(e.key==="1")answer("buyer"); else if(e.key==="2")answer("not_buyer"); else if(e.key==="3")answer("unsure");
  else if(e.key==="ArrowRight")move(1); else if(e.key==="ArrowLeft")move(-1);
  else if(e.key.toLowerCase()==="o"){const a=document.querySelector(".open"); if(a) window.open(a.href,"_blank","noopener");}
});
load().catch(()=>{$("#card").innerHTML='<p class="err">Could not load the sheet. Is the labelling tool still running?</p>';});
</script></body></html>"""


if __name__ == "__main__":
    # `python -m evaluation.label_tool check` labels only the 20-row human check sheet
    srv = serve(CHECK_SHEET if sys.argv[1:] == ["check"] else SHEET)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Your labels are saved in the sheet.")
        sys.exit(0)
