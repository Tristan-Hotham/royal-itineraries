"""Step 7. A small land outline for the static maps: Natural Earth 1:10m land (public domain), the polygons
that touch Britain, Ireland, France and the Low Countries, simplified to about 1 km.
Input: ../../_data3/ne/geojson/ne_10m_land.geojson (read in place). Output: ../work/land.json
Run: python3 07_basemap.py
"""
import json, os
from shapely.geometry import shape, box, mapping

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
G = json.load(open(os.path.join(ROOT, "..", "_data3", "ne", "geojson", "ne_10m_land.geojson")))
B = box(-11.5, 41.5, 10.5, 61.5)
out = []
for f in G["features"]:
    g = shape(f["geometry"])
    if not g.intersects(B): continue
    g = g.intersection(B).simplify(0.01, preserve_topology=True)
    if g.is_empty: continue
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    for p in polys:
        if p.geom_type == "Polygon" and p.area > 0.002:
            out.append([[round(x, 3), round(y, 3)] for x, y in p.exterior.coords])
json.dump(out, open(os.path.join(ROOT, "work", "land.json"), "w"), separators=(",", ":"))
print(len(out), "rings", os.path.getsize(os.path.join(ROOT, "work", "land.json")) // 1024, "KB")
