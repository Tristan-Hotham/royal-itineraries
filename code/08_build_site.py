"""Step 8. Build ../index.html and ../README.md from page_template.html and README_template.md.

Every number in the text is a placeholder like {{monarchs.John.nights|int}} filled from ../data/results.json.
The page data (results and the compact itineraries in page_data.json) are embedded as `const D = ...`.
Formats: int, pct0, pct1, f1, km0, month, raw.
Run: python3 08_build_site.py
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
P = json.load(open(os.path.join(ROOT, "data", "page_data.json")))
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f, pct="%"):
    if f == "int": return f"{int(round(float(v))):,}"
    if f == "pct0": return f"{float(v) * 100:.0f}{pct}"
    if f == "pct1": return f"{float(v) * 100:.1f}{pct}"
    if f in ("f1",): return f"{float(v):.1f}"
    if f == "km0": return f"{float(v):.0f}"
    if f == "month": return MONTHS[int(v) - 1]
    if f == "date":
        y, m, d = str(v).split("-"); return f"{int(d)} {MONTHS[int(m) - 1]} {y}"
    return str(v)


def sub(m_):
    path, _, f = m_.group(1).partition("|")
    return fmt(get(path.strip()), f.strip() or "raw")


if __name__ == "__main__":
    t = open(os.path.join(HERE, "page_template.html")).read()
    t = re.sub(r"\{\{(.+?)\}\}", sub, t)
    t = t.replace("/*DATA*/", "const D = " + json.dumps(dict(R=R, P=P), separators=(",", ":"), ensure_ascii=False) + ";")
    assert "{{" not in t
    open(os.path.join(ROOT, "index.html"), "w").write(t)
    print("index.html", len(t.encode()) // 1024, "KB")
    md = re.sub(r"\{\{(.+?)\}\}", sub, open(os.path.join(HERE, "README_template.md")).read())
    open(os.path.join(ROOT, "README.md"), "w").write(md)
    print("README.md written")
