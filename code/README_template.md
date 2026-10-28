# Governing on the move: where England's kings slept

Medieval English government travelled with the king. This study turns four public-domain printed itineraries into day-by-day data and maps: King John (1199 to 1216, from T. D. Hardy 1835), Edward I (1272 to 1307, from Henry Gough 1900), a sample of dated stays of Henry II (1154 to 1189, from R. W. Eyton 1878) and the 1561 progress of Elizabeth I with the stops of her other progresses (from John Nichols 1823).

**Interactive version:** https://tristan-hotham.github.io/royal-itineraries/

This repository holds the interactive page, derived data and the analysis code for the data study *Governing on the move: where England's kings slept* by Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349). Paper and archived release: https://doi.org/10.5281/zenodo.23729639

## Headline results

- I can place King John on {{coverage.John.days_with_point|int}} of the {{coverage.John.reign_days|int}} days of his reign ({{coverage.John.share_days_with_point|pct0}}) and Edward I on {{coverage.Edward I.days_with_point|int}} of {{coverage.Edward I.reign_days|int}} ({{coverage.Edward I.share_days_with_point|pct0}}). {{coverage.John.share_point|pct0}} of John's index entries and {{coverage.Edward I.share_point|pct0}} of Edward's daily entries were matched to a point; {{checks_passed|int}} of {{checks_n|int}} fixed points (Runnymede on 15 June 1215, Newark in October 1216, Rhuddlan 1277, Conwy 1283, Berwick 1296, Ghent 1297, Caerlaverock 1300, Edward I's last days near Burgh by Sands) are recovered.
- John slept in {{monarchs.John.distinct_night_places|int}} places and Edward I in {{monarchs.Edward I.distinct_night_places|int}}. John's court moved on {{monarchs.John.moved_share|pct0}} of consecutive recorded days (median move {{monarchs.John.km_per_moving_day_median|km0}} km), Edward's on {{monarchs.Edward I.moved_share|pct0}} (median {{monarchs.Edward I.km_per_moving_day_median|km0}} km). In a typical well-recorded year John covered {{monarchs.John.km_per_year_median|int}} km in straight lines, Edward {{monarchs.Edward I.km_per_year_median|int}} km.
- Edward I spent {{headline.edward_westminster_nights|int}} nights at Westminster ({{headline.edward_westminster_share|pct0}} of placed nights), John {{headline.john_westminster_nights|int}}. Within 5 km of Westminster: {{monarchs.John.london_share|pct0}} of John's nights, {{monarchs.Edward I.london_share|pct0}} of Edward's.
- {{john.continent_1199_1203|pct0}} of John's recorded days to December 1203 were on the continent, {{john.continent_1204_1216|pct0}} afterwards. Henry II's sample of {{coverage.Henry II.days_with_entry|int}} dated stays is {{headline.henry_france_share|pct0}} in France; {{headline.henry_christmas_france|int}} of his {{headline.henry_christmas_n|int}} Christmas courts in Eyton were held there.
- Edward I's nights follow his wars: {{edward.wales_1282_1283|pct0}} in Wales in 1282 to 1283, {{edward.france_1286_1289|pct0}} in France in 1286 to 1289, {{edward.lowc_1297_1298|pct0}} in Flanders in 1297 to 1298, {{edward.scotland_1303_1304|pct0}} in Scotland in 1303 to 1304; {{edward.lanercost_nights|int}} nights at Lanercost Priory in 1306 to 1307.
- {{monarchs.John.forest_share|pct0}} of John's nights in England and {{monarchs.Edward I.forest_share|pct0}} of Edward's were within 10 km of a royal forest point (crude; {{forests.located|int}} of {{forests.listed|int}} forests placed).
- Elizabeth I's 1561 progress: {{elizabeth.days_1561|int}} days, {{elizabeth.places_1561|int}} places, {{elizabeth.km_1561|int}} km in straight lines.

## Files

- `index.html`: the interactive page (animated map with play button and speed, charts, tables).
- `header.png`: social card.
- `data/stays.csv`: one row per monarch, date and place as parsed: the place as printed, the editor's county or province, the modern place, latitude and longitude, country, how it was placed (`manual`, `gazetteer`, `close spelling`, `itinerary context`, `region`, `unidentified`, `unplaced`), the gazetteer entry used, the quality of the record and a `flag` for entries left out of the analysis (`isolated`, `same-day conflict`). Dates are Old Style (Julian), as printed.
- `data/nights.csv`: one row per monarch and day: the night place (last place on the day's route).
- `data/places.csv`: nights and entries per place and monarch, with coordinates and source.
- `data/years.csv`: per monarch and year: placed nights, straight-line km, distinct places, nights by country, near Westminster and near a royal forest.
- `data/royal_forests.csv`: royal forests listed in Wikipedia's "Royal forest" article, with the point used and how it was found.
- `data/checks.csv`: the fixed-point checks.
- `data/raw_john.csv`, `data/raw_edward.csv`, `data/raw_henry.csv`, `data/raw_henry_christmas.csv`, `data/raw_elizabeth.csv`, `data/edward_index.csv`: the parser outputs before placing.
- `data/page_data.json`, `data/results.json`: page data and every number quoted on the page, in the paper, the blog post and the collage.
- `code/`: Python scripts, run in order: `01_parse_john.py`, `02_parse_edward.py`, `03_parse_henry.py`, `04_parse_elizabeth.py`, `05_geocode.py` (with `manual_places.csv`), `06_analysis.py`, `07_basemap.py`, `08_build_site.py`, `09_header.py`, `10_figures.py`, `11_paper.py`, `12_release.py`.
- `release/`: paper PDF and LaTeX source, blog post and figures, Zenodo files. `reddit/`: collage and post text.

## Method in brief

**John.** Hardy's day-by-day table is printed in two columns that the OCR interleaves, so I parsed his index instead: {{parse.john.index_entries|int}} place entries with county or province, calendar year, regnal year, month and days. Where the OCR separated a long entry's year labels from its month lines, months were reassigned to years by a dynamic programme that keeps years in printed order and months rising within a year, and prefers assignments whose dates imply the regnal years printed beside them (regnal years from Ascension Day). {{parse.john.valid|int}} place-days on {{parse.john.distinct_days|int}} days; for {{parse.john.assigned_year|int}} the year was reassigned.

**Edward I.** Gough's index of places ({{parse.edward.index_entries|int}} names with county and months) is the vocabulary. The daily pages were walked month by month, each day line recognised by its expected number and weekday (Julian calendar), re-synchronised on each page's running head ({{parse.edward.day_lines_found|int}} of {{parse.edward.days_in_span|int}} day lines found). A fragment of a day's text is a place only if it matches (difflib ratio 0.78 or more) a place the index lists for that month, or very closely (0.90) any indexed place; {{parse.edward.supplementary_names|int}} frequent names lost from the OCR of the index were added when they exactly match an OS or GeoNames place.

**Henry II.** Eyton is a dated narrative. A stay is kept when a dated paragraph says the King is, keeps court, lands or stays at a place in Eyton's index of places, when a royal charter is dated there, or when Eyton's margin repeats the place: {{parse.henry_rows|int}} statements, {{parse.henry_uncertain|int}} flagged uncertain. This is a sample, not an itinerary.

**Elizabeth I.** Nichols prints the Latin household account of the 1561 progress, which I parsed day by day; the stops of other progresses were transcribed from Nichols's preface (year only). The Internet Archive scan labelled vol. 3 is Nichols's *Progresses of King James I* and was not used.

**Places.** Manual identifications for the commonest and hardest names (`code/manual_places.csv`, each pointing to a named gazetteer entry), then OS Open Names, Wikidata residences and GeoNames towns. Namesakes are separated by the county the editor prints (historic county centroids from OS Open Names), or by the itinerary itself (nearest to the places within three days). A namesake outside the printed county is rejected unless it is the only town of that name.

**Analysis.** Night place: the last place on the day's route (greedy from the previous night). Entries more than 120 km from every other entry within three days, or more than 150 km from another place on the same day and further from the surrounding route, are flagged and left out ({{headline.john_flagged|int}} for John, {{headline.edward_flagged|int}} for Edward). Distances are straight lines between records no more than seven days apart, leaving out legs faster than 100 km a day.

**Caveats.** Most days have no record. OCR and parsing errors remain; {{plausibility.John.share_over_100km|pct1}} of John's and {{plausibility.Edward I.share_over_100km|pct1}} of Edward's consecutive-day moves exceed 100 km. Some small French and Irish places are not in the gazetteers used and are unplaced; a few are approximate (Freemantle placed at Kingsclere, the New Temple at the centre of London). Royal forests are points, not areas.

## How to rerun

Python 3 with numpy, scipy, shapely and matplotlib (Playwright for the header, xelatex for the paper). From `code/`, run the scripts in order. Inputs are read one folder up and are not included: `_data12/itineraries_ocr.json.gz` and `itineraries_ocr2.json.gz` (Internet Archive OCR full texts), `_data12/wd_osm_bundle12.json.gz` (Wikidata), `_data12/wikipedia_batch12*.json.gz` (Wikipedia), `osnames_gb.tsv` (OS Open Names), `_data3/ne/geojson/ne_10m_land.geojson` (Natural Earth), and `work/geonames_cities.json` made from github.com/lutangar/cities.json (GeoNames).

## Sources and licence

- T. D. Hardy (1835) *A Description of the Patent Rolls in the Tower of London; to which is added an Itinerary of King John*. https://archive.org/details/descriptionofpat00hard (public domain).
- R. W. Eyton (1878) *Court, Household, and Itinerary of King Henry II*. https://archive.org/details/courthouseholdit00eyto (public domain).
- H. Gough (1900) *Itinerary of King Edward the First throughout his Reign, A.D. 1272 to 1307*, 2 vols. https://archive.org/details/itineraryofkinge01gouguoft and https://archive.org/details/itineraryofkinge02gouguoft (public domain).
- J. Nichols (1823) *The Progresses and Public Processions of Queen Elizabeth*, vols 1 and 2. https://archive.org/details/progressespublic01nich and https://archive.org/details/progressespublic02nich (public domain).
- OS Open Names, Ordnance Survey, Open Government Licence v3.0. Contains OS data © Crown copyright and database right 2026.
- GeoNames (https://www.geonames.org), via https://github.com/lutangar/cities.json, CC BY 4.0.
- Wikidata, CC0.
- Wikipedia articles (CC BY-SA 4.0): Royal forest (list of forests), Itinerant court, Curia regis, Wardrobe (government), Great Seal of the Realm, Purveyance, Exchequer, Court of Common Pleas (England), Woodstock Palace, Clarendon Palace, Tudor Royal Progresses, John, King of England, Edward I and Henry II of England (event dates for the checks and context).
- Natural Earth (public domain). Base map tiles on the page: Esri. Map library: Leaflet.

The derived data and the page text are released under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/), because they include material derived from Wikipedia; please credit OS, GeoNames and the itinerary editors as above. Code is MIT (see `LICENSE`).

Companion studies: [Market towns that failed](https://tristan-hotham.github.io/medieval-markets/) and [Is Domesday destiny?](https://tristan-hotham.github.io/domesday-destiny/).

## Citation

Hotham, T. (2026) *Governing on the move: where England's kings slept. Itineraries of Henry II, John, Edward I and Elizabeth I as data*. Zenodo. https://doi.org/10.5281/zenodo.23729639

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
