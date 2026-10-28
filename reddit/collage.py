"""r/dataisbeautiful collage for Governing on the Move (royal-itineraries). Run from this folder: python3 collage.py
Every number is read from ../data/results.json and the data files in ../data/."""
import csv, json, math, os
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon
from matplotlib.collections import LineCollection

F = os.environ.get("FONT_DIR", "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts/")
for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf", "SourceSerif4-Semibold.ttf", "SourceSerif4-It.ttf"]:
    fm.fontManager.addfont(os.path.join(F, f))
DISP = fm.FontProperties(fname=os.path.join(F, "FrauncesVar.ttf"), weight=900)
SER = "Source Serif 4"; MONO = "IBM Plex Mono"
BG = "#F6F0E1"; FG = "#2A2218"; MUT = "#6E6250"; LAND = "#EADFC6"; COAST = "#CDBB95"; BLUE = "#24427A"; GOLD = "#B07D1A"; RED = "#9E2B40"
ENG, WAL, SCO, FRA, LOW = "#D2AE5E", "#9E2B40", "#24427A", "#7D9CC2", "#7A6A9A"
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
NI = list(csv.DictReader(open(os.path.join(ROOT, "data", "nights.csv"))))
YR = list(csv.DictReader(open(os.path.join(ROOT, "data", "years.csv"))))
LANDR = json.load(open(os.path.join(ROOT, "work", "land.json")))
K = math.cos(math.radians(50))
M = R["monarchs"]; H = R["headline"]
pct = lambda v: f"{v * 100:.0f}%"


def jd(s):
    y, m, d = int(s[:4]), int(s[5:7]), int(s[8:10]); a = (14 - m) // 12; y2 = y + 4800 - a; m2 = m + 12 * a - 3
    return d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - 32083


def hav(a, b, c, d):
    p = math.pi / 180; x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


def legs(mon):
    n = sorted([r for r in NI if r["monarch"] == mon], key=lambda r: r["date"]); out = []
    for a, b in zip(n, n[1:]):
        la, lo, lb, lob = float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"])
        g = jd(b["date"]) - jd(a["date"]); d = hav(la, lo, lb, lob)
        if g <= 7 and 0.5 < d and d / g <= 100: out.append([(lo * K, la), (lob * K, lb)])
    return out


fig = plt.figure(figsize=(12, 15), dpi=200, facecolor=BG)
fig.text(0.04, 0.968, "Where did England's kings sleep?", fontproperties=DISP, fontsize=40, color=FG, va="top")
fig.text(0.04, 0.917, "Medieval government had no capital: it travelled with the king. Every recorded journey of King John (1199 to 1216)\n"
         "and Edward I (1272 to 1307), parsed night by night from the itineraries printed by Hardy (1835) and Gough (1900).",
         family=SER, fontsize=14, color=FG, va="top", linespacing=1.4)

# hero map: every leg between recorded nights
ax = fig.add_axes([0.0, 0.335, 0.6, 0.51])
for ring in LANDR:
    ax.add_patch(Polygon([(x * K, y) for x, y in ring], closed=True, fc=LAND, ec=COAST, lw=.6, zorder=0))
ax.add_collection(LineCollection(legs("Edward I"), colors=GOLD, linewidths=.9, alpha=.32, zorder=2))
ax.add_collection(LineCollection(legs("John"), colors=BLUE, linewidths=.9, alpha=.30, zorder=3))
for mon, col, z in (("Edward I", GOLD, 4), ("John", BLUE, 5)):
    rows = [r for r in csv.DictReader(open(os.path.join(ROOT, "data", "places.csv"))) if r["monarch"] == mon and int(r["nights"]) >= 25]
    ax.scatter([float(r["lon"]) * K for r in rows], [float(r["lat"]) for r in rows], s=[int(r["nights"]) * (0.55 if mon == "Edward I" else 1.6) for r in rows],
               facecolor=col, alpha=.28, edgecolor=col, lw=.8, zorder=z)
LAB = {"Westminster": (12, 10, "left", GOLD), "Rouen": (12, 0, "left", BLUE), "Winchester": (-14, -14, "right", BLUE), "Rhuddlan": (-8, 14, "right", GOLD),
       "Lanercost Priory": (10, 6, "left", GOLD), "Stirling": (-10, 8, "right", GOLD), "Chinon": (10, 0, "left", BLUE), "Ghent": (8, 8, "left", GOLD),
       "Woodstock": (-12, 8, "right", BLUE)}
