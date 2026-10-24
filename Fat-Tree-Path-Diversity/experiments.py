"""Reproducible Monte Carlo experiment and CSV output."""

from __future__ import annotations

import csv
from pathlib import Path
import random
from statistics import mean, stdev

from fat_tree import build_fat_tree, sample_failed_links
from path_metrics import count_surviving_paths, prepare_sample


CSV_FIELDS = [
    "k", "failure_pct", "trials", "sampled_host_pairs", "physical_links",
    "avg_failed_links", "mean_ecmp_paths", "ci95_ecmp_paths",
    "mean_edge_disjoint_paths", "ci95_edge_disjoint_paths",
    "ecmp_remaining_pct", "edge_disjoint_remaining_pct",
]


def run_experiment(
    k_values: list[int], failure_rates: list[float], trials: int,
    n_pairs: int, seed: int, mode: str = "independent",
) -> list[dict]:
    if trials < 1 or n_pairs < 1:
        raise ValueError("trials and n_pairs must be positive")
    if any(not 0 <= p <= 100 for p in failure_rates):
        raise ValueError("failure rates must be between 0 and 100")
    rows = []

    for k in k_values:
        graph = build_fat_tree(k)
        links = list(graph.edges())
        m = k // 2
        rng = random.Random(seed + k * 101)
        pairs = prepare_sample(k, n_pairs, rng)
        # The same sampled pairs are used across every failure rate and trial.
        # A new independent network failure realization is generated each trial.

        for p in failure_rates:
            ecmp_means = []
            independent_means = []
            failure_counts = []
            for _ in range(trials):
                failed = sample_failed_links(links, p, rng, mode=mode)
                failure_counts.append(len(failed))
                total_ecmp = 0
                total_independent = 0
                for pair in pairs:
                    ecmp, independent = count_surviving_paths(pair, failed)
                    total_ecmp += ecmp
                    total_independent += independent
                ecmp_means.append(total_ecmp / len(pairs))
                independent_means.append(total_independent / len(pairs))

            avg_ecmp = mean(ecmp_means)
            avg_independent = mean(independent_means)
            # 95% normal approximation to uncertainty of the trial means.
            ec_ci = 1.96 * stdev(ecmp_means) / trials**0.5 if trials > 1 else 0.0
            ind_ci = 1.96 * stdev(independent_means) / trials**0.5 if trials > 1 else 0.0
            rows.append({
                "k": k,
                "failure_pct": p,
                "trials": trials,
                "sampled_host_pairs": len(pairs),
                "physical_links": len(links),
                "avg_failed_links": mean(failure_counts),
                "mean_ecmp_paths": avg_ecmp,
                "ci95_ecmp_paths": ec_ci,
                "mean_edge_disjoint_paths": avg_independent,
                "ci95_edge_disjoint_paths": ind_ci,
                "ecmp_remaining_pct": 100 * avg_ecmp / (m * m),
                "edge_disjoint_remaining_pct": 100 * avg_independent / m,
            })
    return rows


def save_csv(rows: list[dict], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: round(val, 6) if isinstance(val, float) else val
                             for key, val in row.items()})
