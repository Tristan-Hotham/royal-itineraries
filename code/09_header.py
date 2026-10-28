"""Step 9. Render ../header.png (1200x630 social card) with Playwright Chromium.

Fonts: FONT_DIR holding FrauncesVar.ttf, SourceSerif4-Regular.ttf, IBMPlexMono-Regular.ttf and IBMPlexMono-Medium.ttf
(from github.com/google/fonts); otherwise system serif is used. Land: ../work/land.json from 07_basemap.py (Natural Earth).
Run: FONT_DIR=/path/to/fonts python3 09_header.py
"""
import csv, json, math, os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
LAND = json.load(open(os.path.join(ROOT, "work", "land.json")))
FD = os.environ.get("FONT_DIR", "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts")
K = math.cos(math.radians(51))
LON0, LON1, LAT0, LAT1 = -7.6, 4.2, 43.0, 56.4
Hh = 610; Ww = Hh * (LON1 - LON0) * K / (LAT1 - LAT0)


def pr(lat, lon):
    return (lon - LON0) * K / ((LAT1 - LAT0)) * Hh, (LAT1 - lat) / (LAT1 - LAT0) * Hh


land = ""
for ring in LAND:
    if max(p[0] for p in ring) < LON0 - 1 or min(p[0] for p in ring) > LON1 + 1: continue
    land += "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in (pr(p[1], p[0]) for p in ring)) + "Z"
pl = list(csv.DictReader(open(os.path.join(ROOT, "data", "places.csv"))))
dots = ""
for mon, col in (("Edward I", "#B07D1A"), ("John", "#24427A")):
    for r in pl:
        if r["monarch"] != mon or int(r["nights"]) == 0: continue
        x, y = pr(float(r["lat"]), float(r["lon"]))
        if not (0 <= x <= Ww and 0 <= y <= Hh): continue
        rad = 1.6 + math.sqrt(int(r["nights"])) * (0.45 if mon == "Edward I" else 0.6)
        dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{col}" fill-opacity=".38" stroke="{col}" stroke-opacity=".7" stroke-width=".6"/>'
ff = "".join(f"@font-face{{font-family:'{n}';src:url('file://{FD}/{f}');font-weight:{w};}}" for n, f, w in [
    ("Fraunces", "FrauncesVar.ttf", "100 900"), ("Source Serif 4", "SourceSerif4-Regular.ttf", "400"),
    ("IBM Plex Mono", "IBMPlexMono-Regular.ttf", "400"), ("IBM Plex Mono", "IBMPlexMono-Medium.ttf", "500")]) if os.path.isdir(FD) else ""
M = R["monarchs"]; H = R["headline"]
html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{ff}
body{{margin:0;width:1200px;height:630px;background:radial-gradient(circle at 80% 45%,#FBF6EA 0%,#F3EBD8 55%,#E8DCC0 100%);color:#2A2218;overflow:hidden;position:relative;font-family:'Source Serif 4',Georgia,serif}}
.k{{position:absolute;left:66px;top:58px;font:500 15px/1 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:#6E6250;display:flex;gap:12px;align-items:center}}
.k b{{background:#24427A;color:#F6F0E1;padding:7px 9px;font-weight:500}}
h1{{position:absolute;left:60px;top:96px;margin:0;font:900 88px/.92 Fraunces,Georgia,serif;letter-spacing:-.02em;width:660px}}
h1 em{{font-style:normal;color:#B8862B}}
p{{position:absolute;left:66px;top:318px;width:600px;margin:0;font-size:25px;line-height:1.38}}
p b.j{{color:#24427A}} p b.e{{color:#A8720F}}
.f{{position:absolute;left:66px;bottom:40px;font:400 14px/1 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:#6E6250}}
svg{{position:absolute;right:-10px;top:10px;-webkit-mask-image:radial-gradient(ellipse 52% 54% at 55% 50%,#000 72%,transparent 100%);mask-image:radial-gradient(ellipse 52% 54% at 55% 50%,#000 72%,transparent 100%)}}
</style></head><body>
<div class="k"><b>Data study</b><span>Royal itineraries · 1154 to 1603</span></div>
<h1>Governing on the <em>move</em></h1>
<p>Where England's kings slept. <b class="j">King John</b> moved on {M['John']['moved_share'] * 100:.0f}% of the days we can follow him; <b class="e">Edward I</b> on {M['Edward I']['moved_share'] * 100:.0f}%, and spent {H['edward_westminster_nights']:,} nights at Westminster.</p>
<div class="f">Dr Tristan Hotham · Independent researcher</div>
<svg width="{Ww:.0f}" height="{Hh}" viewBox="0 0 {Ww:.0f} {Hh}"><path d="{land}" fill="#E6DAC0" stroke="#CBBA96" stroke-width="1"/>{dots}</svg>
</body></html>"""
os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
tmp = os.path.join(ROOT, "work", "header.html"); open(tmp, "w").write(html)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 630})
    pg.goto("file://" + os.path.abspath(tmp)); pg.wait_for_timeout(600)
    pg.screenshot(path=os.path.join(ROOT, "header.png")); b.close()
os.remove(tmp)
print("header.png written", round(Ww), "px map")
