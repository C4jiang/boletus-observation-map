# Porcini in Finland

A static, interactive map of high-precision *Boletus edulis* observations in Finland, aggregated to 10 km ETRS-TM35FIN national-grid cells.

## Active dataset rule

The active Laji.fi export is filtered to records meeting all of the following criteria:

- `Scientific name = Boletus edulis`
- observation year is 2009 or later
- location accuracy is 50 m or better
- WGS84 and ETRS-TM35FIN coordinates are present

The public export contains 970 observations in 413 occupied 10 km cells. It publishes the observation fields needed for spatial and temporal analysis but excludes observer names and locality text.

## Rebuild the data

The supplied Laji.fi source TSV is not committed to the public repository. With it available at the local Hermes document-cache path, rebuild the exports with:

```bash
.venv/bin/python extract_laji_observations.py
```

The script uses `pyproj` to construct grid geometry from `EPSG:3067` to WGS84 for browser display. The site is static and can be previewed locally with:

```bash
python3 -m http.server 4173
```

Then open `http://127.0.0.1:4173`.

## Interpretation

This map shows reported observations. It does not establish biological absence, mushroom abundance, or food safety.
