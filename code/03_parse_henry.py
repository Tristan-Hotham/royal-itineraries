"""Step 3. Henry II (1154 to 1189): extract dated stays from R. W. Eyton, Court, Household and Itinerary
of King Henry II (1878).

Eyton is not a table but a dated narrative: each paragraph starts with a date ("Feb. 2.", "c. Jan. 18.")
under a year heading ("A.D. 1170."), and the place where the King is found is repeated in the margin,
which the OCR folds into the end of the line. I extract a stay when a dated paragraph says that the
King (K. Henry, the King, King Henry) is, keeps, holds, reaches, lands, spends, remains... at or in a
named place, and the place is in Eyton's own Index of Places (or is a known region such as Normandy).
Statements with "probably", "perhaps", "about" or a "c." date are kept but flagged as uncertain.
I also collect every "Christmas at <place>" statement for the Christmas courts.

Input: Internet Archive OCR of courthouseholdit00eyto (public domain), ../../_data12/itineraries_ocr.json.gz.
Output: ../data/raw_henry.csv
Run: python3 03_parse_henry.py
"""
import csv, gzip, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
T = json.load(gzip.open(os.path.join(ROOT, "..", "_data12", "itineraries_ocr.json.gz")))["items"]["courthouseholdit00eyto"]["text"]
L = T.split("\n")
IDX_START = next(i for i, l in enumerate(L) if re.match(r"^INDEX\s+O[FP]\s+PLACES", l.strip()))

# ---------------------------------------------------------------- Eyton's index of places
REGIONS = {"normandy", "normandie", "bretagne", "brittany", "anjou", "maine", "poitou", "aquitaine", "guienne", "gascony", "england", "ireland",
           "wales", "scotland", "france", "touraine", "berri", "limousin", "auvergne", "saintonge", "angoumois", "vexin", "flanders", "toulouse",
           "perigord", "quercy", "la marche", "the continent", "kent", "the north"}
index_names = {}
for l in L[IDX_START:]:
    s = l.strip()
    m = re.match(r"^(?:St\.\s+)?([A-Z][A-Za-z'\-]+(?:\s+(?:le|la|de|du|des|en|sur|St\.|[A-Z][a-z'\-]+)){0,3})\s*(?:\(([^)]*)\))?\s*(?:Abbey|Castle|Cast\.|Priory|Nunnery|Mon\.|Abb\.)?,?\s*[0-9]", s)
    if m:
        nm = (("St. " if s.startswith("St.") else "") + m.group(1)).strip()
        index_names.setdefault(nm.lower(), (nm, (m.group(2) or "").strip()))

# keep index names that carry a region in brackets, or that are towns in OS Open Names or GeoNames
_gaz = set()
with open(os.path.join(ROOT, "..", "osnames_gb.tsv")) as _fh:
    for _r in csv.DictReader(_fh, delimiter="\t"):
        if _r["type"] == "populatedPlace": _gaz.add(_r["name1"].lower())
for _n, *_ in json.load(open(os.path.join(ROOT, "work", "geonames_cities.json"))): _gaz.add(_n.lower())
index_names = {k: v for k, v in index_names.items() if v[1] or k in _gaz or k.replace("st. ", "saint-") in _gaz}
for _a in ("Bayeux", "Bordeaux", "Rouen", "Poitiers", "Lisieux", "Angers", "Chinon", "Sees", "Le Mans", "Bonneville-sur-Touques"):
    index_names.setdefault(_a.lower(), (_a, ""))

