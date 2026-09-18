import numpy as np

from scripts.train_logistic_classifier import longitude_kfold_indices, stratified_kfold_indices, roc_auc_score


def test_stratified_kfold_keeps_both_classes_in_every_validation_fold():
    labels = np.array([0] * 10 + [1] * 10)

    folds = stratified_kfold_indices(labels, folds=5, seed=42)

    assert len(folds) == 5
    assert sorted(np.concatenate([validation for _, validation in folds]).tolist()) == list(range(20))
    for _, validation in folds:
        assert labels[validation].tolist().count(0) == 2
        assert labels[validation].tolist().count(1) == 2


def test_roc_auc_score_rewards_perfect_ranking():
    assert roc_auc_score(np.array([0, 0, 1, 1]), np.array([0.1, 0.2, 0.8, 0.9])) == 1.0


def test_longitude_kfold_uses_contiguous_near_equal_longitude_bands():
    longitudes = np.array([24.0, 20.0, 22.0, 21.0, 23.0, 25.0])

    folds = longitude_kfold_indices(longitudes, folds=3)

    assert [validation.tolist() for _, validation in folds] == [[1, 3], [2, 4], [0, 5]]
