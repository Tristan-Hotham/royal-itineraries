"""Step 2. Edward I (1272 to 1307): parse Henry Gough, Itinerary of King Edward the First (1900, 2 vols).

Gough prints one page per month: every day of the month on its own line (day, weekday, Sunday or feast),
then the place or places where the King is found that day, the county, and the record authority
(P.R. Patent Rolls, Cl.R. Close Rolls, F.R. Fine Rolls, W.A. Wardrobe Accounts...).
The OCR keeps the day lines in order but scatters places, counties, ditto marks and authorities.

Method:
  1. Parse Gough's own Index of Places (England, Wales, Scotland, Foreign parts) into place names with
     their county or region and the years and months in which Gough lists the King there.
  2. Walk the daily pages month by month from November 1272 to July 1307, recognising each day line by
     its expected day number and weekday (computed from the Julian calendar), so a garbled number does
     not break the sequence.
  3. For each day, split the text into fragments, drop authorities, ditto marks, feasts and county
     names, and accept a fragment as a place only if it closely matches (difflib ratio >= 0.78) a place
     that Gough's index lists for that same year and month (or >= 0.90 against any indexed place).
Inputs: ../../_data12/itineraries_ocr.json.gz (vol 1) and itineraries_ocr2.json.gz (vol 2), public domain.
Outputs: ../data/raw_edward.csv (one row per day and place), ../data/edward_index.csv (Gough's index).
Run: python3 02_parse_edward.py
"""
import csv, difflib, gzip, json, os, re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
D12 = os.path.join(ROOT, "..", "_data12")
V1 = json.load(gzip.open(os.path.join(D12, "itineraries_ocr.json.gz")))["items"]["itineraryofkinge01gouguoft"]["text"]
V2 = json.load(gzip.open(os.path.join(D12, "itineraries_ocr2.json.gz")))["items"]["itineraryofkinge02gouguoft"]["text"]

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
MABBR = {"jan": 1, "feb": 2, "mar": 3, "march": 3, "apr": 4, "april": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
         "aug": 8, "sept": 9, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def jd(y, m, d):
    a = (14 - m) // 12; y2 = y + 4800 - a; m2 = m + 12 * a - 3
    return d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - 32083


def weekday(y, m, d):  # 0 Monday ... 6 Sunday
    return jd(y, m, d) % 7


def mlen(y, m):
    return [31, 29 if y % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]


# ---------------------------------------------------------------- 1. the index of places
def parse_index():
    L = V2.split("\n")
    st = next(i for i, l in enumerate(L) if "This  Index  is  in  four  divisions" in l)
    div = "England"; entries = []; cur_parent = None; buf = ""
    stream = []
    for l in L[st + 3:]:
        s = l.strip()
        if not s or s.startswith("Index  of") or re.match(r"^[0-9io]{2,4}\s*$", s):
            continue
        if re.match(r"^I+V?\.\s*[—-]\s*(ENGLAND|WALES|SCOTLAND)", s) or re.match(r"^IV\.\s*[—-]\s*FOREIGN", s):
            stream.append(("DIV", s)); continue
        stream.append(("L", s))
    # join into entries: a new entry starts with a line that has "Name ... :" and does not start with a date
    ents = []
    for kind, s in stream:
        if kind == "DIV":
            ents.append(("DIV", s)); continue
        starts_new = (bool(re.match(r'^["“<]?\s*[A-Z\\][^:;]{1,60}?[:;]', s)) or bool(re.match(r"^[A-Z][\w'()\- ]{2,40},\s*[A-Z][\w'. ]{1,20}-\s+1[23]\d\d", s))) \
            and not re.match(r"^(1[23]\d\d|(Jan|Feb|Mar|Apr|May|June|July|Aug|Sept|Oct|Nov|Dec)\b)", s)
        if starts_new or not ents or ents[-1][0] == "DIV":
            ents.append(["E", s])
        else:
            ents[-1][1] += " " + s
    out = []; parent_county = None; parent_open = False
    for e in ents:
        if e[0] == "DIV":
            s = e[1].upper()
            div = "Wales" if "WALES" in s else "Scotland" if "SCOTLAND" in s else "Foreign" if "FOREIGN" in s else "England"
            continue
        s = e[1]
        mh = re.search(r"[:;]|-(?=\s+1[23]\d\d)", s)
        head, rest = (s[:mh.start()], s[mh.end():]) if mh else (s, "")
        head = head.strip().strip('"“” ')
        has_dates = bool(re.search(r"1[23]\d\d", rest))
        if "," in head:
            name, _, county = head.partition(",")
            parent_county = county.strip(); is_sub = False
            parent_open = not has_dates          # "Acton, Chester :" followed by its sub-entries
        elif parent_open:
            name, county, is_sub = head, parent_county, True
        else:
            name, county, is_sub = head, head, False   # county towns such as "York:" or "Chester:"
        name = re.sub(r"\s+", " ", name).strip('"“”<f ').strip()
        ym = []
        for m in re.finditer(r"(1[23]\d\d)\s*[.,]\s*((?:(?:Jan|Feb|Mar|Apr|May|June?|July?|Aug|Sept?|Oct|Nov|Dec)[a-z]*\s*\.?\s*[,;]?\s*)+)", rest.replace("T2", "12").replace("I2", "12").replace("i2", "12")):
            y = int(m.group(1))
            for mo in re.findall(r"(Jan|Feb|Mar|Apr|May|June?|July?|Aug|Sept?|Oct|Nov|Dec)", m.group(2)):
                ym.append((y, MABBR[mo.lower()] if mo.lower() in MABBR else MABBR[mo.lower()[:3]]))
        out.append(dict(name=name, county=(county or "").strip(" ."), division=div, sub=int(is_sub), ym=sorted(set(ym))))
    return out


IDX = parse_index()
by_ym = defaultdict(list)
for i, e in enumerate(IDX):
    for ym in e["ym"]: by_ym[ym].append(i)
def NORM(s):
    s = s.lower().replace("saint", "st").replace("iipon", "upon").replace("tiveed", "tweed").replace("benvick", "berwick").replace("vestmmster", "westminster")
    s = s.replace("london, tower", "tower of london").replace("ashridt'e", "ashridge").replace("ocliham", "odiham")
    s = re.sub(r"\(.*?\)|\(.*$|probably|perhaps", "", s)
    return re.sub(r"[^a-z]", "", s)


IDXN = [NORM(e["name"]) for e in IDX]

COUNTY_WORDS = set()
for e in IDX:
    for w in re.split(r"[ ,.()]+", e["county"]):
        if len(w) > 2: COUNTY_WORDS.add(w.lower())
COUNTY_WORDS |= {"chester", "flint", "cumb", "salop", "wilts", "berks", "bucks", "oxon", "kent", "essex", "surrey", "sussex", "notts", "york", "lincoln",
                 "glouc", "gloucr", "hants", "ston", "midd", "middx", "norfolk", "suffolk", "devon", "dorset", "somerset", "herts", "beds", "hunt", "camb", "cam",
                 "carn", "angl", "fife", "forfar", "perth", "berwick", "roxburgh", "kincard", "haddn", "edinburgh", "linlithgow", "lanark", "ayr", "dumfries",
                 "gascony", "guienne", "picardy", "flanders", "ponthieu", "normandy", "beam", "aquitaine", "burgundy", "savoy", "italy", "france"}
FEAST = re.compile(r"(after|trinity|advent|lent|epiphany|easter|christmas|septuagesima|sexagesima|quinquagesima|palm|ash|passion|pentecost|whit|"
                   r"rogation|ascension|octave|lady|michaelmas|nativity|circumcision|mid-lent|low s|good f|corpus|holy|day$)", re.I)
AUTH = re.compile(r"^(?:[A-Z][a-z]{0,2}\.\s?){1,3}$|^(MSS|Inq|Wykes|Prynne|Rymer|Lib|Pat|Claus|Rot|Chanc|Exch|Liberate|Ann|Chron|Fine|Close|Wardrobe|Misc|Royal|Letters|Writ|Cal|Rolls)")


STOP = {"the", "in", "at", "here", "see", "and", "of", "probably", "near", "or", "perhaps", "on", "to", "from", "with", "by", "a", "an", "this", "king", "edward"}


def candidates(text):
    """Split one line of a day's OCR text into (fragment, position in line, is a county word)."""
    out = []; pos = 0
    for frag in re.split(r"\s{3,}|\t", text):
        f = re.sub(r"\s+", " ", frag).strip(" ,.;:'\"`»„()[]|/\\*")
        f = re.sub(r"\s*\d+$", "", f)          # footnote numbers
        f = re.sub(r"^\(?near\)?\s*|\s*\((near|in [^)]*|\?)\)?", "", f).strip()
        f = re.sub(r"^.*?\b(after|in)\s+(Trinity|Advent|Lent|Epiphany|Easter|Ascension|Pentecost)\b\s*", "", f).strip()
        ws = f.split()
        if len(ws) > 1 and ws[-1].lower().strip(".,'") in COUNTY_WORDS | {"midd'x", "wilts", "guienne", "gascony", "so'ton", "s'ton"}:
            f = " ".join(ws[:-1]).strip(" ,")
        if len(re.sub(r"[^A-Za-z]", "", f)) < 3: continue
        if f.split()[0].lower().strip(".,") in STOP or f[0].islower(): pos += 1; continue
        if AUTH.search(f) or re.search(r"[A-Z]\.[A-Z]", f) or ("." in f and len(f) < 7): continue
        if FEAST.search(f) and not re.search(r"(Westminster|Ashridge|Holy Island|Lady)", f): pos += 1; continue
        out.append((f, pos, f.lower().strip(".") in COUNTY_WORDS)); pos += 1
    return out


def match(frag, y, m):
    n = NORM(frag)
    if len(n) < 3: return None
    best, bi = 0, None
    for i in by_ym.get((y, m), []):
        r = difflib.SequenceMatcher(None, n, IDXN[i]).ratio()
        if r > best: best, bi = r, i
    if best >= 0.78: return bi, best, "month"
    if n in IDXN and IDX[IDXN.index(n)].get("supplementary"):
        return IDXN.index(n), 1.0, "supplement"
    # fall back to any indexed place, but demand a much closer match
    c = difflib.get_close_matches(n, IDXN, 1, 0.9)
    if c:
        i = IDXN.index(c[0]); return i, difflib.SequenceMatcher(None, n, c[0]).ratio(), "any"
    return None


# ---------------------------------------------------------------- 2. the daily pages
WD = {0: ("M", "m", "ivi", "IVI", "M."), 1: ("T", "Tu", "t", "T."), 2: ("W", "w", "VV", "\\V", "W."), 3: ("Th", "Fh", "Tli", "Tb", "Th.", "Tk"),
      4: ("F", "I\"", "P", "F.", "f"), 5: ("S", "5", "s", "S."), 6: ()}
ALLWD = set(sum(WD.values(), ()))


def wd_fits(tok, ew):
    """Does an OCR weekday token fit the expected weekday ew (0 Monday ... 6 Sunday)?"""
    if ew != 6: return tok in WD[ew]
    return len(tok) <= 3 and tok not in ALLWD and not tok[:1].isdigit()


def daynum(tok):
    t = tok.replace("i", "1").replace("I", "1").replace("l", "1").replace("O", "0").replace("o", "0").replace(",", "1").replace("Q", "9").replace(" ", "").replace(".", "")
    return int(t) if t.isdigit() else None


HEAD_RE = re.compile(r"[A4]\s?[.,]\s?D\s?[.,t]?\s+([1Il][23][0-9IlO]{2})\s*(?:[-—]\s*(\d{1,2}))?")


def walk():
    """Walk the daily pages; returns {(y, m, d): [text lines]} and the number of day lines found per month."""
    lines = V1.split("\n")[2555:] + V2.split("\n")[2100:]
    y, m = 1272, 11; d_next = 16  # Henry III died 16 November 1272; Gough starts there
    hdr = None                     # (first year, has second year) from the latest running head
    days = defaultdict(list); cur = None; found = defaultdict(int)
    for raw in lines:
        s = raw.rstrip(); st = s.strip()
        if not st: continue
        if (y, m) > (1307, 7): break
        h = HEAD_RE.search(st)
        if h and len(st) < 60:
            yy = int(h.group(1).replace("I", "1").replace("l", "1").replace("O", "0"))
            if 1272 <= yy <= 1307: hdr = (yy, bool(h.group(2)))
            cur = None; continue
        mh = re.match(r"^([A-Z]{3,10})\.?\s*$", st)
        if mh:
            c = difflib.get_close_matches(mh.group(1).lower(), MONTHS, 1, 0.7)
            if c:
                mi = MONTHS.index(c[0]) + 1
                if hdr:
                    ny = hdr[0] + 1 if (hdr[1] and mi <= 3) else hdr[0]
                else:
                    ny = y + (1 if mi < m else 0)
                ahead = (ny * 12 + mi) - (y * 12 + m)
                if 1 <= ahead <= 4 or (ahead == 0 and d_next <= 2):
                    y, m, d_next = ny, mi, 1; cur = None
                continue
        if d_next > mlen(y, m):
            # month finished but no heading seen: accept an early day of the next month if its weekday fits
            mm = re.match(r"^([0-9iIlO,Q]{1,2})\s+(\S+)", st)
            if mm:
                n = daynum(mm.group(1)); nm, ny = (m % 12) + 1, y + (1 if m == 12 else 0)
                if n and n <= 10 and wd_fits(mm.group(2), weekday(ny, nm, n)):
                    y, m, d_next = ny, nm, n
        if d_next <= mlen(y, m):
            mm = re.match(r"^([0-9iIlO,Q]{1,2}(?:\s[0-9])?|[0-9]\.[0-9])\s+(\S+)(.*)$", st) or re.match(r"^([0-9iIlO,Q]{1,2})()()$", st)
            if mm:
                n = daynum(mm.group(1)); wd_tok = mm.group(2)
                wd_ok = wd_fits(wd_tok, weekday(y, m, d_next))
                skip_ok = False
                if n in (d_next + 1, d_next + 2, d_next + 3) and n <= mlen(y, m):
                    skip_ok = wd_fits(wd_tok, weekday(y, m, n))
                if (n == d_next and (wd_ok or wd_tok == "" or len(mm.group(3)) < 60)) or (n is None and wd_ok) or skip_ok:
                    if skip_ok: d_next = n
                    cur = (y, m, d_next); found[(y, m)] += 1; d_next += 1
                    days[cur].append(mm.group(3))
                    continue
        if cur is not None:
            if re.match(r"^\d{1,2}\s+[\"“A-Z]", st) and (cur[2] >= mlen(*cur[:2]) - 1 or len(st) > 45): continue  # footnotes
            if re.match(r"^\d{1,2}\s+(In|On|A|The|Now|Or|Probably|Near|Here|See|This|Called|Perhaps)\b", st): continue
            if len(st) > 90: continue   # prose notes
            days[cur].append(s)
    return days, found


def supplement(days):
    """Places missing from the OCR of Gough's index: fragments seen in the place column on at least two
    days that are not matched to the index but are, letter for letter, a populated place in OS Open Names
    or a town in GeoNames (Britain, Ireland, France, the Low Countries, Spain, Italy)."""
    import collections
    os_names = set()
    with open(os.path.join(ROOT, "..", "osnames_gb.tsv")) as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            if r["type"] == "populatedPlace":
                os_names.add(NORM(r["name1"]))
    gn = json.load(open(os.path.join(ROOT, "work", "geonames_cities.json")))
    gnames = {NORM(n) for n, *_ in gn}
    cnt = collections.Counter()
    for (y, m, d), texts in days.items():
        for t in texts:
            for f, pos, is_cty in candidates(t):
                if is_cty: continue
                if not match(f, y, m): cnt[f] += 1
    extra = []
    for f, c in cnt.items():
        n = NORM(f)
        if c >= 2 and len(n) >= 4 and (n in os_names or n in gnames) and n not in IDXN:
            extra.append(f)
    extra += ["Ashridge", "London, Tower", "Berwick-upon-Tweed", "Bury St. Edmunds", "Havering-atte-Bower", "Wimborne", "Finchale", "Merioneth", "Anglesey"]
    return sorted(set(extra), key=NORM)


def join_hyphens(texts):
    out = []
    for t in texts:
        if out and re.search(r"[A-Za-z]-\s*$", out[-1].split("   ")[0].strip() if out[-1].strip() else "") and t.strip():
            first, _, rest = t.strip().partition("   ")
            out[-1] = out[-1].split("   ")[0].strip() + first.strip() + ("   " + rest if rest else "")
        else:
            out.append(t)
    return out


def main():
    days, found = walk()
    days = {k: join_hyphens(v) for k, v in days.items()}
    extra = supplement(days)
    print("supplementary names:", len(extra), extra[:80])
    for f in extra:
        IDX.append(dict(name=re.sub(r"\s+", " ", f), county="", division="", sub=0, ym=[], supplementary=1)); IDXN.append(NORM(f))
    rows = []; nd = nplaced = 0
    for (y, m, d), texts in sorted(days.items()):
        nd += 1; seen = []
        for t in texts:
            for f, pos, is_cty in candidates(t):
                if is_cty and pos > 0: continue            # the county column beside a place
                r = match(f, y, m)
                if not r: continue
                if is_cty and any(NORM(IDX[s0[0]]["county"])[:5] == NORM(f)[:5] for s0 in seen) and NORM(f) != NORM(IDX[seen[-1][0]]["name"]):
                    continue                                # a county printed on its own line under its place
                if r[0] not in [s0[0] for s0 in seen]:
                    seen.append((r[0], f, r[1], r[2]))
        if seen: nplaced += 1
        for k, (i, f, sc, how) in enumerate(seen):
            e = IDX[i]
            rows.append(dict(date=f"{y:04d}-{m:02d}-{d:02d}", order=k, ocr=f, place=e["name"], county=e["county"], division=e["division"],
                             score=round(sc, 3), matched_by=how))
    with open(os.path.join(ROOT, "data", "raw_edward.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
    with open(os.path.join(ROOT, "data", "edward_index.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["name", "county", "division", "sub_entry", "year_months"])
        for e in IDX: w.writerow([e["name"], e["county"], e["division"], e["sub"], ";".join(f"{a}-{b:02d}" for a, b in e["ym"])])
    tot = jd(1307, 7, 7) - jd(1272, 11, 16) + 1
    json.dump(dict(days_in_span=tot, day_lines_found=nd, days_with_place=nplaced, rows=len(rows), index_entries=len(IDX) - len(extra),
                   index_entries_with_dates=sum(1 for e in IDX if e["ym"]), supplementary_names=len(extra)),
              open(os.path.join(ROOT, "work", "edward_parse.json"), "w"))
    print("index entries", len(IDX), "with dates", sum(1 for e in IDX if e["ym"]))
    print("days in reign", tot, "day lines found", nd, "days with a place", nplaced, "rows", len(rows))
    short = [(k, v) for k, v in found.items() if v < mlen(*k) - 1]
    print("months with missing day lines:", len(short), short[:20])
    for dd in ("1277-08-01", "1282-06-10", "1296-08-17", "1305-08-23", "1307-07-07", "1290-11-28"):
        print(dd, [(r["place"], r["county"]) for r in rows if r["date"] == dd])


if __name__ == "__main__":
    main()
