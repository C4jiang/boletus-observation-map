from collections import Counter

import pytest

from scripts.build_balanced_boletus_dataset import (
    sample_candidates_by_spatial_block,
    spatial_block_key,
)


def test_spatial_block_key_uses_two_dimensional_tm35fin_cells():
    assert spatial_block_key(524_999.9, 6_749_999.9, block_size_m=25_000) == (20, 269)
    assert spatial_block_key(525_000.0, 6_750_000.0, block_size_m=25_000) == (21, 270)


def test_sampling_matches_target_count_within_each_spatial_block():
    targets = [
        {"id": "target-a", "block": (1, 1)},
        {"id": "target-b", "block": (1, 1)},
        {"id": "target-c", "block": (2, 1)},
    ]
    candidates = [
        {"id": "a-1", "block": (1, 1)},
        {"id": "a-2", "block": (1, 1)},
        {"id": "a-3", "block": (1, 1)},
        {"id": "b-1", "block": (2, 1)},
        {"id": "b-2", "block": (2, 1)},
    ]

    sampled = sample_candidates_by_spatial_block(targets, candidates, seed=42)

    assert len(sampled) == len(targets)
    assert Counter(row["block"] for row in sampled) == Counter(row["block"] for row in targets)
    assert {row["id"] for row in sampled}.issubset({row["id"] for row in candidates})


def test_sampling_rejects_a_spatial_block_without_enough_candidates():
    targets = [{"id": "target", "block": (1, 1)}]
    candidates = []

    with pytest.raises(ValueError, match=r"\(1, 1\)"):
        sample_candidates_by_spatial_block(targets, candidates, seed=42)
