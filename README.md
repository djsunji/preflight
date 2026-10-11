# Preflight Wx

Wetter-Check für die Flugvorbereitung auf Embraer E1/E2: Departure, Destination und Alternate als ICAO-Code eingeben (z. B. LSZH). Die Seite lädt live METAR, TAF und Pistenrichtungen von aviationweather.gov, aktualisiert alle 5 Minuten und prüft sie gegen die Planungskriterien aus OM-A 8.1 und die Windlimiten aus OM-B 1.3.4.

Geprüft werden Take-off Minima (8.1.3.3), Take-off Alternate (8.1.5.3.2), Planungsminima Destination (8.1.5.3.4) und Alternate (8.1.5.3.5) im Fenster ETA ±1 h, Mean Wind, Crosswind und Tailwind (8.1.6.2) sowie Gewitter/CB als Hinweis. Flugzeugtyp, Pistenzustand, ETD, Flugzeit und Anflugminima lassen sich unter „Optionen“ einstellen.

Die ganze Seite ist `index.html`. NOTAMs holt `.github/workflows/notam.yml` alle 30 Minuten für die Flughäfen in `notam-airports.txt` (Branch `notam`); weitere Flughäfen einfach dort eintragen. Weil aviationweather.gov keinen direkten Abruf aus dem Browser erlaubt, holt die GitHub Action `.github/workflows/wx.yml` alle 5 Minuten alle METAR/TAF ab (`tools/build_wx.py`) und legt sie als `wx.json` auf den Branch `data`. Veröffentlicht wird sie mit GitHub Pages (Settings → Pages → Branch `main`, Ordner `/ (root)`).

Hilfsmittel, ersetzt weder OFP, NOTAM noch Handbuch.
