"""Step 10. Static figures for the paper (release/paper/f_*.png) and the blog (release/blog/b_*.png, 1520 px wide).
Drawn with matplotlib from data/*.csv and data/results.json; coastline from work/land.json (Natural Earth).
Fonts: FONT_DIR with SourceSerif4 and IBM Plex Mono (as for the header); falls back to defaults.
Run: python3 10_figures.py
"""
import csv, json, math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
FD = os.environ.get("FONT_DIR", "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts")
for f in ("SourceSerif4-Regular.ttf", "SourceSerif4-Semibold.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf"):
    p = os.path.join(FD, f)
    if os.path.exists(p): fm.fontManager.addfont(p)
SER, MONO = "Source Serif 4", "IBM Plex Mono"
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
PL = list(csv.DictReader(open(os.path.join(ROOT, "data", "places.csv"))))
YR = list(csv.DictReader(open(os.path.join(ROOT, "data", "years.csv"))))
NI = list(csv.DictReader(open(os.path.join(ROOT, "data", "nights.csv"))))
ST = list(csv.DictReader(open(os.path.join(ROOT, "data", "stays.csv"))))
LAND = json.load(open(os.path.join(ROOT, "work", "land.json")))
C = dict(John="#24427A", Edw="#A8720F", Hen="#3D6E4A", Eliz="#9E2B40", England="#C9A04A", Wales="#9E2B40", Scotland="#24427A",
         France="#7D9CC2", Low="#7A6A9A", fg="#2A2218", muted="#6E6250", rule="#DCD0B6", land="#E9DFC8", coast="#C9B994", forest="#4F7A3A")
PAPER = os.path.join(ROOT, "release", "paper"); BLOG = os.path.join(ROOT, "release", "blog")
os.makedirs(PAPER, exist_ok=True); os.makedirs(BLOG, exist_ok=True)


def style(mode):
    big = mode == "blog"
    plt.rcParams.update({"font.family": SER, "font.size": 15 if big else 9, "axes.edgecolor": C["muted"], "axes.labelcolor": C["fg"],
                         "xtick.color": C["muted"], "ytick.color": C["muted"], "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titlesize": 15 if big else 9.5, "legend.frameon": False, "figure.facecolor": "#FBF8F1" if big else "white",
                         "axes.facecolor": "#FBF8F1" if big else "white", "savefig.facecolor": "#FBF8F1" if big else "white"})


def save(fig, name, mode):
    if mode == "blog":
        fig.savefig(os.path.join(BLOG, f"b_{name}.png"), dpi=152)
    else:
        fig.savefig(os.path.join(PAPER, f"f_{name}.png"), dpi=220)
    plt.close(fig)


def land(ax, k):
    patches = [Polygon([(x * k, y) for x, y in ring], closed=True) for ring in LAND]
    ax.add_collection(PatchCollection(patches, facecolor=C["land"], edgecolor=C["coast"], linewidth=.5, zorder=0))


def mapfig(mode):
    style(mode)
    w = 10 if mode == "blog" else 6.6
    fig, axs = plt.subplots(1, 2, figsize=(w, w * .78))
    k = math.cos(math.radians(50))
    for ax, mon, col, lab in ((axs[0], "John", C["John"], "King John, 1199 to 1216"), (axs[1], "Edward I", C["Edw"], "Edward I, 1272 to 1307")):
        land(ax, k)
        rows = sorted([r for r in PL if r["monarch"] == mon and int(r["nights"]) > 0], key=lambda r: -int(r["nights"]))
        s = [(4 if mode == "blog" else 1.6) * int(r["nights"]) ** .9 for r in rows]
        ax.scatter([float(r["lon"]) * k for r in rows], [float(r["lat"]) for r in rows], s=s, c=col, alpha=.35, edgecolors=col, linewidths=.5, zorder=2)
        OFF = {"Westminster": (-40, 22), "Windsor": (-62, -14), "Lambeth": (12, -2), "Marlborough": (-96, -4), "Woodstock": (-80, 6), "Winchester": (-60, -18),
               "Rhuddlan": (8, 6), "Conwy": (-40, 10), "Canterbury": (4, -16), "Lanercost Priory": (6, 4), "Rouen": (8, -6), "Orival": (8, 6)}
        for r in rows[:6]:
            dx, dy = OFF.get(r["place"], (6, 4))
            if mode != "blog": dx, dy = dx * .6, dy * .6
            ax.annotate(r["place"].replace(" Priory", "").replace("Berwick-Upon-Tweed", "Berwick"), (float(r["lon"]) * k, float(r["lat"])),
                        xytext=(dx, dy), textcoords="offset points", fontsize=11 if mode == "blog" else 6.5, family=MONO, color=C["fg"], zorder=3,
                        bbox=dict(boxstyle="round,pad=.15", fc="#FBF8F1", ec="none", alpha=.75))
        ax.set_xlim(-8.2 * k, 3.6 * k); ax.set_ylim(43.2, 58.0); ax.set_aspect(1)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values(): sp.set_visible(False)
        ax.text(.02, .985, lab, transform=ax.transAxes, fontsize=14 if mode == "blog" else 8.5, color=col, va="top", weight="semibold")
        ax.text(.02, .94, f"{R['monarchs'][mon]['nights']:,} nights at {R['monarchs'][mon]['distinct_night_places']:,} places", transform=ax.transAxes,
                fontsize=11 if mode == "blog" else 6.5, family=MONO, color=C["muted"], va="top")
    fig.subplots_adjust(left=.01, right=.99, top=.99, bottom=.02, wspace=.02)
    save(fig, "map", mode)


