"""Step 5. Place every parsed stay on the map.

Gazetteers (read in place, never copied):
  * manual_places.csv (this folder): my identifications of old or Latin forms and of the most visited
    places, each pointing to a named entry in one of the gazetteers below (never a typed coordinate);
  * Wikidata royal residences, palaces, castles, hunting lodges, abbeys and priories (CC0), from the bundle;
  * OS Open Names populated places and woodland (OGL v3);
  * GeoNames towns of 1,000 people or more, via github.com/lutangar/cities.json (CC BY 4.0), for France,
    the Low Countries, Ireland, Spain, Italy and Scottish and Welsh towns.
Same-named places are separated by the county or province printed by the itinerary's editor (historic
county centroids are computed from OS Open Names), and failing that by the itinerary itself: the
candidate nearest to the places where the king is found within three days either side.
Outputs: ../data/places.csv (one row per distinct place and how it was placed), ../data/stays.csv
(intermediate, in ../work/) and ../work/unplaced.csv (for review).
Run: python3 05_geocode.py
"""
import csv, difflib, gzip, json, math, os, re, unicodedata
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, ".."); HIST = os.path.join(ROOT, "..")


def strip_acc(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s):
    s = strip_acc(str(s)).lower().replace("’", "'")
    s = re.sub(r"\bst\.?\s", "saint ", s); s = re.sub(r"\bste\.?\s", "sainte ", s)
    return re.sub(r"[^a-z]", "", s)


