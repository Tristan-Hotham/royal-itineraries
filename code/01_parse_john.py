"""Step 1. King John (1199 to 1216): parse the index to T. D. Hardy's Itinerary of King John (1835).

Hardy's day-by-day table is printed in two interleaved columns, which the OCR scrambles. His index,
by contrast, is one column: each place (with county or French province) followed by calendar year,
regnal year ("an."), month and days. I parse the index into one row per place and day.

The OCR sometimes separates the year labels of a long entry (Westminster, Winchester...) from its
month lines. So each place entry is read as two ordered sequences, labels (year, regnal year) and
month lines (month, days), and the month lines are assigned to the labelled years by a small dynamic
programme: years in printed order, months non-decreasing within a year, years printed on the same
line as a month respected, and as many years as possible whose months imply exactly the regnal years
printed for that year (John's regnal years ran from Ascension Day, 27 May 1199).
Each row keeps how its year was found ("inline" or "assigned") and whether the regnal year agrees.

Input: Internet Archive OCR of descriptionofpat00hard (public domain), ../../_data12/itineraries_ocr2.json.gz.
Output: ../data/raw_john.csv
Run: python3 01_parse_john.py
"""
import csv, difflib, gzip, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
SRC = os.path.join(ROOT, "..", "_data12", "itineraries_ocr2.json.gz")


def easter_julian(y):
    a, b, c = y % 4, y % 7, y % 19
    d = (19 * c + 15) % 30; e = (2 * a + 4 * b - d + 34) % 7
    m = (d + e + 114) // 31; day = (d + e + 114) % 31 + 1
    return m, day


def jd(y, m, d):
    """Julian-calendar date to Julian day number."""
    a = (14 - m) // 12; y2 = y + 4800 - a; m2 = m + 12 * a - 3
    return d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - 32083


ASC = {y: jd(y, *easter_julian(y)) + 39 for y in range(1195, 1220)}
assert ASC[1199] == jd(1199, 5, 27)
START, END = jd(1199, 5, 27), jd(1216, 10, 19)


def regnal(y, m, d):
    return (y - 1198) if jd(y, m, d) >= ASC[y] else (y - 1199)


def valid(y, m, d):
    md = [31, 29 if y % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return 1 <= m <= 12 and 1 <= d <= md[m - 1]


def num(s):
    s = s.replace("I", "1").replace("l", "1").replace("O", "0").replace("o", "0").replace("S", "5").replace("J", "1").replace("b", "6").replace("L", "")
    s = re.sub(r"\s+", "", s)
    return int(s) if s.isdigit() else None


MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                           "september", "october", "november", "december"])}
ABBR = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}


def month_of(w):
    w = w.lower().replace(" ", "").strip(".")
    if w in MONTHS: return MONTHS[w]
    if w in ABBR: return ABBR[w]
    if len(w) >= 4:
        c = difflib.get_close_matches(w, list(MONTHS), 1, 0.72)
        if c: return MONTHS[c[0]]
    return None


def parse_date_line(l):
    """(year, an, month, [days]) if the line is a date line, else None."""
    l = re.sub(r"See also.*$", "", l)
    l = l.replace("»", ".").replace("\\", "1").replace('"', "").replace("]", "1").replace("«", ".").replace("•", ".")
    l = re.sub(r"(\d)[:'^](\d)", r"\1\2", l).replace("'", "").replace("^", ".").replace("<", "")
    l = re.sub(r"(?<=\d)G|\bG\b", "6", l)
    l = re.sub(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)s\b", r"\1 8", l)
    rest = l.strip().lstrip(".,'` "); year = an = month = None
    m = re.match(r"^([1Il]\s{0,2}[0-9Il]\s{0,2}[0-9OIl]\s{0,2}[0-9OIl])\s*(?:[.,\-]|(?=\s+a[nm]))\s*", rest)
    if m:
        year = num(m.group(1)); rest = rest[m.end():]
    m = re.match(r"^(?:a[nm]|\.?'?in)\s*[.,]?\s*([^.,:]{0,5}?)\s*(?:[.,:]|$)\s*", rest)
    if m:
        an = num(m.group(1)); an = an if an and 1 <= an <= 18 else -1; rest = rest[m.end():]
    m = re.match(r"^([A-Za-z][A-Za-z. ]{2,12}?)\s*,?\s*(?=\s[0-9IlO]|[0-9]|$)", rest)
    if m and re.search(r"[a-z]{2}", m.group(1)):
        mo = month_of(m.group(1))
        if mo is None: return None
        month = mo; rest = rest[m.end():]
    rest = re.sub(r"\b[IlO]{1,2}\b", lambda x: num(x.group(0)) is not None and str(num(x.group(0))) or x.group(0), rest)
    if re.search(r"[A-Za-z]", rest): return None
    days = [t for t in re.split(r"[,.;:]", rest) if t.strip()]
    if year is None and an is None and month is None and not days: return None
    return year, an, month, days


