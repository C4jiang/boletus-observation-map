#!/usr/bin/env python3
"""Build a reproducible Boletus edulis versus agaricoid-fungi TSV dataset."""

import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

SOURCE = Path(__file__).parent.parent / "data" / "occurrences.tsv"
OUTPUT = Path(__file__).parent.parent / "data" / "boletus_edulis_vs_other_agaricoid_balanced.tsv"
TARGET_SPECIES = "Boletus edulis"
RANDOM_SEED = 20260918

csv.field_size_limit(sys.maxsize)


def is_other_agaricoid(row):
    return (
        row["scientificName"] != TARGET_SPECIES
        and row["taxonRank"] == "species"
        and "Agaricoid fungi" in row["informalTaxonGroup"]
    )


def main():
    with SOURCE.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        next(reader)
        next(reader)
        headers = list(reader.fieldnames or [])
        targets = [row for row in reader if row["scientificName"] == TARGET_SPECIES]

    with SOURCE.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        next(reader)
        next(reader)
        provinces = sorted(
            {
                row["biogeographicalProvince"]
                for row in reader
                if is_other_agaricoid(row)
                and row["biogeographicalProvince"]
                and "," not in row["biogeographicalProvince"]
            }
        )

    base, remainder = divmod(len(targets), len(provinces))
    quotas = {province: base + (index < remainder) for index, province in enumerate(provinces)}
    sampled = defaultdict(list)
    seen = Counter()
    randomizer = random.Random(RANDOM_SEED)

    with SOURCE.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        next(reader)
        next(reader)
        for row in reader:
            province = row["biogeographicalProvince"]
            if not is_other_agaricoid(row) or province not in quotas:
                continue
            seen[province] += 1
            if len(sampled[province]) < quotas[province]:
                sampled[province].append(row)
            else:
                replacement = randomizer.randrange(seen[province])
                if replacement < quotas[province]:
                    sampled[province][replacement] = row

    unavailable = {province: quotas[province] - len(sampled[province]) for province in provinces if len(sampled[province]) != quotas[province]}
    if unavailable:
        raise ValueError(f"Not enough candidate observations in: {unavailable}")

    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=headers + ["sample_group"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in targets:
            writer.writerow(row | {"sample_group": "boletus_edulis"})
        for province in provinces:
            for row in sampled[province]:
                writer.writerow(row | {"sample_group": "other_agaricoid"})

    print(f"Wrote {OUTPUT}")
    print(f"Boletus edulis: {len(targets)}")
    print(f"Other agaricoid: {sum(map(len, sampled.values()))}")
    print(f"Regions: {len(provinces)}; per-region quota: {base} or {base + 1}")


if __name__ == "__main__":
    main()
