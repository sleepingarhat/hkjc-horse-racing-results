"""
Lightweight read-only inventory endpoint for prod disk visibility.
Exposes:
  GET /            -> HTML overview
  GET /inventory   -> JSON file/row counts
  GET /head/<path> -> first 200 chars of small file (debug)
Stdlib only. Binds 0.0.0.0:5000.
"""
import os
import json
import csv
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, unquote

DATA_DIRS = [
    "horses/profiles",
    "horses/form_records",
    "horses/pedigree",
    "horses/trackwork",
    "horses/injury",
    "entries",
    "trials",
    "results",
    "jockeys",
    "trainers",
]

EXTRA_FILES = [
    "horses/lifecycle.json",
    "entries/today_entries.txt",
    "horses/profiles/horse_profiles.csv",
    "last_sync.json",
]


def dir_summary(path: str) -> dict:
    if not os.path.isdir(path):
        return {"exists": False, "items": 0}
    try:
        items = os.listdir(path)
    except Exception as e:
        return {"exists": True, "items": -1, "error": str(e)}
    return {"exists": True, "items": len(items)}


def file_summary(path: str) -> dict:
    if not os.path.isfile(path):
        return {"exists": False}
    try:
        st = os.stat(path)
        info = {"exists": True, "size": st.st_size, "mtime": int(st.st_mtime)}
        if path.endswith(".csv"):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                info["rows"] = sum(1 for _ in f) - 1
        elif path.endswith(".json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                if isinstance(d, dict):
                    info["keys"] = len(d)
                elif isinstance(d, list):
                    info["len"] = len(d)
            except Exception:
                pass
        elif path.endswith(".txt"):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                info["lines"] = sum(1 for _ in f)
        return info
    except Exception as e:
        return {"exists": True, "error": str(e)}


def build_inventory() -> dict:
    return {
        "cwd": os.getcwd(),
        "dirs": {d: dir_summary(d) for d in DATA_DIRS},
        "files": {f: file_summary(f) for f in EXTRA_FILES},
    }


def render_html(inv: dict) -> str:
    rows = []
    rows.append("<h2>Directories</h2><table border=1 cellpadding=4>")
    rows.append("<tr><th>path</th><th>exists</th><th>items</th></tr>")
    for d, info in inv["dirs"].items():
        rows.append(
            f"<tr><td>{d}</td><td>{info.get('exists')}</td><td>{info.get('items')}</td></tr>"
        )
    rows.append("</table>")
    rows.append("<h2>Files</h2><table border=1 cellpadding=4>")
    rows.append("<tr><th>path</th><th>exists</th><th>size</th><th>rows/lines/keys</th></tr>")
    for f, info in inv["files"].items():
        v = info.get("rows") or info.get("lines") or info.get("keys") or info.get("len") or ""
        rows.append(
            f"<tr><td>{f}</td><td>{info.get('exists')}</td><td>{info.get('size','')}</td><td>{v}</td></tr>"
        )
    rows.append("</table>")
    return (
        "<html><head><meta charset='utf-8'><title>HKJC Inventory</title></head>"
        f"<body><h1>HKJC Prod Inventory</h1><p>cwd: {inv['cwd']}</p>"
        + "".join(rows)
        + "<p><a href='/inventory'>JSON</a></p></body></html>"
    )


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a, **kw):
        pass  # quiet

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            inv = build_inventory()
            body = render_html(inv).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif u.path == "/inventory":
            inv = build_inventory()
            body = json.dumps(inv, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif u.path == "/diag":
            import subprocess
            def run(cmd):
                try:
                    p = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    return {"rc": p.returncode, "stdout": p.stdout[:2000], "stderr": p.stderr[:2000]}
                except Exception as e:
                    return {"error": str(e)}
            diag = {
                "cwd": os.getcwd(),
                "has_dot_git": os.path.isdir(".git"),
                "has_gh_token": bool(os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")),
                "git_status_horses": run(["git", "status", "--porcelain", "--", "horses"]),
                "git_lsfiles_horses": run(["git", "ls-files", "-o", "--", "horses"]),
                "git_log_top": run(["git", "log", "--oneline", "-5"]),
                "git_remote": run(["git", "remote", "-v"]),
            }
            body = json.dumps(diag, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif u.path == "/data_stats":
            stats = {"data_dir_exists": os.path.isdir("data"), "years": [], "totals": {"files": 0, "size_bytes": 0, "rows": 0}}
            if stats["data_dir_exists"]:
                for year in sorted(os.listdir("data")):
                    ypath = os.path.join("data", year)
                    if not os.path.isdir(ypath):
                        continue
                    y_files = 0
                    y_size = 0
                    y_rows = 0
                    for root, _, files in os.walk(ypath):
                        for fn in files:
                            if not fn.endswith(".csv"):
                                continue
                            fp = os.path.join(root, fn)
                            try:
                                y_size += os.path.getsize(fp)
                                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                                    y_rows += max(0, sum(1 for _ in fh) - 1)
                                y_files += 1
                            except Exception:
                                pass
                    stats["years"].append({"year": year, "files": y_files, "size_bytes": y_size, "rows": y_rows})
                    stats["totals"]["files"] += y_files
                    stats["totals"]["size_bytes"] += y_size
                    stats["totals"]["rows"] += y_rows
            body = json.dumps(stats, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif u.path.startswith("/head/"):
            rel = unquote(u.path[len("/head/"):])
            safe = os.path.normpath(rel)
            if safe.startswith("..") or os.path.isabs(safe):
                self.send_error(400, "bad path")
                return
            if not os.path.isfile(safe):
                self.send_error(404, "not found")
                return
            try:
                with open(safe, "r", encoding="utf-8", errors="ignore") as f:
                    body = f.read(2000).encode("utf-8")
            except Exception as e:
                self.send_error(500, str(e))
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)


def main():
    port = int(os.environ.get("PORT", "5000"))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"[inventory] listening on 0.0.0.0:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