def assign_years(labels, items):
    """labels: list of (year, an) in order; items: list of dict(month, days, inline_year).
    Returns a list of years, one per item, or None."""
    years = []
    for y, a in labels:
        if y is not None and (not years or years[-1] != y): years.append(y)
    ans = {}
    for y, a in labels:
        if y is not None and a and a > 0: ans.setdefault(y, set()).add(a)
    # labels without a calendar year but with an regnal year belong to the last calendar year before them
    cur = None
    for y, a in labels:
        if y is not None: cur = y
        elif a and a > 0 and cur is not None: ans.setdefault(cur, set()).add(a)
    k, n = len(items), len(years)
    if n == 0: return None
    NEG = -10 ** 9

    def gscore(i0, i1, j):
        y = years[j]; implied = set(); lastm = 0
        for it in items[i0:i1]:
            if it["inline_year"] is not None and it["inline_year"] != y: return NEG
            if it["month"] < lastm: return NEG
            lastm = it["month"]
            for d in it["days"]:
                if valid(y, it["month"], d): implied.add(regnal(y, it["month"], d))
        return 2 if (y in ans and implied == ans[y]) else (1 if y not in ans else 0)

    dp = [[NEG] * (n + 1) for _ in range(k + 1)]; bk = {}
    dp[0][0] = 0
    for j in range(1, n + 1):
        for i1 in range(1, k + 1):
            best = NEG
            for i0 in range(j - 1, i1):
                if dp[i0][j - 1] == NEG: continue
                s = gscore(i0, i1, j - 1)
                if s == NEG: continue
                if dp[i0][j - 1] + s > best: best = dp[i0][j - 1] + s; bk[(i1, j)] = i0
            dp[i1][j] = best
    if dp[k][n] == NEG: return None
    out = [None] * k; i1 = k
    for j in range(n, 0, -1):
        i0 = bk[(i1, j)]
        for i in range(i0, i1): out[i] = years[j - 1]
        i1 = i0
    return out


def main():
    text = json.load(gzip.open(SRC))["items"]["descriptionofpat00hard"]["text"]
    lines = text.split("\n")
    start = next(i for i, l in enumerate(lines) if "INDEX  TO  THE  ITINERARY" in l)
    end = next(i for i in range(len(lines) - 1, 0, -1) if lines[i].startswith("London:"))
    entries, cur, header_buf, last_date = [], None, [], False
    for raw in lines[start:end]:
        l = raw.strip()
        if not l or "INDEX  TO  THE  ITINERARY" in l or re.search(r"\s(—|-)\s*\S{2,6}\.?\s*$", l):
            continue
        p = parse_date_line(l)
        if p and header_buf and p[0] is None and p[1] is None and p[2] is None:
            p = None  # a bare number straight after a heading is part of the heading
        if p:
            if header_buf and len(" ".join(header_buf)) < 40 and re.search(r"\bc[o0][nu][tlif]\w{0,2}\.?\s*$", " ".join(header_buf), re.I) and cur is not None:
                header_buf = []          # a page head such as "GILLINGHAM cont." continues the entry
            if header_buf:
                h = re.sub(r"\s+", " ", " ".join(header_buf)); header_buf = []
                nm, _, rest = h.partition(",")
                cur = dict(place=nm.strip(), region=re.split(r"[.(]", rest.strip())[0].strip(), labels=[], items=[], header=h)
                entries.append(cur)
            if cur is None: continue
            y, a, mo, days = p
            if y is not None or a is not None:
                cur["labels"].append((y, a))
            dn = [d for d in (num(t) for t in days) if d is not None]
            if mo is not None:
                cur["items"].append(dict(month=mo, days=dn, inline_year=y))
            elif dn and cur["items"]:
                cur["items"][-1]["days"] += dn  # continuation of the previous month line
            last_date = True
        else:
            w0 = re.split(r"[\s.,]+", l)[0]
            if re.match(r"^[0-9(){}]", l) or (len(w0) >= 3 and month_of(w0)) or len(re.sub(r"[^A-Za-z]", "", l)) < 3:
                continue  # a garbled date fragment, never a place heading
            if last_date: header_buf = []
            header_buf.append(l); last_date = False

    rows, nfail = [], 0
    for e in entries:
        # fix calendar years outside the reign from the regnal year printed beside them
        labels = []
        for y, a in e["labels"]:
            if y is not None and not (1199 <= y <= 1216):
                y = None if not (a and a > 0) else None
            labels.append((y, a))
        e["labels"] = labels
        for it in e["items"]:
            if it["inline_year"] is not None and not (1199 <= it["inline_year"] <= 1216): it["inline_year"] = None
        yrs = assign_years(labels, e["items"])
        detached = any(it["inline_year"] is None for it in e["items"])
        if yrs is None:
            nfail += 1
            yrs = []; cy = None
            for it in e["items"]:  # fall back to carrying the last inline year forward
                cy = it["inline_year"] or cy; yrs.append(cy)
        for it, y in zip(e["items"], yrs):
            for d in it["days"]:
                if y is None: continue
                ok = valid(y, it["month"], d) and START <= jd(y, it["month"], d) <= END if valid(y, it["month"], d) else False
                rows.append(dict(place_raw=e["place"], region_raw=e["region"], date=f"{y:04d}-{it['month']:02d}-{d:02d}" if ok else "",
                                 year=y, month=it["month"], day=d, year_from="inline" if it["inline_year"] == y else "assigned",
                                 valid=int(bool(ok))))
    cols = ["place_raw", "region_raw", "date", "year", "month", "day", "year_from", "valid"]
    with open(os.path.join(ROOT, "data", "raw_john.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(rows)
    ok = [r for r in rows if r["valid"]]
    json.dump(dict(index_entries=len(entries), dp_failures=nfail, rows=len(rows), valid=len(ok),
                   assigned_year=sum(r["year_from"] == "assigned" for r in ok), distinct_days=len({r["date"] for r in ok})),
              open(os.path.join(ROOT, "work", "john_parse.json"), "w"))
    print("entries", len(entries), "DP failures", nfail, "rows", len(rows), "valid", len(ok),
          "assigned-year rows", sum(r["year_from"] == "assigned" for r in ok), "distinct days", len({r['date'] for r in ok}))
    for r in ok:
        if r["date"] in ("1215-06-15",):
            print(r)


if __name__ == "__main__":
    main()
