"""Holt die NOTAMs der Flughäfen aus notam-airports.txt über die öffentliche
FAA-NOTAM-Suche (Fallback: FAA DINS) und schreibt sie als notam.json."""
import html, json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
URL = "https://notams.aim.faa.gov/notamSearch/search"
BROWSER = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
UA = {"User-Agent": BROWSER, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Accept": "application/json, text/javascript, */*; q=0.01",
      "Origin": "https://notams.aim.faa.gov", "Referer": "https://notams.aim.faa.gov/notamSearch/nsapp.html", "X-Requested-With": "XMLHttpRequest"}
DINS = "https://www.notams.faa.gov/dinsQueryWeb/queryRetrievalMapAction.do?reportType=Raw&actionType=notamRetrievalByICAOs&submit=View+NOTAMs&retrieveLocId="

airports = []
with open("notam-airports.txt", encoding="utf-8") as f:
    for line in f:
        airports += [w for w in line.split("#")[0].split() if len(w) == 4]
airports = list(dict.fromkeys(airports))


def search(codes, offset):
    body = urllib.parse.urlencode({"searchType": 0, "designatorsForLocation": ",".join(codes), "offset": offset, "notamsOnly": "false", "radius": 10}).encode()
    with urllib.request.urlopen(urllib.request.Request(URL, data=body, headers=UA), timeout=60) as r:
        return json.loads(r.read())


def dins(codes):
    req = urllib.request.Request(DINS + "+".join(codes), headers={"User-Agent": BROWSER})
    with urllib.request.urlopen(req, timeout=60) as r:
        page = r.read().decode("utf-8", "replace")
    out = []
    for block in re.findall(r"<PRE>(.*?)</PRE>", page, re.S | re.I):
        msg = html.unescape(re.sub(r"<[^>]+>", "", block)).strip()
        m = re.search(r"A\)\s*([A-Z]{4})", msg)
        if m and m.group(1) in codes:
            out.append((m.group(1), msg))
    return out


notams, failed = {}, []
source = "notamSearch"
try:
    search(airports[:1], 0)
except Exception as e:
    print("notamSearch nicht erreichbar:", e, "-> FAA DINS")
    source = "dins"

if source == "dins":
    for i in range(0, len(airports), 10):
        batch = airports[i:i + 10]
        try:
            for loc, msg in dins(batch):
                nid = msg.split()[0]
                notams.setdefault(loc, []).append({"id": nid, "msg": msg})
        except Exception as e:
            failed += batch
            print("Fehler bei", batch, e)
        time.sleep(1)
    if notams:
        k = next(iter(notams)); print("Beispiel:", notams[k][0]["msg"][:600])

for i in range(0, len(airports) if source == "notamSearch" else 0, 5):
    batch = airports[i:i + 5]
    offset, total = 0, None
    try:
        while total is None or offset < total:
            res = search(batch, offset)
            items = res.get("notamList") or []
            if total is None:
                total = res.get("totalNotamCount", len(items))
                if i == 0 and items:
                    print("Beispiel:", json.dumps(items[0], ensure_ascii=False)[:1500])
            for n in items:
                loc = n.get("facilityDesignator") or n.get("icaoId") or ""
                msg = n.get("icaoMessage") or n.get("traditionalMessage") or ""
                if loc not in batch or not msg.strip():
                    continue
                notams.setdefault(loc, []).append({"id": n.get("notamNumber", ""), "msg": msg.strip(), "start": n.get("startDate", ""), "end": n.get("endDate", ""), "issued": n.get("issueDate", "")})
            if not items:
                break
            offset += len(items)
            time.sleep(0.4)
    except Exception as e:  # einzelne Fehler sollen den Rest nicht verhindern
        failed += batch
        print("Fehler bei", batch, e)
    time.sleep(0.4)

os.makedirs(OUT, exist_ok=True)
doc = {"source": source, "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "airports": airports, "failed": failed, "notams": notams}
with open(os.path.join(OUT, "notam.json"), "w", encoding="utf-8") as f:
    json.dump(doc, f, separators=(",", ":"), ensure_ascii=False)
print(f"{sum(len(v) for v in notams.values())} NOTAMs für {len(notams)} von {len(airports)} Flughäfen, Fehler: {len(failed)}")
if not notams:
    sys.exit("Keine NOTAMs erhalten")