def hav(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


# ------------------------------------------------------------------ gazetteers
OS = defaultdict(list)       # norm name -> [(lat, lon, local_type, county, label)]
OSW = defaultdict(list)      # woodland / landcover names
COUNTY_PTS = defaultdict(list)
with open(os.path.join(HIST, "osnames_gb.tsv")) as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        if r["type"] == "populatedPlace":
            la, lo = float(r["lat"]), float(r["lon"])
            for nm in (r["name1"], r["name2"]):
                if nm: OS[norm(nm)].append((la, lo, r["local_type"], r["county"], nm))
            if r["county"]: COUNTY_PTS[r["county"]].append((la, lo))
        elif r["type"] == "landcover":
            OSW[norm(r["name1"])].append((float(r["lat"]), float(r["lon"]), r["local_type"], r["county"], r["name1"]))
GN = defaultdict(list)
for n, la, lo, cc in json.load(open(os.path.join(ROOT, "work", "geonames_cities.json"))):
    GN[norm(n)].append((la, lo, "GeoNames " + cc, cc, n))
WD = defaultdict(list); WDQ = {}
B = json.load(gzip.open(os.path.join(HIST, "_data12", "wd_osm_bundle12.json.gz")))
for line in B["results"]["wd_royal_residences"]["tsv"].split("\n")[1:]:
    p = line.split("\t")
    if len(p) < 4 or not p[2].startswith("POINT"): continue
    lo, la = map(float, p[2][6:-1].split())
    lab = p[1].split('"')[1] if '"' in p[1] else p[1]
    q = p[0].rsplit("/", 1)[-1].strip(">")
    cls = p[3].split('"')[1] if '"' in p[3] else p[3]
    WDQ[q] = (la, lo, cls, "", lab)
    WD[norm(lab)].append((la, lo, cls, q, lab))
    base = re.sub(r"\s+(Castle|Palace|Abbey|Priory|Manor|Hunting Lodge|Royal Palace|Cathedral)$", "", lab)
    if base != lab: WD[norm(base)].append((la, lo, cls, q, lab))

# historic counties and continental provinces -> OS county keys or country codes
HC = {
    "berkshire": ["Berkshire", "Windsor and Maidenhead", "Reading", "Wokingham", "Bracknell", "Slough"], "berks": "berkshire",
    "buckinghamshire": ["Buckinghamshire", "Milton Keynes"], "bucks": "buckinghamshire", "buckm": "buckinghamshire",
    "bedfordshire": ["Bedford", "Luton"], "beds": "bedfordshire", "bedford": "bedfordshire",
    "cambridgeshire": ["Cambridgeshire", "Peterborough"], "camb": "cambridgeshire", "cambridge": "cambridgeshire",
    "huntingdonshire": ["Cambridgeshire", "Peterborough"], "huntn": "huntingdonshire", "hunt": "huntingdonshire",
    "cheshire": ["Cheshire", "Warrington", "Halton"], "chester": "cheshire",
    "cornwall": ["Cornwall"], "cumberland": ["Cumberland"], "cumbd": "cumberland", "cumb": "cumberland",
    "derbyshire": ["Derbyshire", "City of Derby"], "derby": "derbyshire",
    "devonshire": ["Devon", "Plymouth", "Torbay"], "devon": "devonshire",
    "dorsetshire": ["Dorset", "Bournemouth"], "dorset": "dorsetshire",
    "durham": ["Durham", "Darlington", "Hartlepool", "Stockton"],
    "essex": ["Essex", "Thurrock", "Southend", "Greater London"],
    "gloucestershire": ["Gloucestershire", "Bristol"], "gloucr": "gloucestershire", "glouc": "gloucestershire", "gloucester": "gloucestershire",
    "hampshire": ["Hampshire", "Southampton", "Portsmouth", "Isle of Wight"], "hants": "hampshire", "ston": "hampshire", "soton": "hampshire", "southampton": "hampshire",
    "herefordshire": ["Herefordshire"], "hereford": "herefordshire",
    "hertfordshire": ["Hertfordshire"], "herts": "hertfordshire", "hertford": "hertfordshire",
    "kent": ["Kent", "Medway", "Greater London"],
    "lancashire": ["Lancashire", "Blackburn", "Blackpool"], "lanc": "lancashire", "lancaster": "lancashire",
    "leicestershire": ["Leicestershire", "Leicester", "Rutland"], "leicr": "leicestershire", "leicester": "leicestershire",
    "lincolnshire": ["Lincolnshire"], "lincoln": "lincolnshire", "linc": "lincolnshire",
    "middlesex": ["Greater London"], "middx": "middlesex", "midd": "middlesex",
    "norfolk": ["Norfolk"], "norf": "norfolk",
    "northamptonshire": ["Northamptonshire"], "nton": "northamptonshire", "northampton": "northamptonshire",
    "northumberland": ["Northumberland"], "nland": "northumberland",
    "nottinghamshire": ["Nottinghamshire", "City of Nottingham"], "notts": "nottinghamshire", "nottm": "nottinghamshire",
    "oxfordshire": ["Oxfordshire"], "oxon": "oxfordshire", "oxford": "oxfordshire",
    "rutland": ["Rutland"], "rutlandshire": "rutland",
    "shropshire": ["Shropshire", "Telford"], "salop": "shropshire",
    "somersetshire": ["Somerset"], "somerset": "somersetshire", "som": "somersetshire",
    "staffordshire": ["Staffordshire", "Stoke"], "stafford": "staffordshire",
    "suffolk": ["Suffolk"], "suff": "suffolk",
    "surrey": ["Surrey", "Greater London"],
    "sussex": ["Sussex", "Brighton"],
    "warwickshire": ["Warwickshire"], "warw": "warwickshire", "warwick": "warwickshire",
    "westmoreland": ["Westmorland"], "westmorland": "westmoreland", "westmd": "westmoreland",
    "wiltshire": ["Wiltshire", "Swindon"], "wilts": "wiltshire",
    "worcestershire": ["Worcestershire"], "worcr": "worcestershire", "worcester": "worcestershire",
    "yorkshire": ["Yorkshire", "York", "Kingston upon Hull", "Redcar", "Middlesbrough"], "york": "yorkshire",
    "yorkwr": "yorkshire", "yorknr": "yorkshire", "yorker": "yorkshire",
    "monmouthshire": ["Monmouthshire", "Newport", "Torfaen", "Blaenau"], "monmouth": "monmouthshire",
    "flint": ["Flintshire"], "flintshire": "flint", "denbigh": ["Denbighshire", "Wrexham", "Conwy"], "carn": ["Gwynedd", "Conwy"], "cam": "carn",
    "carnarvon": "carn", "caernarvon": "carn", "angl": ["Anglesey"], "anglesey": "angl", "merioneth": ["Gwynedd"], "pembroke": ["Pembrokeshire"],
    "pembrokeshire": "pembroke", "carmarthen": ["Carmarthenshire"], "cardigan": ["Ceredigion"], "glamorgan": ["Glamorgan", "Cardiff", "Swansea", "Bridgend", "Neath", "Rhondda", "Merthyr", "Caerphilly"],
    "brecon": ["Powys"], "radnor": ["Powys"], "montgomery": ["Powys"],
    "roxburgh": ["Scottish Borders"], "berwick": ["Scottish Borders", "Northumberland"], "selkirk": ["Scottish Borders"], "peebles": ["Scottish Borders"],
    "edinburgh": ["Edinburgh", "Midlothian"], "haddington": ["East Lothian"], "haddn": "haddington", "linlithgow": ["West Lothian", "Falkirk"],
    "fife": ["Fife"], "perth": ["Perth and Kinross"], "pertk": "perth", "forfar": ["Angus", "Dundee"], "kincard": ["Aberdeenshire"], "kincardine": "kincard",
    "aberdeen": ["Aberdeen"], "banff": ["Aberdeenshire", "Moray"], "elgin": ["Moray"], "moray": ["Moray"], "stirling": ["Stirling", "Falkirk"],
    "lanark": ["Lanarkshire", "Glasgow"], "ayr": ["Ayrshire"], "dumfries": ["Dumfries and Galloway"], "kirkcudt": ["Dumfries and Galloway"],
    "wigtown": ["Dumfries and Galloway"], "inverness": ["Highland"], "clackmannan": ["Clackmannanshire"], "lothian": ["Lothian", "Edinburgh"],
}
FR = {"normandie", "normandy", "anjou", "maine", "poitou", "guienne", "gascony", "gascogne", "bretagne", "brittany", "limosin", "limousin", "angoumois",
      "touraine", "berri", "berry", "saintonge", "aquitaine", "picardy", "picardie", "ponthieu", "perigord", "quercy", "auvergne", "vexin", "beam", "bearn",
      "burgundy", "bourgogne", "champagne", "france", "isledefrance", "orleanois", "lamarche", "marche", "agenois", "rouergue", "languedoc", "toulouse",
      "armagnac", "bigorre", "bordelais", "blesois", "dunois", "perche", "cotentin", "avranchin", "isle", "flanders", "artois", "boulogne", "boulonnais"}
OTHER_CC = {"flanders": ["BE", "FR", "NL"], "brabant": ["BE", "NL"], "holland": ["NL"], "zealand": ["NL"], "ireland": ["IE", "GB"], "spain": ["ES"],
            "aragon": ["ES"], "castile": ["ES"], "navarre": ["ES", "FR"], "italy": ["IT"], "sicily": ["IT"], "savoy": ["FR", "IT", "CH"],
            "germany": ["DE"], "scotland": ["GB"], "wales": ["GB"]}


def hkey(region):
    k = norm(region)
    for _ in range(3):
        if isinstance(HC.get(k), str): k = HC[k]
    return k


CENT = {}
for k, v in HC.items():
    if isinstance(v, list):
        pts = [p for c, ps in COUNTY_PTS.items() if any(key.lower() in c.lower() for key in v) for p in ps]
        if pts:
            CENT[k] = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

TYPE_RANK = {"City": 0, "Town": 1, "Suburban Area": 2, "Village": 3, "Hamlet": 4, "Other Settlement": 5}

MANUAL = {}
with open(os.path.join(HERE, "manual_places.csv")) as fh:
    for r in csv.DictReader(fh):
        MANUAL[(r["monarch"], norm(r["raw"]))] = r


def resolve_manual(r):
    """A manual row names the gazetteer and the entry: os:<name>[|<county substring>], osw:<name>, wd:<Q id>, gn:<name>|<cc>, region:<name>."""
    g = r["gazetteer"]; kind, _, key = g.partition(":")
    name, _, extra = key.partition("|")
    if kind == "wd":
        la, lo, cls, _, lab = WDQ[name]; return la, lo, f"Wikidata {name} ({lab})"
    if kind in ("os", "osw"):
        pool = (OS if kind == "os" else OSW)[norm(name)]
        if extra: pool = [p for p in pool if extra.lower() in p[3].lower()] or pool
        pool = sorted(pool, key=lambda p: TYPE_RANK.get(p[2], 6))
        if not pool: raise KeyError(g)
        return pool[0][0], pool[0][1], f"OS Open Names: {pool[0][4]} ({pool[0][2]}, {pool[0][3]})"
    if kind == "gn":
        pool = [p for p in GN[norm(name)] if not extra or p[3] == extra]
        if not pool: raise KeyError(g)
        return pool[0][0], pool[0][1], f"GeoNames: {pool[0][4]} ({pool[0][3]})"
    if kind == "region":
        return None, None, "region"
    if kind == "none":
        return None, None, "none"
    raise KeyError(g)


def variants(raw):
    s = re.sub(r"\s+", " ", raw).strip(" .,;:'\"")
    out = []
    m = re.match(r"^(.*?)\s*\((le|la|les|l')\)\s*(.*)$", s, re.I)            # "Mans (le)" -> "Le Mans"
    if m: out.append(f"{m.group(2)} {m.group(1)} {m.group(3)}".strip()); out.append(f"{m.group(2)}{m.group(1)}" if m.group(2).endswith("'") else "")
    base = re.sub(r"\(.*?\)|\(.*$|\[|\]|\{.*", "", s).strip(" .,")
    out.append(base)
    for part in re.split(r"\s+or\s+|\s+al\.\s+|\s*/\s*", base):
        out.append(part.strip())
    out.append(base.replace("-", " ")); out.append(base.replace(" ", "-"))
    out.append(re.sub(r"^(Castle|Abbey of|Priory of|Church of)\s+", "", base))
    out.append(re.sub(r"\s+(Castle|Abbey|Priory|Palace|Park|Manor)$", "", base))
    return [o for o in dict.fromkeys(out) if o and len(norm(o)) >= 3]


def region_key(region):
    """'Normandie, vide Orival' -> 'normandie'; 'No?-mandie' -> 'normandie'; 'Wilts' -> 'wilts'."""
    if not region: return ""
    r = norm(region.split(",")[0]) or norm(region)
    r = r.replace("nomandie", "normandie")
    for f in sorted(FR | set(OTHER_CC), key=len, reverse=True):
        if len(f) > 4 and f in norm(region): return f
    return r


def candidates(raw, region):
    region = region_key(region) if region else ""
    hk = hkey(region) if region else ""
    reg = region
    foreign = reg in FR or reg in OTHER_CC or any(reg.startswith(f) for f in FR if len(f) > 4)
    ccs = ["FR"] if reg in FR else OTHER_CC.get(reg, [])
    out = []
    for v in variants(raw):
        n = norm(v)
        if not foreign:
            out += [(p[0], p[1], f"OS Open Names: {p[4]} ({p[2]}, {p[3]})", TYPE_RANK.get(p[2], 6)) for p in OS.get(n, [])]
            out += [(p[0], p[1], f"Wikidata {p[3]} ({p[4]}, {p[2]})", 2) for p in WD.get(n, [])]
        gpool = [p for p in GN.get(n, []) if (not ccs or p[3] in ccs) and (foreign or p[3] in ("GB", "IE"))]
        out += [(p[0], p[1], f"GeoNames: {p[4]} ({p[3]})", 1) for p in gpool]
        if out: break
    if hk in CENT and out and not foreign:
        c = CENT[hk]
        inside = [o for o in out if hav(o[0], o[1], c[0], c[1]) < 75]   # a namesake outside the printed county is not accepted...
        towns = [o for o in out if o[3] <= 1 and o[2].startswith("OS")]
        if not inside and len({(round(o[0], 1), round(o[1], 1)) for o in towns}) == 1:
            # ...unless the name is a single OS city or town: the printed county is then most likely an OCR slip
            inside = [(towns[0][0], towns[0][1], towns[0][2] + " [county as printed does not match]", towns[0][3])]
        out = inside
    if foreign and reg in FR and reg not in ("burgundy", "bourgogne", "champagne", "france", "flanders", "artois"):
        out = [o for o in out if 42.5 < o[0] < 51.2 and -5.5 < o[1] < 3.6]   # the Plantagenet lands of western France
    return out, hk, foreign


def fuzzy(raw, region, foreign):
    """Last resort: a close spelling (ratio >= 0.86) in the same county or country."""
    region = region_key(region) if region else ""
    hk = hkey(region) if region else ""
    n = norm(variants(raw)[0]) if variants(raw) else norm(raw)
    if len(n) < 5: return []
    if foreign:
        pool = GN
    else:
        pool = OS
    keys = list(pool.keys())
    best = difflib.get_close_matches(n, keys, 3, 0.86)
    out = []
    for b in best:
        for p in pool[b]:
            if foreign and p[3] not in (["FR"] if norm(region) in FR else OTHER_CC.get(norm(region), ["FR"])): continue
            if not foreign and hk in CENT and hav(p[0], p[1], *CENT[hk]) > 60: continue
            out.append((p[0], p[1], ("GeoNames" if foreign else "OS Open Names") + f" (close spelling): {p[4]}", 3))
        if out: break
    return out


def clean_name(src):
    """Modern name from a gazetteer source string."""
    m = re.match(r"^Wikidata Q\d+ \((.+?), [^,]+\)$", src)
    if m: return m.group(1)
    return src.split(": ", 1)[-1].split(" (")[0].replace(" [county as printed does not match]", "")


def load_stays():
    S = []
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "raw_john.csv"))):
        if r["valid"] == "1":
            S.append(dict(monarch="John", date=r["date"], raw=r["place_raw"], region=r["region_raw"], order=0, quality="index", src="Hardy 1835, index"))
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "raw_edward.csv"))):
        S.append(dict(monarch="Edward I", date=r["date"], raw=r["place"], region=r["county"] or r["division"], order=int(r["order"]),
                      quality=r["matched_by"], src="Gough 1900"))
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "raw_henry.csv"))):
        S.append(dict(monarch="Henry II", date=f"{int(r['year']):04d}-{int(r['month']):02d}-{int(r['day']):02d}", raw=r["place"], region=r["region"],
                      order=0, quality=("uncertain " if r["uncertain"] == "1" else "") + r["evidence_type"], src="Eyton 1878", kind=r["kind"]))
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "raw_elizabeth.csv"))):
        S.append(dict(monarch="Elizabeth I", date=r["date"], raw=r["place"], region=r["county"], order=int(r["order"]), quality=r["quality"],
                      src=r["source"]))
    return S


