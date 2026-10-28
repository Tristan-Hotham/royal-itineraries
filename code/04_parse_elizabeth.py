"""Step 4. Elizabeth I: her progresses from John Nichols, The Progresses and Public Processions of
Queen Elizabeth (1823 edition, vols 1 and 2; the scan labelled vol 3 is in fact Nichols's Progresses of
King James I and is not used).

Two kinds of evidence, kept apart:
  1. Day by day, 10 July to the end of the account in 1561: the household account of the progress into
     Essex, Suffolk and Hertfordshire that Nichols prints in Latin ("Jovis, decimo die Julii, ibidem &
     Charterhowse"). Each day line gives the Latin day and month, and the place the household reached
     ("ibidem & X", or "ibidem" for the same place). Parsed automatically below.
  2. Year by year, 1559 to 1602: the places Nichols names in the year-by-year summary of the progresses
     in his preface (vol. 1, pp. xiii to xxi). I read the preface and transcribed each named stop with
     the words that name it (EVIDENCE below). These are visits within a summer, without day dates, and
     are used only for the progress maps and counts, never for nights or distances.
Input: ../../_data12/itineraries_ocr.json.gz (progressespublic01nich), public domain.
Output: ../data/raw_elizabeth.csv
Run: python3 04_parse_elizabeth.py
"""
import csv, gzip, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
T = json.load(gzip.open(os.path.join(ROOT, "..", "_data12", "itineraries_ocr.json.gz")))["items"]["progressespublic01nich"]["text"].split("\n")

UNITS = {"primo": 1, "secundo": 2, "tertio": 3, "quarto": 4, "quinto": 5, "sexto": 6, "septimo": 7, "octavo": 8, "nono": 9}
TENS = {"decimo": 10, "vicesimo": 20, "vicessimo": 20, "tricesimo": 30, "tricessimo": 30}
SPECIAL = {"undecimo": 11, "duodecimo": 12}
MONTHS = {"julii": 7, "augusti": 8, "septembris": 9}


def latin_day(words):
    w = [x.lower().strip(",.") for x in words]
    if w and w[0] in SPECIAL: return SPECIAL[w[0]]
    if w and w[0] in UNITS: return UNITS[w[0]]
    if w and w[0] in TENS:
        return TENS[w[0]] + (UNITS.get(w[1], 0) if len(w) > 1 else 0)
    return None


def parse_1561():
    st = next(i for i, l in enumerate(T) if "Progress  into  Essex,  Suffolk,  and  Hertfordshire,  in  1561" in l)
    rows = []; heading = None; last = None
    for l in T[st:st + 900]:
        s = re.sub(r"\s+", " ", l).strip()
        if not s: continue
        m = re.match(r"^(?:Die\s+)?(Lun\w*|Mart\w*|Mercur\w*|Jov\w*|Vener\w*|Sabb\w*|Domin\w*)\s*,\s*(.+?)\s+(?:die\s+)?(Julii|Augusti|Septembris)\s*,\s*ibidem(.*)$", s)
        if m:
            words = [x for x in m.group(2).split() if x.lower() != "die"]
            d = latin_day(words); mo = MONTHS[m.group(3).lower()]
            rest = re.split(r"dispens|\d{2,}|\s-\s|\s-$", m.group(4))[0]
            rest = re.sub(r"(?<=[a-z])\s?[0-9*]+\b|\s+l\b", "", rest)
            names = [x.strip(" ,.-") for x in re.split(r"\s*(?:&|\bet\b|\but\b)\s*", rest)]
            names = [x for x in names if re.match(r"^[A-Z][a-z]", x) and not x.lower().startswith(("ut supra", "ibidem"))]
            place = names[-1] if names else None
            place = place or last or heading
            if d:
                rows.append(dict(date=f"1561-{mo:02d}-{d:02d}", place=place, latin=s[:90]))
                last = place
            continue
        s = re.sub(r"(?<=[a-z])\s?[0-9*]+(?=\s|\.|$)", "", s)
        hm = re.match(r"^(?:Adhuc\s+)?([A-Z][A-Za-z]+(?:\s+(?:Hall|House|Park))?(?:\s*&\s*[A-Z][A-Za-z]+(?:\s+(?:Hall|House))?)?)\s*[0-9*]?\s*\.\s*$", s)
        if hm and len(s) < 45:
            heading = hm.group(1).split("&")[-1].strip()
        if s.startswith("The  Progress") and rows and len(rows) > 5: break
    return rows