MON = {"jan": 1, "feb": 2, "peb": 2, "mar": 3, "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8,
       "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12, "dee": 12, "doc": 12, "deo": 12}
DATE_RE = re.compile(r"^(c\.\s*|circa\s*|about\s*)?(Jan|Feb|Peb|Mar|Apr|April|May|June|Jun|July|Jul|Aug|Sept|Sep|Oct|Nov|Dec|Dee|Doc|Deo)\.?\s*([0-9ilIoOsS]{1,2})\s*[.,]", re.I)
YEAR_RE = re.compile(r"^A\.\s*D\.\s*(11[5-8][0-9])\.?\s*$")
SUBJ = r"(?:K\.\s*Henry|The\s+King|the\s+King|King\s+Henry|K\.\s*H\.)(?!'s|\s*'s)"
VERB = (r"(?:is|was|are|keeps?|kept|holds?|held|reach(?:es|ed)|arrives?|arrived|lands?|landed|spends?|spent|remains?|remained|stays?|stayed|"
        r"returns?|returned|comes?|came|goes|went|proceeds?|proceeded|passes|passed|crosses|crossed|meets?|met|visits?|visited|"
        r"celebrates?|celebrated|probably|still|again|now|at)")
PLACE = r"([A-Z][A-Za-z'\-]+(?:\s+(?:le|la|de|du|des|en|sur|St\.|Saint|[A-Z][a-z'\-]+)){0,3})"
STAY_RE = re.compile(SUBJ + r"\b[^.;]{0,70}?\b" + VERB + r"\b[^.;]{0,40}?\b(?:at|in|to|into)\s+" + PLACE)
CHARTER_RE = re.compile(r"(?:[Cc]harter|[Ww]rit|[Pp]recept|[Ll]etter|[Gg]rant|[Cc]onfirmation)s?\b[^.;]{0,80}?\b(?:dated|passed|tested|attested|given)\s+(?:apud\s+\w+\s*,?\s*)?(?:at|in)\s+" + PLACE)
XMAS_RE = re.compile(r"Christmas(?:\s+court)?\s+(?:at|in)\s+" + PLACE)


def dnum(s):
    s = s.replace("i", "1").replace("l", "1").replace("I", "1").replace("o", "0").replace("O", "0").replace("s", "5").replace("S", "5")
    return int(s) if s.isdigit() else None


OLD_SPELL = {"Baieux": "Bayeux", "Bourdeaux": "Bordeaux", "Bouen": "Rouen", "Poictiers": "Poitiers", "Liseux": "Lisieux", "Angiers": "Angers",
             "Chinum": "Chinon", "Bonneville": "Bonneville-sur-Touques", "Seez": "Sees", "Mans": "Le Mans"}
NOT_PLACES = {"william", "richard", "hugh", "john", "roger", "robert", "march", "henry", "geoffrey", "geoffry", "walter", "ralph", "thomas", "gilbert",
              "simon", "peter", "stephen", "bernard", "philip", "matthew", "reginald", "alan", "adam", "eustace", "baldwin", "jordan", "nigel",
              "theobald", "becket", "may", "earl", "bishop", "king", "queen", "prince", "abbot", "prior", "dean", "master", "pope", "count",
              "comte", "eleanor", "louis", "william de", "richard de", "arnulf", "rotrou", "jocelin", "warin", "manasser", "humphrey", "saher"}


def known(p):
    """Return (canonical name, region or '', kind) if p is in Eyton's index or a known region."""
    q = p.strip().rstrip(".,")
    q = OLD_SPELL.get(q, q)
    if q.lower() in NOT_PLACES or q.split()[0].lower() in NOT_PLACES: return None
    for cand in (q, " ".join(q.split()[:2]), q.split()[0]):
        if cand.lower() in REGIONS: return cand, "", "region"
        if cand.lower() in index_names:
            nm, reg = index_names[cand.lower()]
            return nm, reg, "place"
    return None


def main():
    rows, xmas = [], []
    year = None; dated = None; uncertain = False; buf = []

    def flush():
        if dated is None or not buf: return
        txt = re.sub(r"\s+", " ", " ".join(buf))
        txt = re.sub(r"(\w)-\s+(\w)", r"\1\2", txt)
        sents = re.split(r"(?<=[.;])\s+(?=[A-Z(])", txt)
        got = None
        for sent in sents:
            m = STAY_RE.search(sent)
            if m and known(m.group(1)):
                got = (m, sent, "narrative"); break
        if not got:
            for sent in sents:
                m = CHARTER_RE.search(sent)
                if m and known(m.group(1)):
                    got = (m, sent, "charter"); break
        if not got:
            # the margin: a place that ends a line of this paragraph and is also named earlier in it
            for ln in buf:
                c = re.sub(r"\s+", " ", ln).strip()
                mm = re.search(r"([A-Z][A-Za-z'\-]+(?: (?:le|la|de|du|en|sur|St\.|[A-Z][a-z'\-]+)){0,2})\.?$", c)
                if mm and known(mm.group(1)) and known(mm.group(1))[2] == "place":
                    nm = mm.group(1)
                    if txt.count(nm[:5]) >= 2:
                        got = (mm, c, "margin"); break
        if got:
            m, sent, ev = got; k = known(m.group(1))
            unc = uncertain or bool(re.search(r"\b(probably|perhaps|possibly|seems|likely|about|may have)\b", sent))
            rows.append(dict(year=dated[0], month=dated[1], day=dated[2], place=k[0], region=k[1], kind=k[2], evidence_type=ev,
                             uncertain=int(unc), evidence=sent[:160]))
        for m in XMAS_RE.finditer(txt):
            k = known(m.group(1))
            if k and dated[1] in (11, 12, 1):
                xmas.append(dict(year=dated[0] if dated[1] != 1 else dated[0] - 1, place=k[0], region=k[1], kind=k[2], evidence=m.group(0)))

    for l in L[:IDX_START]:
        s = l.strip()
        if not s: continue
        ym = YEAR_RE.match(s)
        if ym:
            flush(); buf = []; dated = None
            year = int(ym.group(1)); continue
        dm = DATE_RE.match(s)
        if dm and year:
            flush(); buf = []
            mo = MON[dm.group(2).lower()[:4] if dm.group(2).lower()[:4] in MON else dm.group(2).lower()[:3]]
            d = dnum(dm.group(3))
            if d is None or not (1 <= d <= 31): dated = None; continue
            dated = (year, mo, d); uncertain = bool(dm.group(1))
            buf = [s[dm.end():]]
            continue
        if re.match(r"^\d\s+[A-Z*]", s) or re.match(r"^[0-9]{1,3}\s*$", s) or "ITINERARY" in s.upper():
            continue  # footnotes, page numbers and running heads
        if dated is not None and len(buf) < 12:
            buf.append(s)
    flush()
    # one row per date: keep the first statement for a date
    seen = set(); out = []
    for r in rows:
        k = (r["year"], r["month"], r["day"])
        if k in seen: continue
        seen.add(k); out.append(r)
    with open(os.path.join(ROOT, "data", "raw_henry.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, list(out[0])); w.writeheader(); w.writerows(out)
    xs = {}
    for x in xmas: xs.setdefault(x["year"], x)
    with open(os.path.join(ROOT, "data", "raw_henry_christmas.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, ["year", "place", "region", "kind", "evidence"]); w.writeheader(); w.writerows([xs[k] for k in sorted(xs)])
    print("index names", len(index_names), "dated stays", len(out), "places", sum(r["kind"] == "place" for r in out),
          "regions", sum(r["kind"] == "region" for r in out), "uncertain", sum(r["uncertain"] for r in out))
    print("christmas", [(k, xs[k]["place"]) for k in sorted(xs)])
    import collections
    print(collections.Counter(r["place"] for r in out).most_common(30))


if __name__ == "__main__":
    main()