def main():
    S = load_stays()
    keys = Counter((s["monarch"], s["raw"], s["region"]) for s in S)
    placed = {}; how = {}
    amb = {}
    for (mon, raw, reg), n in keys.items():
        mr = MANUAL.get((mon, norm(raw))) or MANUAL.get(("*", norm(raw)))
        if mr:
            la, lo, src = resolve_manual(mr)
            placed[(mon, raw, reg)] = (la, lo, src, mr["modern"], "manual" if la is not None else ("unidentified" if src == "none" else "region"))
            continue
        if norm(reg) in ("england", "wales", "scotland", "ireland", "normandy", "normandie", "anjou", "bretagne", "guienne", "gascony", "poitou", "aquitaine",
                         "maine", "france") and norm(raw) == norm(reg):
            placed[(mon, raw, reg)] = (None, None, "region", raw, "region"); continue
        c, hk, foreign = candidates(raw, reg)
        if not c:
            c = fuzzy(raw, reg, foreign)
        if not c: continue
        best_rank = min(x[3] for x in c)
        c = [x for x in c if x[3] == best_rank] if not (hk in CENT) else c
        uniq = {(round(x[0], 2), round(x[1], 2)) for x in c}
        if len(uniq) == 1 or (hk in CENT and not foreign):
            if hk in CENT and not foreign:
                cc = CENT[hk]; x = min(c, key=lambda x: (x[3], hav(x[0], x[1], cc[0], cc[1]) / 30))
            else:
                x = c[0]
            placed[(mon, raw, reg)] = (x[0], x[1], x[2], clean_name(x[2]), "close spelling" if "close spelling" in x[2] else "gazetteer")
        else:
            amb[(mon, raw, reg)] = c
    # ambiguous names: choose the candidate nearest to where the king is found within three days either side
    import datetime as dt
    byday = defaultdict(list)
    for s in S:
        k = (s["monarch"], s["raw"], s["region"])
        if k in placed and placed[k][0] is not None: byday[(s["monarch"], s["date"])].append(placed[k][:2])
    for k, c in amb.items():
        mon = k[0]; pts = []
        for s in S:
            if (s["monarch"], s["raw"], s["region"]) != k: continue
            d0 = dt.date.fromisoformat(s["date"])
            for dd in range(-3, 4):
                if dd == 0: continue
                pts += byday.get((mon, (d0 + dt.timedelta(days=dd)).isoformat()), [])
        if pts:
            x = min(c, key=lambda x: sorted(hav(x[0], x[1], p[0], p[1]) for p in pts)[len(pts) // 2])
            placed[k] = (x[0], x[1], x[2], clean_name(x[2]), "itinerary context")
        else:
            x = sorted(c, key=lambda x: x[3])[0]
            placed[k] = (x[0], x[1], x[2], clean_name(x[2]), "gazetteer (ambiguous)")
    # outputs
    rows = []
    for s in S:
        k = (s["monarch"], s["raw"], s["region"]); p = placed.get(k)
        s2 = dict(s); s2.pop("kind", None)
        s2.update(lat=round(p[0], 5) if p and p[0] is not None else "", lon=round(p[1], 5) if p and p[0] is not None else "",
                  place=p[3] if p else "", placed_by=p[4] if p else "unplaced", place_source=p[2] if p else "")
        rows.append(s2)
    cols = ["monarch", "date", "order", "raw", "region", "place", "lat", "lon", "placed_by", "place_source", "quality", "src"]
    with open(os.path.join(ROOT, "work", "stays_geocoded.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(rows)
    un = Counter((r["monarch"], r["raw"], r["region"]) for r in rows if r["placed_by"] == "unplaced")
    with open(os.path.join(ROOT, "work", "unplaced.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["monarch", "raw", "region", "rows"])
        for (m, r, g), n in un.most_common(): w.writerow([m, r, g, n])
    for mon in ("John", "Henry II", "Edward I", "Elizabeth I"):
        rr = [r for r in rows if r["monarch"] == mon]
        if not rr: continue
        c = Counter(r["placed_by"] for r in rr)
        print(mon, len(rr), dict(c), "placed share %.3f" % (1 - c["unplaced"] / len(rr)))
    print("top unplaced:", un.most_common(40))


if __name__ == "__main__":
    main()