# Places named for each year in Nichols's preface (vol. 1, pp. xiii to xxi), in the order named.
PREFACE = [
    (1559, ["Greenwich", "Dartford", "Cobham", "Eltham", "Nonsuch", "Hampton Court"], "In the Summer of 1559, she made an excursion from Greenwich to Dartford and Cobham; and afterwards to Eltham, Nonsuch, and Hampton Court."),
    (1564, ["Cambridge", "Stanton-All-Saints", "Hinchinbroke Priory"], "the next year those of the University of Cambridge; and, on her return, visited Bishop Cox at Stanton-All-Saints ... and Sir Henry Cromwell at Hinchinbroke Priory"),
    (1565, ["Coventry", "Kenilworth", "Stamford"], "She certainly was at Coventry, and at Kenilworth. She also passed through Stamford in her way to Lincolnshire."),
    (1566, ["Oxford", "Burghley"], "she visited Oxford, in compliment to the Earl of Leicester, then Chancellor of that University; and Burghley, the mansion of the great Cecil."),
    (1572, ["Kenilworth", "Warwick", "Charlecote", "Long Compton", "Weston", "Berkeley Castle", "Woodstock", "Reading", "Windsor", "Hampton Court"],
     "thence to Kenilworth, Warwick, Charlecot, Long Compton, Weston juxta Cheriton, Berkeley Castle, Woodstock, Reading, Windsor, and Hampton Court"),
    (1573, ["Croydon"], "She visited Archbishop Parker at Croydon"),
    (1574, ["Woodstock", "Sudeley Castle", "Berkeley Castle", "Bristol", "Longleat", "Heytesbury", "Wilton", "Salisbury"],
     "passing through Woodstock, visited old Lady Chandos at Sudeley Castle; and Lord Berkeley at Berkeley Castle; and was afterwards amused at Bristol ... was entertained at Longleat, Heytesbury, and Wilton; and visited the City of New Sarum."),
    (1575, ["Theobalds", "Grafton", "Kenilworth", "Lichfield", "Worcester"], "she passed from Theobalds, through Bedfordshire, to her Palace at Grafton in Northamptonshire, and thence to the Earl of Leicester's splendid Castle of Kenilworth ... There are accounts of her being at the two first of these places [Lichfield, Worcester]"),
    (1577, ["Gorhambury"], "Early in 1577, she spent three days at Sir Nicholas Bacon's at Gorhambury"),
    (1578, ["Audley End"], "received the compliments of the University of Cambridge in her way at Audley Inn"),
    (1582, ["Canterbury"], "In February 1581-2, she accompanied the Duke of Anjou ... to Canterbury on his departure."),
    (1588, ["Tilbury"], "Her reception by her Army at Tilbury, in 1588"),
    (1591, ["Cowdray", "Elvetham", "Titchfield", "Theobalds"], "particularly at Cowdray, Elvetham, and Tichfield ... the great Entertainments he gave her at Theobalds, when she conferred the honour of Knighthood on him in 1591"),
    (1592, ["Bisham", "Sudeley Castle", "Rycote", "Oxford"], "and the next year at Bisham, Sudeley, and Rycott ... In 1592, she paid a second Visit to Oxford"),
    (1600, ["Blackfriars", "Fulham"], "she honoured the nuptials of Lord Herbert with her presence in Black Friars ... In 1600 and 1601, she visited Bishop Bancroft at Fulham Palace"),
    (1602, ["Harefield"], "Sir Thomas Egerton ... both at his residence at Westminster, and his mansion at Harefield"),
]
COUNTY = {"Greenwich": "Kent", "Dartford": "Kent", "Cobham": "Kent", "Eltham": "Kent", "Nonsuch": "Surrey", "Hampton Court": "Middlesex",
          "Cambridge": "Cambridgeshire", "Stanton-All-Saints": "Cambridgeshire", "Hinchinbroke Priory": "Huntingdonshire", "Coventry": "Warwickshire",
          "Kenilworth": "Warwickshire", "Stamford": "Lincolnshire", "Oxford": "Oxfordshire", "Burghley": "Northamptonshire", "Warwick": "Warwickshire",
          "Charlecote": "Warwickshire", "Long Compton": "Warwickshire", "Weston": "Warwickshire", "Berkeley Castle": "Gloucestershire",
          "Woodstock": "Oxfordshire", "Reading": "Berkshire", "Windsor": "Berkshire", "Croydon": "Surrey", "Sudeley Castle": "Gloucestershire",
          "Bristol": "Gloucestershire", "Longleat": "Wiltshire", "Heytesbury": "Wiltshire", "Wilton": "Wiltshire", "Salisbury": "Wiltshire",
          "Theobalds": "Hertfordshire", "Grafton": "Northamptonshire", "Lichfield": "Staffordshire", "Worcester": "Worcestershire",
          "Gorhambury": "Hertfordshire", "Audley End": "Essex", "Canterbury": "Kent", "Tilbury": "Essex", "Cowdray": "Sussex", "Elvetham": "Hampshire",
          "Titchfield": "Hampshire", "Bisham": "Berkshire", "Rycote": "Oxfordshire", "Blackfriars": "Middlesex", "Fulham": "Middlesex", "Harefield": "Middlesex"}
C1561 = {"Charterhowse": "Middlesex", "Charterhouse": "Middlesex", "Stronde": "Middlesex", "Strond": "Middlesex", "Wansted": "Essex", "Havering": "Essex",
         "Haveringe": "Essex", "Purgo": "Essex", "Lowtenhall": "Essex", "Ingerstone": "Essex", "Hingerstone": "Essex", "Newhall": "Essex",
         "Felixhall": "Essex", "Colchester": "Essex", "Harwich": "Essex", "Ippeswiche": "Suffolk", "Ippeswich": "Suffolk", "Smalebridge": "Suffolk",
         "Hemingham": "Essex", "Gosfeld": "Essex"}


def main():
    rows = []
    d61 = parse_1561()
    for i, r in enumerate(d61):
        rows.append(dict(date=r["date"], order=0, place=r["place"], county=C1561.get(r["place"], "Essex"), quality="household account",
                         source="Nichols 1823, vol. 1, progress of 1561 (household account)", evidence=r["latin"]))
    for y, places, ev in PREFACE:
        for k, p in enumerate(places):
            rows.append(dict(date=f"{y}-07-01", order=k, place=p, county=COUNTY.get(p, ""), quality="preface summary (year only)",
                             source="Nichols 1823, vol. 1, preface", evidence=ev))
    with open(os.path.join(ROOT, "data", "raw_elizabeth.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
    print("1561 days", len(d61), d61[0]["date"], "to", d61[-1]["date"])
    print([(r["date"][5:], r["place"]) for r in d61])
    print("preface stops", sum(len(p) for _, p, _ in PREFACE), "years", len(PREFACE))


if __name__ == "__main__":
    main()
