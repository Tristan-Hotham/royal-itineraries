"""Step 6. All the numbers: coverage, checks against fixed points, nights per place, distance and speed,
seasons, Christmas courts, royal forests, the geography of Edward I's wars and the pull of Westminster.

Definitions
  * A "stay" is one place on one day in an itinerary. A day may have two or more places (the king moved).
  * The "night" place of a day is the last place on the day's path, the path running from the place
    nearest the previous night's place (greedy nearest neighbour). Nights per place counts these.
  * Distances are great-circle distances between places, in km, summed along the daily path, only between
    records no more than 7 days apart (a longer gap hides the route). They are straight lines, so true road
    distances were longer; sea crossings count as straight lines too.
  * Country: from GeoNames country codes for continental and Irish places, otherwise from the nearest OS
    Open Names settlement (England, Wales, Scotland).
  * Royal forests: the forests listed in the Wikipedia article "Royal forest" (England table), placed at a
    named OS Open Names wood or forest feature, or the Wikipedia article's coordinates, or the OS settlement
    they are named after (see data/royal_forests.csv). A stay is "in or near a royal forest" when it lies
    within 10 km of one of these points: a crude proxy, since forests had wide and changing bounds.
Inputs: ../data/stays_geocoded.csv, ../data/raw_henry_christmas.csv, OS Open Names, Wikipedia bundle.
Outputs: ../data/results.json, ../data/nights.csv, ../data/places.csv, ../data/years.csv,
         ../data/royal_forests.csv, ../data/checks.csv, ../data/page_data.json
Run: python3 06_analysis.py
"""
import csv, datetime as dt, gzip, json, math, os, re, statistics as st
from collections import Counter, defaultdict
import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, ".."); HIST = os.path.join(ROOT, "..")
DATA = os.path.join(ROOT, "data")