def topfig(mode):
    style(mode)
    w = 10 if mode == "blog" else 6.6
    fig, axs = plt.subplots(1, 2, figsize=(w, w * .55))
    for ax, mon, col in ((axs[0], "John", C["John"]), (axs[1], "Edward I", C["Edw"])):
        t = R["monarchs"][mon]["top_places"][:12][::-1]
        names = [x["place"].replace("Freemantle (near Kingsclere)", "Freemantle").replace("Berwick-Upon-Tweed", "Berwick") for x in t]
        ax.barh(names, [x["nights"] for x in t], color=col, height=.72)
        for i, x in enumerate(t):
            ax.text(x["nights"] + max(y["nights"] for y in t) * .01, i, str(x["nights"]), va="center", fontsize=11 if mode == "blog" else 6.5, family=MONO, color=C["muted"])
        ax.set_xlabel("Nights", fontsize=12 if mode == "blog" else 7.5)
        ax.tick_params(axis="y", labelsize=12 if mode == "blog" else 7); ax.tick_params(axis="x", labelsize=10 if mode == "blog" else 6.5)
        ax.text(0, 1.02, mon, transform=ax.transAxes, color=col, weight="semibold", fontsize=14 if mode == "blog" else 8.5)
    fig.tight_layout()
    save(fig, "top", mode)


def kmfig(mode):
    style(mode)
    w = 10 if mode == "blog" else 6.6
    fig, axs = plt.subplots(1, 2, figsize=(w, w * .42), gridspec_kw=dict(width_ratios=[1, 2.1]))
    for mon, col in (("John", C["John"]), ("Edward I", C["Edw"])):
        rows = [r for r in YR if r["monarch"] == mon and int(r["nights"]) >= 30]
        ax = axs[0] if mon == "John" else axs[1]
        xs = [int(r["year"]) for r in rows]; ys = [int(r["km"]) for r in rows]
        ax.plot(xs, ys, color=col, lw=2)
        ax.scatter([x for x, r in zip(xs, rows) if int(r["nights"]) >= 150], [y for y, r in zip(ys, rows) if int(r["nights"]) >= 150], color=col, s=18, zorder=3)
        ax.scatter([x for x, r in zip(xs, rows) if int(r["nights"]) < 150], [y for y, r in zip(ys, rows) if int(r["nights"]) < 150], facecolor="white", edgecolor=col, s=18, zorder=3)
        ax.set_ylim(0, 8500); ax.grid(axis="y", color=C["rule"], lw=.6)
        ax.text(.02, .97, f"{mon}: median {R['monarchs'][mon]['km_per_year_median']:,.0f} km a year", transform=ax.transAxes, color=col, va="top",
                fontsize=12 if mode == "blog" else 7.5, weight="semibold")
        ax.tick_params(labelsize=10 if mode == "blog" else 6.5)
    axs[0].set_ylabel("Straight-line km per year", fontsize=12 if mode == "blog" else 7.5)
    axs[0].axvline(1204, color=C["muted"], ls=":", lw=1); axs[0].text(1204.3, 300, "1204", fontsize=10 if mode == "blog" else 6.5, family=MONO, color=C["muted"])
    axs[1].set_yticklabels([])
    fig.tight_layout()
    save(fig, "km", mode)


