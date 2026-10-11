"""Holt alle aktuellen METAR/TAF von aviationweather.gov und Pistenrichtungen
von OurAirports und schreibt sie als wx.json, die die Seite ohne CORS-Probleme laden kann."""
import csv, gzip, json, os, sys, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
CACHE = sys.argv[2] if len(sys.argv) > 2 else "cache"
UA = {"User-Agent": "preflight-wx (github.com/djsunji/preflight)"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
        data = r.read()
    try:
        return gzip.decompress(data)
    except OSError:
        return data


def awc(name):
    text = get(f"https://aviationweather.gov/data/cache/{name}.cache.csv.gz").decode("utf-8", "replace")
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("raw_text"))
    return list(csv.DictReader(lines[start:]))


def awc_xml(name, tag):
    root = ET.fromstring(get(f"https://aviationweather.gov/data/cache/{name}.cache.xml.gz"))
    return [{c.tag: (c.text or "") for c in el} for el in root.iter(tag)]


def latest(rows, timecol):
    out = {}
    for r in rows:
        st, t = r.get("station_id", ""), r.get(timecol, "")
        if len(st) == 4 and r.get("raw_text") and (st not in out or t > out[st][1]):
            out[st] = (r["raw_text"].strip(), t)
    return {k: v[0] for k, v in out.items()}


def cached(name, url):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, name)
    if not os.path.exists(p):
        with open(p, "wb") as f:
            f.write(get(url))
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


metar = latest(awc("metars"), "observation_time")
taf = latest(awc_xml("tafs", "TAF"), "issue_time")  # TAF gibt es nur als XML
wanted = set(metar) | set(taf)

base = "https://davidmegginson.github.io/ourairports-data/"
alias, name = {}, {}
for a in cached("airports.csv", base + "airports.csv"):
    icao = next((c for c in (a.get("icao_code"), a.get("gps_code"), a.get("ident")) if c in wanted), None)
    if icao:
        alias[a["ident"]] = icao
        name[icao] = a.get("name", "")

rwy = {}
for r in cached("runways.csv", base + "runways.csv"):
    icao = alias.get(r.get("airport_ident"))
    if not icao or r.get("closed") == "1" or not r.get("le_ident") or "H" in r["le_ident"]:
        continue
    try:
        hdg = round(float(r["le_heading_degT"]))
    except (KeyError, ValueError):
        hdg = None
    ident = r["le_ident"] + ("/" + r["he_ident"] if r.get("he_ident") else "")
    rwy.setdefault(icao, []).append({"id": ident, "alignment": hdg})

os.makedirs(OUT, exist_ok=True)
doc = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "metar": metar, "taf": taf, "name": name, "rwy": rwy}
with open(os.path.join(OUT, "wx.json"), "w", encoding="utf-8") as f:
    json.dump(doc, f, separators=(",", ":"), ensure_ascii=False)
print(f"{len(metar)} METAR, {len(taf)} TAF, {len(rwy)} Flughäfen mit Pisten")
if len(metar) < 1000 or len(taf) < 500:
    sys.exit("Zu wenige Meldungen, vermutlich ein Fehler bei aviationweather.gov")