def hav(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(min(1, math.sqrt(x)))


def D(s):
    """Julian-calendar ISO date string to Julian day number (the itineraries use the Julian calendar)."""
    y, m, d = int(s[:4]), int(s[5:7]), int(s[8:10])
    a = (14 - m) // 12; y2 = y + 4800 - a; m2 = m + 12 * a - 3
    return d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - 32083


def J2S(j):
    """Julian day number back to a Julian-calendar ISO date string."""
    c = j + 32082; d = (4 * c + 3) // 1461; e = c - (1461 * d) // 4; m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1; mon = m + 3 - 12 * (m // 10); yr = d - 4800 + m // 10
    return f"{yr:04d}-{mon:02d}-{day:02d}"


assert J2S(D("1300-02-29")) == "1300-02-29" and D("1215-06-16") - D("1215-06-15") == 1
REIGNS = {"Henry II": ("1154-12-19", "1189-07-06"), "John": ("1199-05-27", "1216-10-19"), "Edward I": ("1272-11-20", "1307-07-07")}
# Edward I's regnal years began on 20 November 1272 (Gough's first day is 16 November, when Henry III died).

# ------------------------------------------------------------------ load
S = list(csv.DictReader(open(os.path.join(ROOT, "work", "stays_geocoded.csv"))))
for s in S:
    s["lat"] = float(s["lat"]) if s["lat"] else None; s["lon"] = float(s["lon"]) if s["lon"] else None

# country of each point
OSP = []; OSC = []
with open(os.path.join(HIST, "osnames_gb.tsv")) as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        if r["type"] == "populatedPlace" and r["local_type"] in ("City", "Town", "Village"):
            OSP.append((float(r["lat"]), float(r["lon"]) * math.cos(math.radians(53)))); OSC.append(r["country"])
TREE = cKDTree(np.array(OSP))
FRREG = {"normandie", "normandy", "anjou", "maine", "poitou", "guienne", "gascony", "bretagne", "limosin", "angoumois", "touraine", "berri", "berry",
         "saintonge", "aquitaine", "picardy", "ponthieu", "perigord", "france", "aunis", "beam", "champagne", "burgundy", "flanders", "vexin", "perche",
         "limousin", "auvergne", "agenois", "quercy", "artois", "brabant", "holland", "aragon", "spain", "italy", "savoy", "sicily", "orleanois"}


def country(s):
    src = s["place_source"]
    m = re.search(r"GeoNames[^:]*: .*\((\w\w)\)", src)
    if m and m.group(1) != "GB": return {"FR": "France", "BE": "Low Countries", "NL": "Low Countries", "IE": "Ireland", "IT": "Italy", "ES": "Spain",
                                         "DE": "Germany", "CH": "Switzerland"}.get(m.group(1), m.group(1))
    if s["lat"] is None:
        reg = re.sub(r"[^a-z]", "", (s["region"] or "").lower())
        if any(f in reg for f in FRREG): return "France" if "flanders" not in reg and "brabant" not in reg and "holland" not in reg else "Low Countries"
        if "ireland" in reg or reg.endswith("co"): return "Ireland"
        return None
    if s["lon"] > 1.9 or (s["lat"] < 49.95 and s["lon"] > -6): return "France"
    d, i = TREE.query((s["lat"], s["lon"] * math.cos(math.radians(53))))
    if s["lon"] < -5.6 and d > 0.25: return "Ireland"
    return OSC[i]


for s in S: s["country"] = country(s)

# Edward I died on 7 July 1307; Gough's pages run on into his son's first weeks
S = [s for s in S if not (s["monarch"] == "Edward I" and s["date"] > "1307-07-07")]

# ------------------------------------------------------------------ isolated stays (likely parsing or placing errors)
# A stay is flagged when it lies more than 120 km from every placed stay within three days either side
# (and there is at least one such neighbour). Flagged stays are kept in the data but left out of nights,
# distances and speeds.
def flag_isolated(mon, km=120, win=3):
    by = defaultdict(list)
    for s in S:
        if s["monarch"] == mon and s["lat"] is not None and not s.get("flag"): by[D(s["date"])].append(s)
    n = 0
    for j, st_ in by.items():
        nb = [x for k in range(-win, win + 1) if k for x in by.get(j + k, [])]
        if not nb: continue
        for s in st_:
            if min(hav(s["lat"], s["lon"], x["lat"], x["lon"]) for x in nb) > km:
                s["flag"] = "isolated"; n += 1
    return n


def prune_conflicts(mon, km=150, win=5):
    """Two places more than 150 km apart on the same day cannot both be right unless the king crossed the
    sea that day; keep the place nearest the median position of the stays within five days either side
    and flag the others as 'same-day conflict'."""
    by = defaultdict(list)
    for s in S:
        if s["monarch"] == mon and s["lat"] is not None: by[D(s["date"])].append(s)
    n = 0
    for j, st_ in by.items():
        if len(st_) < 2: continue
        far = max(hav(a["lat"], a["lon"], b["lat"], b["lon"]) for a in st_ for b in st_)
        if far <= km: continue
        nb = [x for k in range(-win, win + 1) if k for x in by.get(j + k, [])]
        if not nb: continue
        mlat = st.median([x["lat"] for x in nb]); mlon = st.median([x["lon"] for x in nb])
        keep = min(st_, key=lambda s: hav(s["lat"], s["lon"], mlat, mlon))
        for s in st_:
            if s is not keep and hav(s["lat"], s["lon"], keep["lat"], keep["lon"]) > km:
                s["flag"] = "same-day conflict"; n += 1
    return n


CONF = {mon: prune_conflicts(mon) for mon in ("John", "Edward I")}
ISOL = {mon: flag_isolated(mon) for mon in ("John", "Edward I", "Henry II")}
for s in S:
    s.setdefault("flag", "")

# ------------------------------------------------------------------ daily structure
MONS = ["Henry II", "John", "Edward I", "Elizabeth I"]
days = {m: defaultdict(list) for m in MONS}
for s in S:
    if s["monarch"] == "Elizabeth I" and not s["quality"].startswith("household"): continue
    if s["flag"]: continue
    days[s["monarch"]][s["date"]].append(s)


def day_path(prev, stays):
    pts = [x for x in stays if x["lat"] is not None]
    seen = set(); uniq = []
    for p in pts:
        k = (round(p["lat"], 3), round(p["lon"], 3))
        if k not in seen: seen.add(k); uniq.append(p)
    if not uniq: return []
    if prev is None: return uniq
    order = []; cur = prev; rest = uniq[:]
    while rest:
        nx = min(rest, key=lambda p: hav(cur["lat"], cur["lon"], p["lat"], p["lon"])); order.append(nx); rest.remove(nx); cur = nx
    return order


R = {"monarchs": {}}
NIGHTS = []; YEARS = []; MOVES = defaultdict(list)
for mon in MONS:
    ds = sorted(days[mon]); prev = None; prev_date = None
    paths = {}
    for d in ds:
        p = day_path(prev, days[mon][d])
        if not p: continue
        paths[d] = p
        if prev is not None:
            gap = D(d) - D(prev_date)
            dist = hav(prev["lat"], prev["lon"], p[0]["lat"], p[0]["lon"]) + sum(hav(a["lat"], a["lon"], b["lat"], b["lon"]) for a, b in zip(p, p[1:]))
            MOVES[mon].append(dict(d0=prev_date, d1=d, gap=gap, km=dist))
        prev = p[-1]; prev_date = d
        NIGHTS.append(dict(monarch=mon, date=d, place=p[-1]["place"], raw=p[-1]["raw"], lat=p[-1]["lat"], lon=p[-1]["lon"], country=p[-1]["country"] or "",
                           places_that_day=len(p)))
    days[mon + "_paths"] = paths

# ------------------------------------------------------------------ coverage
cov = {}
for mon in MONS:
    rows = [s for s in S if s["monarch"] == mon and (mon != "Elizabeth I" or s["quality"].startswith("household"))]
    pt = [s for s in rows if s["lat"] is not None]
    reg = [s for s in rows if s["lat"] is None and s["placed_by"] == "region"]
    dd = {s["date"] for s in rows}; dp = {s["date"] for s in pt}
    c = dict(entries=len(rows), entries_point=len(pt), entries_region=len(reg), share_point=len(pt) / len(rows) if rows else 0,
             days_with_entry=len(dd), days_with_point=len(dp), distinct_places=len({(s["place"], round(s["lat"], 2)) for s in pt}),
             first=min(dd) if dd else None, last=max(dd) if dd else None)
    if mon in REIGNS:
        a, b = REIGNS[mon]; n = D(b) - D(a) + 1
        c["reign_days"] = n
        c["share_days_with_entry"] = len([d for d in dd if a <= d <= b]) / n
        c["share_days_with_point"] = len([d for d in dp if a <= d <= b]) / n
    cov[mon] = c
eliz_pref = [s for s in S if s["monarch"] == "Elizabeth I" and s["quality"].startswith("preface")]
cov["Elizabeth I preface"] = dict(stops=len(eliz_pref), years=len({s["date"][:4] for s in eliz_pref}), placed=sum(s["lat"] is not None for s in eliz_pref))
R["coverage"] = cov
# parse diagnostics written by the parsers
jr = list(csv.DictReader(open(os.path.join(DATA, "raw_john.csv"))))
R["parse"] = dict(
    john_index_rows=len(jr), john_valid=sum(r["valid"] == "1" for r in jr), john_assigned_year=sum(r["valid"] == "1" and r["year_from"] == "assigned" for r in jr),
    edward_rows=len(list(csv.DictReader(open(os.path.join(DATA, "raw_edward.csv"))))),
    edward_index_names=len(list(csv.DictReader(open(os.path.join(DATA, "edward_index.csv"))))),
    henry_rows=len(list(csv.DictReader(open(os.path.join(DATA, "raw_henry.csv"))))),
    henry_by_evidence=dict(Counter(r["evidence_type"] for r in csv.DictReader(open(os.path.join(DATA, "raw_henry.csv"))))),
    henry_uncertain=sum(r["uncertain"] == "1" for r in csv.DictReader(open(os.path.join(DATA, "raw_henry.csv")))))
R["parse"]["john"] = json.load(open(os.path.join(ROOT, "work", "john_parse.json")))
R["parse"]["edward"] = json.load(open(os.path.join(ROOT, "work", "edward_parse.json")))
pb = Counter((s["monarch"], s["placed_by"]) for s in S)
R["placed_by"] = {m: {k[1]: v for k, v in pb.items() if k[0] == m} for m in MONS}

# ------------------------------------------------------------------ checks against fixed points
PT = lambda name, mon=None: next((s["lat"], s["lon"]) for s in S if s["place"].lower() == name.lower() and s["lat"] is not None and (mon is None or s["monarch"] == mon))


def where(mon, date, window=0):
    out = []
    for k in range(-window, window + 1):
        d = J2S(D(date) + k)
        out += [s for s in days[mon].get(d, []) if s["lat"] is not None]
    return out


checks = []


def check(label, mon, date, target_name, target, window=0, km=25, source=""):
    st_ = where(mon, date, window)
    if not st_:
        checks.append(dict(check=label, monarch=mon, date=date, window_days=window, target=target_name, found="no placed entry", km=None, passed=None, source=source)); return
    best = min(st_, key=lambda s: hav(s["lat"], s["lon"], *target))
    k = hav(best["lat"], best["lon"], *target)
    checks.append(dict(check=label, monarch=mon, date=date, window_days=window, target=target_name, found=best["place"] + " (" + best["date"] + ")", km=round(k, 1),
                       passed=k <= km, source=source))


RUN = PT("Runnymede"); NEWARK = PT("Newark-on-Trent") if any(s["place"] == "Newark-on-Trent" for s in S) else PT("Newark")
check("John meets the barons at Runnymede", "John", "1215-06-15", "Runnymede", RUN, 0, 10, "Wikipedia, John, King of England: met the rebel leaders at Runnymede on 15 June 1215")
check("John dies at Newark", "John", "1216-10-18", "Newark", NEWARK, 1, 10, "Wikipedia, John, King of England: died 19 October 1216, Newark Castle")
RHU = PT("Rhuddlan"); check("Edward I's first Welsh war (August 1277)", "Edward I", "1277-08-25", "Rhuddlan", RHU, 3, 30, "Wikipedia, Edward I: invaded Wales in July 1277")
check("Edward I's second Welsh war (1283)", "Edward I", "1283-05-01", "Conwy", PT("Conwy"), 5, 40, "Wikipedia, Edward I: conquest of Wales 1282 to 1283")
BER = PT("Berwick-upon-Tweed"); check("Edward I takes Berwick (1296)", "Edward I", "1296-04-05", "Berwick-upon-Tweed", BER, 5, 20, "Wikipedia, Edward I: invaded Scotland in 1296 and took Berwick")
check("Edward I in Flanders (autumn 1297)", "Edward I", "1297-10-15", "Ghent", PT("Ghent"), 10, 60, "Wikipedia, Edward I: in Flanders until the truce of October 1297")
check("Siege of Caerlaverock (1300)", "Edward I", "1300-07-12", "Caerlaverock Castle", PT("Caerlaverock Castle"), 6, 25, "Wikipedia, Edward I: besieged Caerlaverock Castle in 1300")
check("Edward I's last days (July 1307)", "Edward I", "1307-07-05", "Burgh by Sands", PT("Burgh by Sands") if any(s["place"] == "Burgh by Sands" for s in S) else (54.92, -3.05), 6, 30,
      "Wikipedia, Edward I: encamped at Burgh by Sands on 6 July 1307 and died there on 7 July")
for c in checks:
    print("CHECK", c)
with open(os.path.join(DATA, "checks.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, list(checks[0])); w.writeheader(); w.writerows(checks)
R["checks"] = checks
R["checks_passed"] = sum(1 for c in checks if c["passed"]); R["checks_n"] = len(checks)

# Gascony 1286 to 1289 and other date-range shares
def share_country(mon, a, b, ctry):
    nn = [n for n in NIGHTS if n["monarch"] == mon and a <= n["date"] <= b]
    return (sum(n["country"] == ctry for n in nn) / len(nn)) if nn else None, len(nn)


# ------------------------------------------------------------------ plausibility of moves (parsing check)
plaus = {}
for mon in ("John", "Edward I"):
    mv = [m for m in MOVES[mon] if m["gap"] == 1]
    plaus[mon] = dict(consecutive_pairs=len(mv), over_60km=sum(m["km"] > 60 for m in mv), over_100km=sum(m["km"] > 100 for m in mv),
                      share_over_100km=sum(m["km"] > 100 for m in mv) / len(mv), share_under_40km=sum(m["km"] <= 40 for m in mv) / len(mv))
R["plausibility"] = plaus
R["isolated"] = ISOL; R["conflicts"] = CONF

# ------------------------------------------------------------------ nights per place, top places
places = defaultdict(lambda: dict(nights=0, entries=0))
for s in S:
    if s["lat"] is None: continue
    k = (s["monarch"], s["place"], round(s["lat"], 4), round(s["lon"], 4))
    places[k]["entries"] += 1
for n in NIGHTS:
    k = (n["monarch"], n["place"], round(n["lat"], 4), round(n["lon"], 4)); places[k]["nights"] += 1
PL = []
for (mon, name, la, lo), v in places.items():
    src = next(s["place_source"] for s in S if s["monarch"] == mon and s["place"] == name and s["lat"] is not None and round(s["lat"], 4) == la)
    PL.append(dict(monarch=mon, place=name, lat=la, lon=lo, nights=v["nights"], entries=v["entries"], source=src))
PL.sort(key=lambda r: (r["monarch"], -r["nights"]))
with open(os.path.join(DATA, "places.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, list(PL[0])); w.writeheader(); w.writerows(PL)
with open(os.path.join(DATA, "nights.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, list(NIGHTS[0])); w.writeheader(); w.writerows(NIGHTS)

# ------------------------------------------------------------------ royal forests
A = {}
for fn in ("wikipedia_batch12.json.gz", "wikipedia_batch12b.json.gz"):
    A.update(json.load(gzip.open(os.path.join(HIST, "_data12", fn)))["articles"])
t = A["Royal forest"]["text"]; tab = t[t.index("== Royal forests by county =="):t.index("===Ireland===")]
OSW = defaultdict(list); OSPOP = defaultdict(list)
norm = lambda s: re.sub(r"[^a-z]", "", s.lower())
with open(os.path.join(HIST, "osnames_gb.tsv")) as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        if r["type"] == "landcover": OSW[norm(r["name1"])].append((float(r["lat"]), float(r["lon"]), r["county"], r["name1"]))
        elif r["type"] == "populatedPlace": OSPOP[norm(r["name1"])].append((float(r["lat"]), float(r["lon"]), r["county"], r["name1"]))
CTY = {"Northants": "Northamptonshire", "Hants": "Hampshire", "Wilts": "Wiltshire", "Notts": "Nottinghamshire", "Glos": "Gloucestershire", "Bucks": "Buckinghamshire",
       "Berks": "Berkshire", "Oxon": "Oxfordshire", "Yorks": "Yorkshire", "Lancs": "Lancashire", "Herts": "Hertfordshire", "Leics": "Leicestershire"}
CKEYS = {"Berkshire": ["Berkshire", "Windsor", "Reading", "Wokingham", "Bracknell", "Slough"], "Yorkshire": ["Yorkshire", "York"], "Middlesex": ["London"],
         "Essex": ["Essex", "London", "Thurrock"], "Huntingdonshire": ["Cambridgeshire"], "Lancashire": ["Lancashire", "Blackburn"], "Hampshire": ["Hampshire", "Southampton"],
         "Northamptonshire": ["Northamptonshire"], "Cheshire": ["Cheshire"], "Gloucestershire": ["Gloucestershire"], "Somerset": ["Somerset"], "Shropshire": ["Shropshire", "Telford"],
         "Cumberland": ["Cumberland"], "Herefordshire": ["Herefordshire"], "Leicestershire": ["Leicestershire"], "Lincolnshire": ["Lincolnshire"]}


def county_ok(cty, osc):
    if not cty: return True
    for w in re.split(r"[ ,]+", cty):
        if len(w) < 4 or w in ("and", "part", "modern", "negligibly", "Fens"): continue
        for k in CKEYS.get(w, [w[:5]]):
            if k.lower() in osc.lower(): return True
    return False


FOR = []
for row in tab.split("\n|-")[1:]:
    cells = [c.strip() for c in re.split(r"\|\|", row.strip().lstrip("|"))]
    if len(cells) < 2 or cells[0].startswith("!"): continue
    clean = lambda c: re.sub(r"<ref.*?(</ref>|/>)|\{\{.*?\}\}|\[http\S+\s([^\]]*)\]", lambda m: m.group(2) or "" if m.group(0).startswith("[http") else "", c)
    nm = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", clean(cells[0])).strip(" '")
    link = re.search(r"\[\[([^|\]]+)", cells[0]); link = link.group(1) if link else nm
    cty = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", clean(cells[1])).strip()
    cty = CTY.get(cty, cty)
    if not nm: continue
    base = re.sub(r"\s*\(.*?\)|\s+(Forest|Chase|Frith)$|^Forest of\s+|,.*$", "", nm).strip()
    variants = [nm, nm + " Forest", "Forest of " + nm, base, base + " Forest", "Forest of " + base, base + " Chase", base + " Park", base + " Great Park"]
    got = None
    for v in variants:
        cands = [p for p in OSW.get(norm(v), []) if county_ok(cty, p[2])]
        if cands: got = (cands[0][0], cands[0][1], f"OS Open Names wood or forest: {cands[0][3]}"); break
    if not got and link in A and A[link].get("coord"):
        got = (A[link]["coord"]["lat"], A[link]["coord"]["lon"], f"Wikipedia article coordinates: {link}")
    if not got:
        for v in (base, base.split()[0] if base else ""):
            cands = [p for p in OSPOP.get(norm(v), []) if county_ok(cty, p[2])]
            if cands: got = (cands[0][0], cands[0][1], f"OS Open Names settlement it is named after: {cands[0][3]}"); break
    FOR.append(dict(forest=nm, county=cty, lat=round(got[0], 5) if got else "", lon=round(got[1], 5) if got else "", located_by=got[2] if got else "not located"))
with open(os.path.join(DATA, "royal_forests.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, list(FOR[0])); w.writeheader(); w.writerows(FOR)
FP = [(r["lat"], r["lon"]) for r in FOR if r["lat"] != ""]
FTREE = cKDTree(np.array([(a, b * math.cos(math.radians(52.5))) for a, b in FP]))
R["forests"] = dict(listed=len(FOR), located=len(FP))


def near_forest(lat, lon, km=10):
    d, i = FTREE.query((lat, lon * math.cos(math.radians(52.5))))
    return d * 111.2 <= km


# ------------------------------------------------------------------ per-monarch summaries and years
LONDON = (51.4995, -0.1248)   # Westminster (GeoNames City of Westminster point is 1 km away; any stay within 5 km counts)
for mon in MONS:
    nn = [n for n in NIGHTS if n["monarch"] == mon]
    if not nn: continue
    m = {}
    top = Counter(n["place"] for n in nn).most_common(25)
    m["top_places"] = [dict(place=p, nights=c, share=c / len(nn)) for p, c in top]
    m["nights"] = len(nn)
    cc = Counter(n["country"] or "unknown" for n in nn)
    m["country_share"] = {k: v / len(nn) for k, v in cc.items()}
    m["london_share"] = sum(hav(n["lat"], n["lon"], *LONDON) <= 5 for n in nn) / len(nn)
    if mon != "Elizabeth I":
        m["forest_share"] = sum(near_forest(n["lat"], n["lon"]) for n in nn if n["country"] == "England") / max(1, sum(n["country"] == "England" for n in nn))
    mv = MOVES[mon]
    d1 = [x for x in mv if x["gap"] == 1]
    m["consecutive_pairs"] = len(d1)
    m["moved_share"] = sum(x["km"] > 3 for x in d1) / len(d1) if len(d1) >= 5 else None
    kms = [x["km"] for x in d1 if x["km"] > 3]
    m["km_per_moving_day_median"] = st.median(kms) if len(kms) >= 5 else None
    m["km_per_moving_day_p90"] = float(np.percentile(kms, 90)) if len(kms) >= 5 else None
    m["moving_days_n"] = len(kms)
    # stays: runs of consecutive nights in the same place
    runs = []; cur = None
    for n in nn:
        if cur and n["place"] == cur["place"] and D(n["date"]) - D(cur["last"]) == 1:
            cur["len"] += 1; cur["last"] = n["date"]
        else:
            if cur: runs.append(cur)
            cur = dict(place=n["place"], len=1, last=n["date"])
    runs.append(cur)
    m["stay_median_nights"] = st.median([r["len"] for r in runs]); m["stay_mean_nights"] = st.mean([r["len"] for r in runs])
    m["distinct_night_places"] = len({n["place"] for n in nn})
    # per year
    yrs = defaultdict(lambda: dict(nights=0, km=0.0, places=set(), countries=Counter(), london=0, forest=0, eng=0, moves=0))
    for n in nn:
        y = int(n["date"][:4]); yy = yrs[y]
        yy["nights"] += 1; yy["places"].add(n["place"]); yy["countries"][n["country"] or "unknown"] += 1
        yy["london"] += hav(n["lat"], n["lon"], *LONDON) <= 5
        if n["country"] == "England": yy["eng"] += 1; yy["forest"] += near_forest(n["lat"], n["lon"])
    for x in mv:
        # legs no more than 7 days apart and no faster than 100 km a day (faster legs are mostly misread dates or places)
        if x["gap"] <= 7 and x["km"] / x["gap"] <= 100: yrs[int(x["d1"][:4])]["km"] += x["km"]; yrs[int(x["d1"][:4])]["moves"] += 1
    ylist = []
    for y in sorted(yrs):
        v = yrs[y]
        row = dict(monarch=mon, year=y, nights=v["nights"], km=round(v["km"]), distinct_places=len(v["places"]),
                   england=v["countries"].get("England", 0), wales=v["countries"].get("Wales", 0), scotland=v["countries"].get("Scotland", 0),
                   france=v["countries"].get("France", 0), low_countries=v["countries"].get("Low Countries", 0), ireland=v["countries"].get("Ireland", 0),
                   london=v["london"], forest=v["forest"], km_per_record_day=round(v["km"] / v["nights"], 1) if v["nights"] else 0)
        ylist.append(row); YEARS.append(row)
    m["years"] = ylist
    full = [r for r in ylist if r["nights"] >= 150]
    m["km_per_year_median"] = st.median([r["km"] for r in full]) if full else None
    m["km_per_year_max"] = max(full, key=lambda r: r["km"]) if full else None
    m["places_per_year_median"] = st.median([r["distinct_places"] for r in full]) if full else None
    # month pattern (nights by month and share near forests by month)
    mon_n = Counter(int(n["date"][5:7]) for n in nn)
    m["by_month"] = {k: mon_n.get(k, 0) for k in range(1, 13)}
    if mon in ("John", "Edward I"):
        fm = Counter(int(n["date"][5:7]) for n in nn if n["country"] == "England" and near_forest(n["lat"], n["lon"]))
        em = Counter(int(n["date"][5:7]) for n in nn if n["country"] == "England")
        m["forest_by_month"] = {k: (fm.get(k, 0) / em[k]) if em.get(k) else None for k in range(1, 13)}
        lm = Counter(int(n["date"][5:7]) for n in nn if hav(n["lat"], n["lon"], *LONDON) <= 5)
        m["london_by_month"] = {k: (lm.get(k, 0) / mon_n[k]) if mon_n.get(k) else None for k in range(1, 13)}
    # Christmas
    xm = []
    for y in range(1150, 1310):
        st_ = [s for s in days[mon].get(f"{y}-12-25", []) if s["lat"] is not None]
        if st_: xm.append(dict(year=y, place=st_[-1]["place"]))
    m["christmas"] = xm
    R["monarchs"][mon] = m

# Henry II Christmas courts from Eyton's narrative
HX = list(csv.DictReader(open(os.path.join(DATA, "raw_henry_christmas.csv"))))
R["monarchs"]["Henry II"]["christmas_eyton"] = [dict(year=int(x["year"]), place=x["place"]) for x in HX]
for mon in ("Henry II", "John", "Edward I"):
    xs = R["monarchs"][mon].get("christmas_eyton") if mon == "Henry II" else R["monarchs"][mon]["christmas"]
    R["monarchs"][mon]["christmas_n"] = len(xs)
    R["monarchs"][mon]["christmas_top"] = Counter(x["place"] for x in xs).most_common(5)
    R["monarchs"][mon]["christmas_distinct"] = len({x["place"] for x in xs})

# John: before and after the loss of Normandy (Rouen fell in June 1204)
def cshare(mon, a, b, key):
    nn = [n for n in NIGHTS if n["monarch"] == mon and a <= n["date"] <= b]
    return (sum((n["country"] or "") == key for n in nn) / len(nn)) if nn else None


# day-level continent share including entries that are not on a point (Hardy prints the province)
def day_continent_share(mon, a, b):
    dd = defaultdict(list)
    for s in S:
        if s["monarch"] == mon and a <= s["date"] <= b: dd[s["date"]].append(s["country"])
    k = [d for d, cs in dd.items() if any(c for c in cs)]
    return sum(any(c in ("France", "Low Countries") for c in dd[d]) for d in k) / len(k) if k else None, len(k)


R["john"] = dict(
    continent_1199_1203=day_continent_share("John", "1199-05-27", "1203-12-05")[0],
    continent_1204_1216=day_continent_share("John", "1203-12-06", "1216-10-19")[0],
    continent_days_1199_1203=day_continent_share("John", "1199-05-27", "1203-12-05")[1],
    ireland_1210=cshare("John", "1210-06-01", "1210-08-31", "Ireland"),
    poitou_1206=cshare("John", "1206-06-01", "1206-12-31", "France"),
    poitou_1214=cshare("John", "1214-02-15", "1214-10-15", "France"))
# John left Normandy for the last time in December 1203; Hardy's index places him at Barfleur on 5 December? (see checks)
R["edward"] = dict(
    wales_1277_aug_nov=cshare("Edward I", "1277-07-15", "1277-11-30", "Wales"),
    wales_1282_1283=cshare("Edward I", "1282-04-01", "1283-12-31", "Wales"),
    wales_1284=cshare("Edward I", "1284-01-01", "1284-12-31", "Wales"),
    france_1286_1289=cshare("Edward I", "1286-05-13", "1289-08-12", "France"),
    lowc_1297_1298=cshare("Edward I", "1297-08-22", "1298-03-14", "Low Countries"),
    scotland_1296=cshare("Edward I", "1296-03-28", "1296-09-30", "Scotland"),
    scotland_1298=cshare("Edward I", "1298-06-25", "1298-12-31", "Scotland"),
    scotland_1303_1304=cshare("Edward I", "1303-05-15", "1304-08-31", "Scotland"),
    war_share_by_decade={})
# Edward I nights by decade: England, Wales, Scotland, abroad
for a, b in ((1272, 1281), (1282, 1291), (1292, 1301), (1302, 1307)):
    nn = [n for n in NIGHTS if n["monarch"] == "Edward I" and a <= int(n["date"][:4]) <= b]
    c = Counter(n["country"] for n in nn)
    R["edward"]["war_share_by_decade"][f"{a} to {b}"] = {k: c.get(k, 0) / len(nn) for k in ("England", "Wales", "Scotland", "France", "Low Countries")}
# Lanercost 1306 to 1307: the sick king's long stay
lan = [n for n in NIGHTS if n["monarch"] == "Edward I" and n["place"].startswith("Lanercost")]
R["edward"]["lanercost_nights"] = len(lan); R["edward"]["lanercost_first"] = min(n["date"] for n in lan) if lan else None
R["edward"]["lanercost_last"] = max(n["date"] for n in lan) if lan else None

# Elizabeth 1561
e = sorted([n for n in NIGHTS if n["monarch"] == "Elizabeth I"], key=lambda n: n["date"])
km61 = sum(m["km"] for m in MOVES["Elizabeth I"])
R["elizabeth"] = dict(days_1561=len(e), first=e[0]["date"], last=e[-1]["date"], places_1561=len({n["place"] for n in e}), km_1561=km61,
                      moves_1561=sum(m["km"] > 3 for m in MOVES["Elizabeth I"]),
                      km_per_moving_day_1561=st.median([m["km"] for m in MOVES["Elizabeth I"] if m["km"] > 3]),
                      stops_1561=[dict(place=p, nights=c) for p, c in Counter(n["place"] for n in e).items()],
                      preface_years=sorted({int(s["date"][:4]) for s in eliz_pref}), preface_stops=len(eliz_pref),
                      preface_top=Counter(s["place"] for s in eliz_pref).most_common(6))

# headline comparisons
R["compare"] = {mon: dict(nights=R["monarchs"][mon]["nights"], distinct=R["monarchs"][mon]["distinct_night_places"],
                          moved_share=R["monarchs"][mon]["moved_share"], km_med=R["monarchs"][mon]["km_per_moving_day_median"],
                          london=R["monarchs"][mon]["london_share"], stay_mean=R["monarchs"][mon]["stay_mean_nights"],
                          km_year=R["monarchs"][mon]["km_per_year_median"]) for mon in MONS if mon in R["monarchs"]}

OUTC = ["monarch", "date", "order", "raw", "region", "place", "lat", "lon", "country", "placed_by", "place_source", "quality", "flag", "src"]
with open(os.path.join(DATA, "stays.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, OUTC, extrasaction="ignore"); w.writeheader(); w.writerows(sorted(S, key=lambda s: (s["monarch"], s["date"], int(s["order"]))))
M = R["monarchs"]
H = {}
H["edward_westminster_nights"] = next(t["nights"] for t in M["Edward I"]["top_places"] if t["place"] == "Westminster")
H["edward_westminster_share"] = H["edward_westminster_nights"] / M["Edward I"]["nights"]
H["john_westminster_nights"] = next((t["nights"] for t in M["John"]["top_places"] if t["place"] == "Westminster"), 0)
H["john_westminster_share"] = H["john_westminster_nights"] / M["John"]["nights"]
H["john_rouen_nights"] = next(t["nights"] for t in M["John"]["top_places"] if t["place"] == "Rouen")
H["john_winchester_nights"] = next(t["nights"] for t in M["John"]["top_places"] if t["place"] == "Winchester")
H["moved_ratio"] = M["John"]["moved_share"] / M["Edward I"]["moved_share"]
H["km_ratio"] = M["John"]["km_per_year_median"] / M["Edward I"]["km_per_year_median"]
H["henry_france_share"] = M["Henry II"]["country_share"].get("France", 0)
H["henry_england_share"] = M["Henry II"]["country_share"].get("England", 0)
H["henry_christmas_n"] = len(M["Henry II"]["christmas_eyton"])
H["henry_christmas_france"] = sum(1 for x in M["Henry II"]["christmas_eyton"] if x["place"] in ("Bordeaux", "Falaise", "Le Mans", "Bayeux", "Nantes", "Argentan", "Angers", "Caen"))
H["john_christmas_n"] = M["John"]["christmas_n"]; H["edward_christmas_n"] = M["Edward I"]["christmas_n"]
H["john_christmas_distinct"] = M["John"]["christmas_distinct"]; H["edward_christmas_distinct"] = M["Edward I"]["christmas_distinct"]
H["john_flagged"] = R["isolated"]["John"] + R["conflicts"]["John"]; H["edward_flagged"] = R["isolated"]["Edward I"] + R["conflicts"]["Edward I"]
H["forest_month_john_max"] = max((v, k) for k, v in M["John"]["forest_by_month"].items() if v is not None)
H["forest_month_john_min"] = min((v, k) for k, v in M["John"]["forest_by_month"].items() if v is not None)
H["edward_lanercost_nights"] = R["edward"]["lanercost_nights"]
R["headline"] = H
R["placed_manual_rows"] = sum(1 for _ in csv.DictReader(open(os.path.join(HERE, "manual_places.csv"))))
json.dump(R, open(os.path.join(DATA, "results.json"), "w"), indent=1, default=lambda o: list(o) if isinstance(o, set) else str(o))
with open(os.path.join(DATA, "years.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, list(YEARS[0])); w.writeheader(); w.writerows(YEARS)
json.dump(R, open(os.path.join(DATA, "results.json"), "w"), indent=1, default=lambda o: list(o) if isinstance(o, set) else str(o))

# ------------------------------------------------------------------ page data (compact)
P = {"monarchs": {}, "forests": [[r["forest"], r["lat"], r["lon"]] for r in FOR if r["lat"] != ""]}
for mon in MONS:
    nn = sorted([n for n in NIGHTS if n["monarch"] == mon], key=lambda n: n["date"])
    if not nn: continue
    plist = []; pidx = {}
    for n in nn:
        k = (n["place"], round(n["lat"], 3), round(n["lon"], 3))
        if k not in pidx: pidx[k] = len(plist); plist.append([n["place"], round(n["lat"], 3), round(n["lon"], 3), 0])
        plist[pidx[k]][3] += 1
    d0 = D(nn[0]["date"])
    P["monarchs"][mon] = dict(start=nn[0]["date"], places=plist,
                              nights=[[D(n["date"]) - d0, pidx[(n["place"], round(n["lat"], 3), round(n["lon"], 3))]] for n in nn])
P["elizabeth_preface"] = [[int(s["date"][:4]), s["order"], s["place"], round(s["lat"], 3), round(s["lon"], 3)] for s in eliz_pref if s["lat"] is not None]
P["henry_christmas"] = [[x["year"], x["place"]] for x in R["monarchs"]["Henry II"]["christmas_eyton"]]
json.dump(P, open(os.path.join(DATA, "page_data.json"), "w"), separators=(",", ":"))
print(json.dumps({k: R[k] for k in ("coverage", "plausibility", "john", "edward", "forests", "compare")}, indent=1, default=str)[:6000])
