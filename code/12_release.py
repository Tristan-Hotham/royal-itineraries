"""Step 12. Blog post (release/blog/post.html from blog_template.html), blog and Zenodo meta files,
and the Zenodo folder (paper, key CSVs, results.json and a code-and-data zip).
Image placeholders {{IMG|file|alt|caption}} are left for the uploader.
Run: python3 12_release.py
"""
import importlib.util, json, os, re, shutil, zipfile

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
spec = importlib.util.spec_from_file_location("b", os.path.join(HERE, "08_build_site.py")); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
R = b.R; SLUG = "royal-itineraries"; DOI = "10.5281/zenodo.23729639"; PDF = "Hotham_Royal_Itineraries.pdf"
t = open(os.path.join(HERE, "blog_template.html")).read()
t = re.sub(r"\{\{(?!IMG\|)([^{}]+?)\}\}", b.sub, t)
open(os.path.join(ROOT, "release", "blog", "post.html"), "w").write(t)
for m in re.findall(r"\{\{IMG\|([^|]+)\|", t):
    assert os.path.exists(os.path.join(ROOT, "release", "blog", m)), m
M = R["monarchs"]; H = R["headline"]
meta = dict(
    title="Governing on the move: where England's kings slept",
    slug=SLUG,
    excerpt=(f"Medieval government travelled with the king. I mapped King John and Edward I night by night from old printed itineraries: John moved on "
             f"{M['John']['moved_share'] * 100:.0f}% of the days we can follow him, Edward on {M['Edward I']['moved_share'] * 100:.0f}%, "
             f"and Edward spent {H['edward_westminster_nights']:,} nights at Westminster."),
    seo_description=f"Where England's kings slept: King John and Edward I mapped night by night, with Henry II and Elizabeth I's progresses.",
    tags=["medieval", "King John", "Edward I", "Elizabeth I", "royal progresses", "itinerant kingship", "maps", "data"],
    header_alt=(f"Title card reading 'Governing on the move' on a vellum background, beside a map of England, Wales and western France covered in blue dots "
                f"for King John's nights and gold dots for Edward I's. Text: King John moved on {M['John']['moved_share'] * 100:.0f}% of the days we can follow him; "
                f"Edward I on {M['Edward I']['moved_share'] * 100:.0f}%, and spent {H['edward_westminster_nights']:,} nights at Westminster."))
assert len(meta["seo_description"]) < 160, len(meta["seo_description"])
json.dump(meta, open(os.path.join(ROOT, "release", "blog", "meta.json"), "w"), indent=2, ensure_ascii=False)

pt = open(os.path.join(ROOT, "release", "paper", PDF.replace(".pdf", ".tex"))).read()
ab = pt.split("\\begin{center}\\textbf{Abstract}\\end{center}")[1].split("\\textbf{Keywords:}")[0].strip()
ab = ab.replace("\\%", "%").replace("\\textit{", "").replace("}", "")
Z = os.path.join(ROOT, "release", "zenodo"); os.makedirs(Z, exist_ok=True)
zmeta = dict(
    title="Governing on the Move: Where England's Kings Slept. Itineraries of Henry II, John, Edward I and Elizabeth I as Data",
    description_html=(f"<p>{ab}</p><p>Itineraries parsed from the public-domain books of T. D. Hardy (1835), R. W. Eyton (1878), H. Gough (1900) and J. Nichols (1823), "
                      "via Internet Archive OCR. Places from OS Open Names (OGL v3), GeoNames (CC BY 4.0) and Wikidata (CC0); royal forest list from Wikipedia (CC BY-SA 4.0).</p>"
                      f"<p>Interactive version: https://tristan-hotham.github.io/{SLUG}/. Data and code: https://github.com/Tristan-Hotham/{SLUG}. Blog post: to follow.</p>"),
    keywords=["itinerant kingship", "royal itineraries", "King John", "Edward I", "Henry II", "Elizabeth I", "royal progresses", "Westminster", "historical GIS", "OCR"],
    licence="cc-by-sa-4.0",
    related=[
        dict(identifier=f"https://github.com/Tristan-Hotham/{SLUG}", relation="issupplementedby", resource_type="software"),
        dict(identifier=f"https://tristan-hotham.github.io/{SLUG}/", relation="issupplementedby", resource_type="other"),
        dict(identifier="https://archive.org/details/descriptionofpat00hard", relation="isderivedfrom", resource_type="other"),
        dict(identifier="https://archive.org/details/courthouseholdit00eyto", relation="isderivedfrom", resource_type="other"),
        dict(identifier="https://archive.org/details/itineraryofkinge01gouguoft", relation="isderivedfrom", resource_type="other"),
        dict(identifier="https://archive.org/details/itineraryofkinge02gouguoft", relation="isderivedfrom", resource_type="other"),
        dict(identifier="https://archive.org/details/progressespublic01nich", relation="isderivedfrom", resource_type="other"),
        dict(identifier="https://www.ordnancesurvey.co.uk/products/os-open-names", relation="isderivedfrom", resource_type="dataset"),
        dict(identifier="https://www.geonames.org", relation="isderivedfrom", resource_type="dataset"),
        dict(identifier="https://www.wikidata.org", relation="isderivedfrom", resource_type="dataset"),
        dict(identifier="https://en.wikipedia.org/wiki/Royal_forest", relation="isderivedfrom", resource_type="other"),
    ])
json.dump(zmeta, open(os.path.join(Z, "meta.json"), "w"), indent=2, ensure_ascii=False)
shutil.copy(os.path.join(ROOT, "release", PDF), Z)
for f in ["stays.csv", "nights.csv", "places.csv", "years.csv", "royal_forests.csv", "checks.csv", "results.json"]:
    shutil.copy(os.path.join(ROOT, "data", f), Z)
with zipfile.ZipFile(os.path.join(Z, f"{SLUG}_code_and_data.zip"), "w", zipfile.ZIP_DEFLATED) as zf:
    for sub in ("code", "data"):
        for f in sorted(os.listdir(os.path.join(ROOT, sub))):
            p = os.path.join(ROOT, sub, f)
            if os.path.isfile(p) and not f.endswith(".pyc"): zf.write(p, f"{SLUG}/{sub}/{f}")
    for f in ("README.md", "LICENSE"): zf.write(os.path.join(ROOT, f), f"{SLUG}/{f}")
words = len(re.sub(r"<[^>]+>", " ", re.sub(r"\{\{IMG\|.*?\}\}", "", t, flags=re.S)).split())
print("release files written; post words:", words)
