# Porcini in Finland

A static, interactive explorer for the complete user-provided Laji.fi Boletus export. The map aggregates coordinate-bearing records to 1 km ETRS-TM35FIN national-grid cells.

## Active dataset

The public export contains all 2,139 supplied records. It excludes observer names and locality text while retaining fields needed for filtering and spatial analysis:

- species and scientific name
- date and year
- coordinate accuracy
- WGS84 and ETRS-TM35FIN coordinates
- reliability, collection quality and record type
- source collection and 1 km grid identifier

2,138 records contain the coordinates needed for mapping. The map begins unfiltered and provides client-side filters for year range, maximum location accuracy, reliability and record type.

## Grid system

Each occupied map cell is a 1 km × 1 km square in ETRS-TM35FIN (`EPSG:3067`). The browser converts the generated polygon boundaries to WGS84 only for display in Leaflet; grid assignment itself is performed in the Finnish national coordinate system.

## Rebuild the data

The supplied Laji.fi source TSV is not committed to the public repository. With it available at the local Hermes document-cache path, rebuild the exports with:

```bash
.venv/bin/python extract_full_laji_observations.py
```

The script uses `pyproj` to construct grid geometry. Preview the static site locally with:

```bash
python3 -m http.server 4173
```

Then open `http://127.0.0.1:4173`.

## Comparative dataset

`scripts/build_balanced_boletus_dataset.py` produces a reproducible comparison dataset of *Boletus edulis* records versus sampled records of other agaricoid fungi. It is **not** an occurrence–absence dataset: an `other_agaricoid` row records another fungus, not a verified absence of *B. edulis*.

The script assigns records to 25 km × 25 km two-dimensional `EPSG:3067` (ETRS-TM35FIN) blocks. Within every block containing target observations, it uses a fixed-seed reservoir sample of other-agaricoid records to match that block's target-record count. This preserves the target's broad spatial distribution without treating biogeographical provinces as negative-sampling strata.

## Weather features

All 7-, 14-, and 30-day weather features use complete calendar days ending on the day **before** the observation date. For an observation on day `D`, the windows are `D−7…D−1`, `D−14…D−1`, and `D−30…D−1`; the observation day is excluded to avoid temporal leakage.

## Interpretation

This map shows reported observations. It does not establish biological absence, mushroom abundance or food safety.
