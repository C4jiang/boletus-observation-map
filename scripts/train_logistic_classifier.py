#!/usr/bin/env python3
"""Train a reproducible 5-fold logistic baseline on weather features only."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT = DATA_DIR / "boletus_edulis_vs_other_agaricoid_weather.tsv"
RESULTS = DATA_DIR / "logistic_weather_cv_results.json"
PREDICTIONS = DATA_DIR / "logistic_weather_cv_predictions.tsv"
FEATURE_COLUMNS = [
    "temp_mean_7d",
    "temp_mean_14d",
    "temp_mean_30d",
    "temp_min_7d",
    "temp_max_7d",
    "rain_mean_7d",
    "rain_mean_14d",
    "rain_mean_30d",
    "rainy_days_14d",
    "day_of_year",
]
TARGET_COLUMN = "Has Boletus edulis"


def stratified_kfold_indices(labels: np.ndarray, folds: int, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """Return shuffled stratified train/validation index pairs."""
    if folds < 2:
        raise ValueError("folds must be at least 2")
    classes, counts = np.unique(labels, return_counts=True)
    if len(classes) != 2 or counts.min() < folds:
        raise ValueError("each binary class must contain at least one row per fold")
    randomizer = np.random.default_rng(seed)
    partitions = [[] for _ in range(folds)]
    for label in classes:
        indices = np.flatnonzero(labels == label)
        randomizer.shuffle(indices)
        for fold_index, chunk in enumerate(np.array_split(indices, folds)):
            partitions[fold_index].extend(chunk.tolist())
    all_indices = np.arange(len(labels))
    result = []
    for validation_list in partitions:
        validation = np.array(sorted(validation_list), dtype=int)
        training = np.setdiff1d(all_indices, validation, assume_unique=True)
        result.append((training, validation))
    return result


def longitude_kfold_indices(longitudes: np.ndarray, folds: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """Hold out contiguous, near-equal record-count longitude bands."""
    if folds < 2:
        raise ValueError("folds must be at least 2")
    if len(longitudes) < folds:
        raise ValueError("there must be at least one row per fold")
    ordered = np.argsort(np.asarray(longitudes, dtype=float), kind="mergesort")
    all_indices = np.arange(len(longitudes))
    return [
        (np.setdiff1d(all_indices, validation, assume_unique=True), validation)
        for validation in np.array_split(ordered, folds)
    ]


def sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -500, 500)))


def fit_logistic_regression(features: np.ndarray, labels: np.ndarray, l2: float = 0.1, learning_rate: float = 0.1, iterations: int = 3000) -> tuple[np.ndarray, float]:
    """Fit a binary logistic model with an unpenalized intercept."""
    weights = np.zeros(features.shape[1], dtype=float)
    intercept = 0.0
    for _ in range(iterations):
        probabilities = sigmoid(features @ weights + intercept)
        residual = probabilities - labels
        weights -= learning_rate * ((features.T @ residual) / len(labels) + l2 * weights / len(labels))
        intercept -= learning_rate * residual.mean()
    return weights, intercept


def roc_auc_score(labels: np.ndarray, probabilities: np.ndarray) -> float:
    """Compute ROC AUC from average ranks, including tied probabilities."""
    labels = np.asarray(labels, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    positive_count = int(labels.sum())
    negative_count = len(labels) - positive_count
    if not positive_count or not negative_count:
        raise ValueError("ROC AUC requires both classes")
    order = np.argsort(probabilities, kind="mergesort")
    sorted_probabilities = probabilities[order]
    ranks = np.empty(len(probabilities), dtype=float)
    start = 0
    while start < len(probabilities):
        end = start + 1
        while end < len(probabilities) and sorted_probabilities[end] == sorted_probabilities[start]:
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    return float((ranks[labels == 1].sum() - positive_count * (positive_count + 1) / 2) / (positive_count * negative_count))


def binary_metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, float | int]:
    predicted = probabilities >= 0.5
    true_positive = int(np.sum((predicted == 1) & (labels == 1)))
    true_negative = int(np.sum((predicted == 0) & (labels == 0)))
    false_positive = int(np.sum((predicted == 1) & (labels == 0)))
    false_negative = int(np.sum((predicted == 0) & (labels == 1)))
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    return {
        "accuracy": (true_positive + true_negative) / len(labels),
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "roc_auc": roc_auc_score(labels, probabilities),
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
    }


def load_dataset(path: Path) -> tuple[list[dict[str, str]], np.ndarray, np.ndarray]:
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source, delimiter="\t"))
    usable = [row for row in rows if all(row.get(column, "") != "" for column in FEATURE_COLUMNS) and row.get(TARGET_COLUMN, "") != ""]
    features = np.array([[float(row[column]) for column in FEATURE_COLUMNS] for row in usable], dtype=float)
    labels = np.array([int(row[TARGET_COLUMN]) for row in usable], dtype=int)
    return usable, features, labels


def run_cross_validation(rows: list[dict[str, str]], features: np.ndarray, labels: np.ndarray, folds: int, seed: int) -> tuple[dict, np.ndarray]:
    predictions = np.full(len(labels), np.nan)
    fold_results = []
    coefficient_rows = []
    longitudes = np.array([float(row["longitude_wgs84"]) for row in rows], dtype=float)
    for fold_number, (training, validation) in enumerate(longitude_kfold_indices(longitudes, folds), start=1):
        mean = features[training].mean(axis=0)
        scale = features[training].std(axis=0)
        scale[scale == 0] = 1.0
        weights, intercept = fit_logistic_regression((features[training] - mean) / scale, labels[training])
        probabilities = sigmoid(((features[validation] - mean) / scale) @ weights + intercept)
        predictions[validation] = probabilities
        fold_results.append(
            {
                "fold": fold_number,
                "validation_rows": int(len(validation)),
                "validation_longitude_min": float(longitudes[validation].min()),
                "validation_longitude_max": float(longitudes[validation].max()),
                "validation_positive_rows": int(labels[validation].sum()),
                "validation_negative_rows": int(len(validation) - labels[validation].sum()),
                **binary_metrics(labels[validation], probabilities),
            }
        )
        coefficient_rows.append(weights)
    overall = binary_metrics(labels, predictions)
    coefficient_mean = np.mean(coefficient_rows, axis=0)
    report = {
        "model": "L2-regularized logistic regression",
        "validation": {
            "scheme": "contiguous longitude-balanced k-fold",
            "folds": folds,
            "seed": None,
            "method": "sort records by longitude_wgs84, then split into near-equal contiguous bands",
        },
        "input": {"path": str(INPUT.relative_to(DATA_DIR.parent)), "rows": int(len(rows)), "positive_rows": int(labels.sum()), "negative_rows": int(len(labels) - labels.sum()), "features": FEATURE_COLUMNS},
        "overall": overall,
        "folds": fold_results,
        "mean_standardized_coefficients": {name: float(value) for name, value in zip(FEATURE_COLUMNS, coefficient_mean)},
    }
    return report, predictions


def write_predictions(rows: list[dict[str, str]], predictions: np.ndarray) -> None:
    columns = ["sample_group", "scientific_name", "event_year", "day_of_year", TARGET_COLUMN, "predicted_probability"]
    with PREDICTIONS.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row, probability in zip(rows, predictions):
            writer.writerow({column: row[column] for column in columns[:-1]} | {"predicted_probability": f"{probability:.8f}"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260918)
    arguments = parser.parse_args()
    rows, features, labels = load_dataset(INPUT)
    report, predictions = run_cross_validation(rows, features, labels, arguments.folds, arguments.seed)
    RESULTS.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_predictions(rows, predictions)
    print(json.dumps(report["overall"], indent=2))
    print(f"Wrote {RESULTS}")
    print(f"Wrote {PREDICTIONS}")


if __name__ == "__main__":
    main()
