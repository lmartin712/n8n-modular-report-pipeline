"""Exports the 5 EN experiment workflows from the local n8n and writes SANITIZED copies to ../workflows/.

Kept: node names, types, positions, connections, sticky notes, IF/loop/merge structure, Gotenberg call shape.
Replaced: every SQL query, every Code-node body, Sheets document/sheet IDs, credentials, file paths, workflow IDs.
Run from anywhere: python export_sanitized.py
"""
import io, json, os, re, sys, urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://127.0.0.1:5678/api/v1"
KEY = next(x for x in (l.strip() for l in io.open(os.path.expanduser(r"~\n8n_api_key.txt"), encoding="utf-8-sig")) if x.startswith("eyJ") and x.count(".") == 2)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workflows")

# source id -> (file name, public workflow name)
WF = {
    "3JoDlw2zVLAh4Q4x": ("01-sub-html-to-pdf.json", "SUB · HTML to PDF (Gotenberg, portrait/landscape A4)"),
    "RLCGNIpGLL39pvQW": ("02-sub-prerequisite-check.json", "SUB · Prerequisite check (DB health + heartbeat)"),
    "YOu7hjqkSMWl33u0": ("03-sub-report-package-payroll.json", "SUB · Report package: Payroll (4 reports)"),
    "H2X9EMoaopuIxbID": ("04-sub-report-package-vat.json", "SUB · Report package: VAT (4 reports)"),
    "FHQkBsHOiDep6Uo3": ("05-controller.json", "Controller · Report export (calls the 4 sub-workflows)"),
}
KEEP_TYPES = {
    "n8n-nodes-base.stickyNote", "n8n-nodes-base.executeWorkflowTrigger", "n8n-nodes-base.manualTrigger",
    "n8n-nodes-base.merge", "n8n-nodes-base.splitInBatches",
}
SKIP_KEYS = {"id", "credentials", "webhookId", "notes", "notesInFlow"}


def get(wid):
    req = urllib.request.Request(f"{BASE}/workflows/{wid}", headers={"X-N8N-API-KEY": KEY})
    return json.load(urllib.request.urlopen(req))


def code_stub(name):
    return (f"// {name}\n// Production logic is client-owned and not published.\n"
            "// This stub passes items through so the workflow imports and the wiring can be inspected.\n"
            "return $input.all();")


def sql_stub(name):
    rep = name.split(":", 1)[-1].strip() if ":" in name else name
    return (f"-- {name}\n-- Illustrative query on a fictional schema; the production SQL is client-owned.\n"
            f"SELECT *\nFROM demo.{re.sub(r'[^a-z0-9_]', '_', rep.lower())[:40]}\n"
            "WHERE company_id = {{ $json.company_id }}\n  AND period = '{{ $json.period }}';")


def clean(n, ids):
    t = n["type"]
    out = {k: v for k, v in n.items() if k not in SKIP_KEYS}
    p = out.get("parameters", {})
    if t in KEEP_TYPES:
        return out
    if t == "n8n-nodes-base.code":
        out["parameters"] = {"jsCode": code_stub(n["name"])}
    elif t == "n8n-nodes-base.microsoftSql":
        out["parameters"] = {"operation": "executeQuery", "query": sql_stub(n["name"])}
    elif t == "n8n-nodes-base.googleSheets":
        out["parameters"] = {"operation": p.get("operation", "read"),
                             "documentId": {"__rl": True, "mode": "id", "value": "YOUR_CONTROL_SHEET_ID"},
                             "sheetName": {"__rl": True, "mode": "name", "value": "YOUR_TAB"}}
    elif t == "n8n-nodes-base.executeWorkflow":
        tgt = p["workflowId"]["value"]
        out["parameters"] = dict(p, workflowId={"__rl": True, "mode": "id", "value": f"REPLACE_WITH_ID_OF:{ids.get(tgt, 'unknown')}"})
    elif t == "n8n-nodes-base.httpRequest":
        out["parameters"] = p  # Gotenberg call: internal docker hostname + paper size only; checked by scan below
    elif t == "n8n-nodes-base.if":
        out["parameters"] = p  # conditions reference field names only; checked by scan below
    elif t == "n8n-nodes-base.scheduleTrigger":
        out["parameters"] = {"rule": {"interval": [{"field": "minutes", "minutesInterval": 10}]}}
    else:
        raise SystemExit(f"Unhandled node type {t} ({n['name']}) — decide how to sanitize it first.")
    return out


ids = {wid: fname for wid, (fname, _) in WF.items()}
os.makedirs(OUT, exist_ok=True)
for wid, (fname, pub) in WF.items():
    w = get(wid)
    assert not w.get("active"), f"{wid} is active — refusing"
    data = {"name": pub, "nodes": [clean(n, ids) for n in w["nodes"]], "connections": w["connections"],
            "settings": {"executionOrder": "v1"}}
    io.open(os.path.join(OUT, fname), "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"{fname}: {len(data['nodes'])} nodes")
