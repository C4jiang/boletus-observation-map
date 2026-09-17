# Porcini in Finland

A static, interactive map of high-precision *Boletus edulis* occurrence observations.

## Dataset rule

The extraction retains records that meet all of the following criteria:

- `taxonKey = MCH9`
- `scientificName = Boletus edulis Bull.`
- observation year is 2009 or later
- `coordinateUncertaintyInMeters <= 1000`

The generated CSV and GeoJSON contain 554 observations: 526 in Finland, 25 in Estonia, 2 in Denmark, and 1 in Norway.

## Rebuild the data

The source dataset is deliberately not copied into this repository. Place the original file at its Homebase inbox path, then run:

```bash
python3 extract_observations.py
```

The site is static and can be previewed locally with:

```bash
python3 -m http.server 4173
```

Then open `http://127.0.0.1:4173`.

## Interpretation

This map shows reported observations. It does not establish biological absence, mushroom abundance, or food safety.
