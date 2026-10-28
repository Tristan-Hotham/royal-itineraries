"""Step 11. Build the paper PDF: fill paper_template.tex with numbers and tables from data/results.json,
write release/paper/Hotham_Royal_Itineraries.tex and compile it with xelatex (figures from 10_figures.py).
Run: python3 11_paper.py
"""
import json, os, re, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
OUT = os.path.join(ROOT, "release", "paper"); NAME = "Hotham_Royal_Itineraries"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
WORDS = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split() + \
        ["twenty-one", "twenty-two", "twenty-three", "twenty-four", "twenty-five", "twenty-six", "twenty-seven", "twenty-eight", "twenty-nine", "thirty"] + \
        [None] * 19 + ["forty-nine"]


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f == "int": return f"{int(round(float(v))):,}"
    if f == "pct0": return f"{float(v) * 100:.0f}\\%"
    if f == "pct1": return f"{float(v) * 100:.1f}\\%"
    if f == "f1": return f"{float(v):.1f}"
    if f == "km0": return f"{float(v):.0f}"
    if f == "month": return MONTHS[int(v) - 1]
    if f == "words": return WORDS[int(v)] if int(v) < len(WORDS) and WORDS[int(v)] else f"{int(v):,}"
    if f == "raw" and re.match(r"^\d{4}-\d\d-\d\d$", str(v)):
        y, m, d = str(v).split("-"); return f"{int(d)} {MONTHS[int(m) - 1]} {y}"
    return str(v)


def sub(m):
    path, _, f = m.group(1).partition("|")
    return fmt(get(path.strip()), f.strip() or "raw")


pc = lambda v: f"{v * 100:.0f}\\%" if v is not None else ""
C = R["coverage"]; rows = ""
for mon, src in (("Henry II", "Eyton 1878"), ("John", "Hardy 1835"), ("Edward I", "Gough 1900"), ("Elizabeth I", "Nichols 1823")):
    x = C[mon]
    rows += (f"{mon} & {src} & {x['entries']:,} & {pc(x['share_point'])} & {x['days_with_entry']:,} & "
             f"{(x.get('reign_days') and format(x['reign_days'], ',')) or '1561 only'} & {pc(x.get('share_days_with_entry')) or ''} & {R['monarchs'][mon]['distinct_night_places']:,}\\\\\n")
TC = ("\\begin{table}[tbp]\\centering\\small\\caption{What the four sources give. Entries: place-days parsed. Placed: share of entries matched to a point. "
      "Days: days with at least one entry. Places: distinct night places after flags.}\\label{tab:coverage}"
      "\\begin{tabular}{llrrrrrr}\\toprule Monarch & Source & Entries & Placed & Days & Reign days & Share & Places\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
rows = ""
for k in R["checks"]:
    rows += f"{k['check']} & {k['date']}{(' $\\pm$' + str(k['window_days'])) if k['window_days'] else ''} & {k['found']} & {k['km']} & {'pass' if k['passed'] else 'fail'}\\\\\n"
TK = ("\\begin{table}[tbp]\\centering\\footnotesize\\caption{Checks against fixed points. Pass: a placed record within the stated distance of the target in the window "
      "of days (10 km for John, 20 to 60 km for Edward I's campaigns). Event dates from the Wikipedia articles on John and Edward I.}\\label{tab:checks}"
      "\\begin{tabular}{p{5.2cm}lp{4.4cm}rl}\\toprule Check & Date & Nearest placed record & km & Result\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
M = R["monarchs"]; J, E = M["John"], M["Edward I"]
rows = ""
for lab, a, b in (("Placed nights", f"{J['nights']:,}", f"{E['nights']:,}"), ("Distinct night places", f"{J['distinct_night_places']:,}", f"{E['distinct_night_places']:,}"),
                  ("Consecutive recorded days", f"{J['consecutive_pairs']:,}", f"{E['consecutive_pairs']:,}"),
                  ("Moved on (share of consecutive days)", pc(J["moved_share"]), pc(E["moved_share"])),
                  ("Median move (km)", f"{J['km_per_moving_day_median']:.0f}", f"{E['km_per_moving_day_median']:.0f}"),
                  ("90th percentile move (km)", f"{J['km_per_moving_day_p90']:.0f}", f"{E['km_per_moving_day_p90']:.0f}"),
                  ("Mean stay (nights)", f"{J['stay_mean_nights']:.1f}", f"{E['stay_mean_nights']:.1f}"),
                  ("Median km per well-recorded year", f"{J['km_per_year_median']:,.0f}", f"{E['km_per_year_median']:,.0f}"),
                  ("Median places per well-recorded year", f"{J['places_per_year_median']:.1f}", f"{E['places_per_year_median']:.1f}"),
                  ("Nights within 5 km of Westminster", pc(J["london_share"]), pc(E["london_share"])),
                  ("Nights in England within 10 km of a royal forest", pc(J["forest_share"]), pc(E["forest_share"]))):
    rows += f"{lab} & {a} & {b}\\\\\n"
TM = ("\\begin{table}[tbp]\\centering\\small\\caption{How John and Edward I travelled. A move is more than 3 km between nights on consecutive recorded days. "
      "Well-recorded years have at least 150 placed nights.}\\label{tab:compare}"
      "\\begin{tabular}{lrr}\\toprule & John & Edward I\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
s = open(os.path.join(HERE, "paper_template.tex")).read()
s = s.replace("{{TABLE_COVERAGE}}", TC).replace("{{TABLE_CHECKS}}", TK).replace("{{TABLE_COMPARE}}", TM)
s = re.sub(r"\{\{(.+?)\}\}", sub, s)
assert "{{" not in s
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, NAME + ".tex"), "w").write(s)
for _ in range(2):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", NAME + ".tex"], cwd=OUT, capture_output=True, text=True)
print(r.stdout[-500:])
for ext in (".aux", ".log", ".out"):
    p = os.path.join(OUT, NAME + ext)
    if os.path.exists(p): os.remove(p)
shutil.move(os.path.join(OUT, NAME + ".pdf"), os.path.join(ROOT, "release", NAME + ".pdf"))