PL = {r["place"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data", "places.csv"))) if int(r["nights"]) > 0}
for nm, (dx, dy, ha, col) in LAB.items():
    r = [q for q in csv.DictReader(open(os.path.join(ROOT, "data", "places.csv"))) if q["place"] == nm and q["monarch"] == ("John" if col == BLUE else "Edward I")][0]
    ax.annotate(f"{nm.replace(' Priory', '')} {r['nights']}", (float(r["lon"]) * K, float(r["lat"])), xytext=(dx, dy), textcoords="offset points", ha=ha, va="center",
                family=MONO, fontsize=10.5, color=col, zorder=7, bbox=dict(fc=BG, ec="none", alpha=.85, pad=1.2))
ax.set_xlim(-6.4 * K, 4.4 * K); ax.set_ylim(43.3, 56.6); ax.set_aspect("equal"); ax.axis("off")
ax.text(0.03, 0.035, "Lines: moves between recorded nights no more than a week apart.\nCircles and labels: nights at the most visited places.",
        transform=ax.transAxes, family=MONO, fontsize=9.5, color=MUT, va="bottom", linespacing=1.4)
fig.patches.append(matplotlib.patches.Rectangle((0.04, 0.852), 0.03, 0.005, transform=fig.transFigure, fc=BLUE))
fig.text(0.075, 0.8545, f"King John: {M['John']['nights']:,} nights", va="center", family=MONO, fontsize=11, color=FG)
fig.patches.append(matplotlib.patches.Rectangle((0.33, 0.852), 0.03, 0.005, transform=fig.transFigure, fc=GOLD))
fig.text(0.365, 0.8545, f"Edward I: {M['Edward I']['nights']:,} nights", va="center", family=MONO, fontsize=11, color=FG)

# headline numbers
tx = fig.add_axes([0.62, 0.355, 0.36, 0.495]); tx.axis("off")
notes = [(f"{M['John']['distinct_night_places']}", BLUE, f"places where King John spent a night,\nmoving on {pct(M['John']['moved_share'])} of the days I can follow\nhim. Edward I: {pct(M['Edward I']['moved_share'])}."),
         (f"{M['John']['km_per_year_median']:,.0f} km", BLUE, f"ridden by John in a typical year, in\nstraight lines between nights. Edward I:\n{M['Edward I']['km_per_year_median']:,.0f} km."),
         (f"{pct(R['john']['continent_1199_1203'])} to {pct(R['john']['continent_1204_1216'])}", BLUE, f"John's days spent in France before\nand after Normandy fell in 1204.\nRouen was his top stop ({H['john_rouen_nights']} nights)."),
         (f"{H['edward_westminster_nights']}", GOLD, f"nights at Westminster for Edward I,\n{pct(H['edward_westminster_share'])} of the total. John managed\n{H['john_westminster_nights']}: a capital in the making.")]
for (big, col, small), y in zip(notes, [1.0, 0.75, 0.5, 0.25]):
    tx.text(0, y, big, fontproperties=DISP, fontsize=36, color=col, va="top", transform=tx.transAxes)
    tx.text(0, y - 0.085, small, family=SER, fontsize=12.5, color=FG, va="top", transform=tx.transAxes, linespacing=1.3)

# small multiple 1: Edward I by country and year
fig.text(0.04, 0.318, "EDWARD I'S NIGHTS BY COUNTRY, PER YEAR: HIS WARS", family=MONO, fontsize=10.5, color=MUT)
bx = fig.add_axes([0.06, 0.145, 0.52, 0.143], facecolor=BG)
rows = [r for r in YR if r["monarch"] == "Edward I"]; xs = [int(r["year"]) for r in rows]; bot = np.zeros(len(rows))
for key, col, lab in (("england", ENG, "England"), ("wales", WAL, "Wales"), ("scotland", SCO, "Scotland"), ("france", FRA, "France"), ("low_countries", LOW, "Flanders")):
    v = np.array([int(r[key]) for r in rows]); bx.bar(xs, v, bottom=bot, color=col, width=.85, label=lab); bot += v
for x, t, y in ((1283, "Wales", 245), (1287.5, "Gascony", 185), (1297.5, "Flanders", 172), (1303.5, "Scotland", 215)):
    bx.text(x, y, t, ha="center", family=MONO, fontsize=10, color=FG)
bx.set_ylim(0, 270); bx.set_xlim(1272, 1308)
for sp in ("top", "right"): bx.spines[sp].set_visible(False)
bx.spines["left"].set_color(MUT); bx.spines["bottom"].set_color(MUT)
bx.tick_params(labelsize=10, colors=FG); [t.set_family(MONO) for t in bx.get_xticklabels() + bx.get_yticklabels()]
bx.legend(ncol=5, fontsize=9.5, frameon=False, loc="upper left", bbox_to_anchor=(0, 1.2), prop=dict(family=MONO, size=9.5), handlelength=1, columnspacing=1)

# small multiple 2: Elizabeth 1561
fig.text(0.64, 0.318, "ELIZABETH I'S PROGRESS OF 1561", family=MONO, fontsize=10.5, color=MUT)
cx = fig.add_axes([0.63, 0.15, 0.35, 0.155], facecolor=BG)
KE = math.cos(math.radians(52))
for ring in LANDR:
    cx.add_patch(Polygon([(x * KE, y) for x, y in ring], closed=True, fc=LAND, ec=COAST, lw=.5))
E = sorted([r for r in NI if r["monarch"] == "Elizabeth I"], key=lambda r: r["date"])
cx.plot([float(r["lon"]) * KE for r in E], [float(r["lat"]) for r in E], color=RED, lw=1.8)
for nm, (dx, dy) in (("Charterhouse (London)", (6, -9)), ("Colchester", (-14, 8)), ("Ipswich", (6, 4)), ("Castle Hedingham", (-6, 8))):
    r = [q for q in E if q["place"] == nm][0]
    cx.scatter([float(r["lon"]) * KE], [float(r["lat"])], s=22, color=RED, zorder=3)
    cx.annotate(nm.split(" (")[0], (float(r["lon"]) * KE, float(r["lat"])), xytext=(dx, dy), textcoords="offset points", family=MONO, fontsize=9.5,
                color=FG, ha="right" if dx < 0 else "left")
cx.set_xlim(-0.35 * KE, 1.45 * KE); cx.set_ylim(51.42, 52.2); cx.set_aspect("equal"); cx.set_xticks([]); cx.set_yticks([])
for sp in cx.spines.values(): sp.set_color(COAST)
fig.text(0.64, 0.138, f"{R['elizabeth']['days_1561']} days, {R['elizabeth']['places_1561']} places, {R['elizabeth']['km_1561']:.0f} km in all: by the 1500s the\nprogress was a summer tour, not a government on the road.",
         family=SER, fontsize=11, color=FG, va="top", linespacing=1.3)

# footer
fig.text(0.04, 0.101, f"Checked against fixed points such as John at Runnymede on 15 June 1215 and Edward I at Rhuddlan 1277, Berwick 1296 and Caerlaverock 1300\n"
         f"({R['checks_passed']} of {R['checks_n']} recovered). Most days have no record: {pct(R['coverage']['John']['share_days_with_point'])} of John's reign and "
         f"{pct(R['coverage']['Edward I']['share_days_with_point'])} of Edward's are placed. Straight-line distances;\n"
         "OCR and identification errors remain, and outliers far from neighbouring records were removed.",
         family=MONO, fontsize=8.8, color=MUT, va="top", linespacing=1.3)
fig.text(0.04, 0.006, "Sources: T. D. Hardy, Itinerary of King John (1835); H. Gough, Itinerary of King Edward the First (1900); J. Nichols, Progresses of\n"
         "Queen Elizabeth (1823): public domain, Internet Archive OCR. Places: OS Open Names (OGL v3, Crown copyright 2026), GeoNames (CC BY 4.0),\n"
         "Wikidata (CC0); Natural Earth. Analysis and chart: Tristan Hotham, with Python and matplotlib.",
         family=MONO, fontsize=8.8, color=MUT, va="bottom", linespacing=1.3)
out = os.path.join(HERE, "where_did_englands_kings_sleep.png")
fig.savefig(out, dpi=200, facecolor=BG)
print("written", out)