def warfig(mode):
    style(mode)
    w = 10 if mode == "blog" else 6.6
    fig, ax = plt.subplots(figsize=(w, w * .42))
    rows = [r for r in YR if r["monarch"] == "Edward I"]
    xs = [int(r["year"]) for r in rows]; bottom = [0] * len(rows)
    for key, lab, col in (("england", "England", C["England"]), ("wales", "Wales", C["Wales"]), ("scotland", "Scotland", C["Scotland"]),
                          ("france", "France", C["France"]), ("low_countries", "Low Countries", C["Low"])):
        v = [int(r[key]) for r in rows]
        ax.bar(xs, v, bottom=bottom, color=col, width=.85, label=lab)
        bottom = [a + b for a, b in zip(bottom, v)]
    ax.set_ylabel("Placed nights", fontsize=12 if mode == "blog" else 7.5)
    ax.legend(ncol=5, fontsize=11 if mode == "blog" else 6.5, loc="upper center", bbox_to_anchor=(.5, 1.13))
    for x, t, yy in ((1277, "Wales", 262), (1283, "Wales", 245), (1287.5, "Gascony", 180), (1297.5, "Flanders", 175), (1303.5, "Scotland", 215)):
        ax.text(x, yy, t, ha="center", fontsize=10 if mode == "blog" else 6.2, family=MONO, color=C["muted"])
    ax.set_ylim(0, 290); ax.tick_params(labelsize=10 if mode == "blog" else 6.5); ax.grid(axis="y", color=C["rule"], lw=.6); ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "war", mode)


def contfig(mode):
    style(mode)
    w = 10 if mode == "blog" else 6.6
    fig, ax = plt.subplots(figsize=(w, w * .36))
    rows = [r for r in YR if r["monarch"] == "John" and int(r["nights"]) >= 30]
    xs = [int(r["year"]) for r in rows]; ys = [(int(r["france"]) + int(r["low_countries"])) / int(r["nights"]) * 100 for r in rows]
    ax.plot(xs, ys, color=C["John"], lw=2.2, marker="o", ms=5)
    ax.axvline(1204, color=C["muted"], ls=":", lw=1)
    ax.text(1204.15, 92, "Rouen falls, 1204", fontsize=10 if mode == "blog" else 6.5, family=MONO, color=C["muted"])
    for x, t in ((1206, "Poitou"), (1214, "Poitou")):
        y = ys[xs.index(x)]
        ax.annotate(t, (x, y), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=10 if mode == "blog" else 6.5, family=MONO, color=C["muted"])
    ax.set_xticks(range(1200, 1217, 2))
    ax.set_ylim(0, 105); ax.set_ylabel("% of nights abroad", fontsize=12 if mode == "blog" else 7.5)
    ax.tick_params(labelsize=10 if mode == "blog" else 6.5); ax.grid(axis="y", color=C["rule"], lw=.6)
    fig.tight_layout()
    save(fig, "continent", mode)


def monthfig(mode):
    style(mode)
    w = 10 if mode == "blog" else 6.6
    fig, axs = plt.subplots(1, 2, figsize=(w, w * .36), sharey=True)
    mlab = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    for ax, key, title in ((axs[0], "london_by_month", "Within 5 km of Westminster"), (axs[1], "forest_by_month", "Within 10 km of a royal forest (England)")):
        for mon, col in (("John", C["John"]), ("Edward I", C["Edw"])):
            v = [R["monarchs"][mon][key][str(m)] * 100 for m in range(1, 13)]
            ax.plot(range(1, 13), v, color=col, lw=2, marker="o", ms=4, label=mon)
        ax.set_xticks(range(1, 13)); ax.set_xticklabels(mlab); ax.tick_params(labelsize=10 if mode == "blog" else 6.5)
        ax.set_title(title, loc="left", fontsize=12 if mode == "blog" else 7.5)
        ax.grid(axis="y", color=C["rule"], lw=.6)
    axs[0].set_ylabel("% of nights", fontsize=12 if mode == "blog" else 7.5); axs[0].legend(fontsize=10 if mode == "blog" else 6.5)
    fig.tight_layout()
    save(fig, "months", mode)


