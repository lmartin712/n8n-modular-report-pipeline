"""Leak scan for the published workflow JSONs and docs. Exit 1 on any hit.
Also prints the parameters of nodes whose parameters were KEPT (IF, HTTP) for a human read."""
import io, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PATTERNS = {
    "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
    "windows/unc path": r"[A-Za-z]:\\\\|\\\\\\\\[\w.-]+",
    "google id": r"[A-Za-z0-9_-]{33,}",
    "hu tax number": r"\b\d{8}-\d-\d{2}\b",
    "url (non-local)": r"https?://(?!gotenberg[:/]|localhost|127\.0\.0\.1)[^\s\"']+",
    "names/terms": r"(?i)infot[eé]ka|vajda|dp ?world|web-?tax|zita|julika|zsolt|anita|kont[uú]r|\bbt\.|\bkft\.",
}
hits = 0
for dp, _, fs in os.walk(ROOT):
    rel = os.path.relpath(dp, ROOT).split(os.sep)[0]
    if rel in (".git", "tools", "images"):
        continue
    for f in fs:
        if not f.endswith((".json", ".md")):
            continue
        txt = io.open(os.path.join(dp, f), encoding="utf-8").read()
        for label, rx in PATTERNS.items():
            for m in re.finditer(rx, txt):
                hits += 1
                print(f"HIT {f} [{label}]: {txt[max(0, m.start() - 40):m.end() + 20]!r}")
        if f.endswith(".json"):
            for n in json.loads(txt)["nodes"]:
                if n["type"] in ("n8n-nodes-base.if", "n8n-nodes-base.httpRequest"):
                    print(f"-- KEPT {f} :: {n['name']}: {json.dumps(n['parameters'], ensure_ascii=False)[:500]}")
print("TALÁLAT:", hits)
sys.exit(1 if hits else 0)
