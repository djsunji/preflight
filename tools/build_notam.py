"""Holt die NOTAMs der Flughäfen aus notam-airports.txt über die öffentliche
FAA-NOTAM-Suche und schreibt sie als notam.json."""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
URL = "https://notams.aim.faa.gov/notamSearch/search"
UA = {"User-Agent": "preflight-wx (github.com/djsunji/preflight)", "Content-Type": "application/x-www-form-urlencoded"}

airports = []
with open("notam-airports.txt", encoding="utf-8") as f:
    for line in f:
        airports += [w for w in line.split("#")[0].split() if len(w) == 4]
airports = list(dict.fromkeys(airports))


def search(codes, offset):
    body = urllib.parse.urlencode({"searchType": 0, "designatorsForLocation": ",".join(codes), "offset": offset, "notamsOnly": "false", "radius": 10}).encode()
    with urllib.request.urlopen(urllib.request.Request(URL, data=body, headers=UA), timeout=60) as r:
        return json.loads(r.read())


notams, failed = {}, []
for i in range(0, len(airports), 5):
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
doc = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "airports": airports, "failed": failed, "notams": notams}
with open(os.path.join(OUT, "notam.json"), "w", encoding="utf-8") as f:
    json.dump(doc, f, separators=(",", ":"), ensure_ascii=False)
print(f"{sum(len(v) for v in notams.values())} NOTAMs für {len(notams)} von {len(airports)} Flughäfen, Fehler: {len(failed)}")
if not notams:
    sys.exit("Keine NOTAMs erhalten")