def elizfig(mode):
    style(mode)
    w = 10 if mode == "blog" else 6.6
    fig, axs = plt.subplots(1, 2, figsize=(w, w * .44), gridspec_kw=dict(width_ratios=[1.25, 1]))
    k = math.cos(math.radians(52))
    E = [r for r in NI if r["monarch"] == "Elizabeth I"]
    pref = [r for r in ST if r["monarch"] == "Elizabeth I" and r["quality"].startswith("preface") and r["lat"]]
    for ax, ext in ((axs[0], (-3.2, 1.6, 50.6, 53.0)), (axs[1], (-0.4, 1.5, 51.4, 52.15))):
        land(ax, k)
        ax.set_xlim(ext[0] * k, ext[1] * k); ax.set_ylim(ext[2], ext[3]); ax.set_aspect(1); ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values(): sp.set_color(C["rule"])
    ax = axs[0]
    ax.scatter([float(r["lon"]) * k for r in pref], [float(r["lat"]) for r in pref], s=26 if mode == "blog" else 10, facecolor="white", edgecolor=C["Edw"], lw=1.1, zorder=3)
    yrs = {}
    for r in pref: yrs.setdefault(r["place"], (float(r["lon"]) * k, float(r["lat"]), []))[2].append(r["date"][:4])
    POFF = {"Kenilworth": (5, 4), "Coventry": (5, 8), "Oxford": (5, 3), "Sudeley Castle": (-70, 4), "Woodstock": (5, -10)}
    for nm in ("Kenilworth", "Bristol", "Longleat", "Cowdray", "Elvetham", "Oxford", "Cambridge", "Canterbury", "Tilbury", "Sudeley Castle"):
        if nm in yrs:
            x, y, ys = yrs[nm]; dx, dy = POFF.get(nm, (5, 3))
            if mode != "blog": dx, dy = dx * .55, dy * .55
            ax.annotate(f"{nm.replace(' Castle', '')} {', '.join(sorted(set(ys)))}", (x, y), xytext=(dx, dy), textcoords="offset points",
                        fontsize=9 if mode == "blog" else 5.5, family=MONO, color=C["fg"])
    ax.text(.02, .98, "Progresses named in Nichols's preface, 1559 to 1602", transform=ax.transAxes, va="top", fontsize=11 if mode == "blog" else 6.8, color=C["Edw"], weight="semibold")
    ax = axs[1]
    xs = [float(r["lon"]) * k for r in E]; ys = [float(r["lat"]) for r in E]
    ax.plot(xs, ys, color=C["Eliz"], lw=1.6, zorder=2)
    seen = {}
    for r in E: seen.setdefault(r["place"], (float(r["lon"]) * k, float(r["lat"]), 0)); seen[r["place"]] = (seen[r["place"]][0], seen[r["place"]][1], seen[r["place"]][2] + 1)
    for nm, (x, y, n) in seen.items():
        ax.scatter([x], [y], s=(14 if mode == "blog" else 6) * n, color=C["Eliz"], alpha=.5, zorder=3)
        short = nm.split(" (")[0].replace("New Hall, Boreham", "New Hall").replace("Strand", "Strand").replace("Smallbridge", "Smallbridge")
        EO = {"Pyrgo Park": (10, -26), "Strand (Somerset House, London)": (4, -11), "Smallbridge (Bures)": (-20, 9), "Ingatestone": (8, -16), "Colchester": (6, -20),
              "Loughton Hall": (-80, 6), "Havering Palace": (-18, 12), "Castle Hedingham": (-90, 10)}
        ox, oy = EO.get(nm, (4, 4)); f_ = 1 if mode == "blog" else .55
        ax.annotate(short, (x, y), xytext=(ox * f_, oy * f_), textcoords="offset points",
                    fontsize=9 if mode == "blog" else 5.5, family=MONO, color=C["fg"])
    ax.text(.02, .98, f"The 1561 progress, {R['elizabeth']['days_1561']} days", transform=ax.transAxes, va="top", fontsize=11 if mode == "blog" else 6.8, color=C["Eliz"], weight="semibold")
    fig.tight_layout()
    save(fig, "elizabeth", mode)


for mode in ("paper", "blog"):
    for f in (mapfig, topfig, kmfig, warfig, contfig, monthfig, elizfig):
        f(mode)
print(sorted(os.listdir(PAPER)), sorted(os.listdir(BLOG)))
