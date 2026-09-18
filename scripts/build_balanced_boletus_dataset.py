#!/usr/bin/env python3
"""Build a spatially balanced Boletus edulis versus agaricoid-fungi TSV dataset."""

import csv
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Transformer

SOURCE = Path(__file__).parent.parent / "data" / "occurrences.tsv"
OUTPUT = Path(__file__).parent.parent / "data" / "boletus_edulis_vs_other_agaricoid_balanced.tsv"
TARGET_SPECIES = "Boletus edulis"
RANDOM_SEED = 20260918
BLOCK_SIZE_M = 25_000
TO_TM35FIN = Transformer.from_crs("EPSG:4326", "EPSG:3067", always_xy=True)

csv.field_size_limit(sys.maxsize)


def is_other_agaricoid(row):
    return (
        row["scientificName"] != TARGET_SPECIES
        and row["taxonRank"] == "species"
        and "Agaricoid fungi" in row["informalTaxonGroup"]
    )


def spatial_block_key(easting_m, northing_m, block_size_m=BLOCK_SIZE_M):
    """Return the two-dimensional EPSG:3067 block containing a coordinate."""
    if block_size_m <= 0:
        raise ValueError("block_size_m must be positive")
    return (math.floor(easting_m / block_size_m), math.floor(northing_m / block_size_m))


def spatial_block_for_row(row):
    """Transform a coordinate-bearing source row into an EPSG:3067 block key."""
    if not row["decimalLatitude"] or not row["decimalLongitude"]:
        raise ValueError(f"Missing coordinate for occurrence {row['occurrenceID']}")
    easting_m, northing_m = TO_TM35FIN.transform(float(row["decimalLongitude"]), float(row["decimalLatitude"]))
    return spatial_block_key(easting_m, northing_m)


def sample_candidates_by_spatial_block(targets, candidates, seed):
    """Reservoir-sample candidates to match the target count in every spatial block."""
    quotas = Counter(row["block"] for row in targets)
    sampled = defaultdict(list)
    seen = Counter()
    randomizer = random.Random(seed)

    for row in candidates:
        block = row["block"]
        quota = quotas.get(block)
        if quota is None:
            continue
        seen[block] += 1
        if len(sampled[block]) < quota:
            sampled[block].append(row)
        else:
            replacement = randomizer.randrange(seen[block])
            if replacement < quota:
                sampled[block][replacement] = row

    unavailable = {
        block: quotas[block] - len(sampled[block])
        for block in quotas
        if len(sampled[block]) != quotas[block]
    }
    if unavailable:
        raise ValueError(f"Not enough candidate observations in spatial blocks: {unavailable}")
    return [row for block in sorted(quotas) for row in sampled[block]]


def source_rows():
    with SOURCE.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        next(reader)
        next(reader)
        yield list(reader.fieldnames or [])
        yield from reader


def main():
    rows = source_rows()
    headers = next(rows)
    targets = []
    for row in rows:
        if row["scientificName"] == TARGET_SPECIES:
            targets.append(row | {"block": spatial_block_for_row(row)})

    def candidates():
        rows = source_rows()
        next(rows)
        for row in rows:
            if is_other_agaricoid(row) and row["decimalLatitude"] and row["decimalLongitude"]:
                yield row | {"block": spatial_block_for_row(row)}

    sampled = sample_candidates_by_spatial_block(targets, candidates(), seed=RANDOM_SEED)

    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=headers + ["sample_group"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in targets:
            writer.writerow({field: row[field] for field in headers} | {"sample_group": "boletus_edulis"})
        for row in sampled:
            writer.writerow({field: row[field] for field in headers} | {"sample_group": "other_agaricoid"})

    block_count = len({row["block"] for row in targets})
    print(f"Wrote {OUTPUT}")
    print(f"Boletus edulis: {len(targets)}")
    print(f"Other agaricoid: {len(sampled)}")
    print(f"Spatial blocks: {block_count}; block size: {BLOCK_SIZE_M / 1000:g} km")


if __name__ == "__main__":
    main()
