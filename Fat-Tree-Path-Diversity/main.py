"""Command-line interface for generation and path-diversity experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random

from experiments import run_experiment, save_csv
from fat_tree import build_fat_tree, canonical_link, sample_failed_links, topology_counts
from visualize import plot_results, plot_small_topology


def cmd_generate(args: argparse.Namespace) -> None:
    graph = build_fat_tree(args.k)
    failed = sample_failed_links(graph.edges(), args.failure_rate,
                                 random.Random(args.seed), mode=args.failure_mode)
    data = {
        "configuration": {"k": args.k, "failure_percentage": args.failure_rate,
                          "failure_mode": args.failure_mode, "seed": args.seed,
                          "capacity_gbps_per_link": 1.0},
        "counts": topology_counts(graph),
        "actual_failed_links": len(failed),
        "nodes": [{"id": name, **attrs} for name, attrs in graph.nodes(data=True)],
        "links": [{"u": u, "v": v, **attrs,
                   "failed": canonical_link(u, v) in failed}
                  for u, v, attrs in graph.edges(data=True)],
    }
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Topology written to {dest}")
    print(f"Counts: {data['counts']} | Failed links: {len(failed)}")
    if args.plot:
        fig = dest.with_suffix(".png")
        plot_small_topology(graph, fig)
        print(f"Topology figure written to {fig}")


def cmd_experiment(args: argparse.Namespace) -> None:
    rows = run_experiment(
        k_values=args.k_values,
        failure_rates=args.failure_rates,
        trials=args.trials,
        n_pairs=args.pairs,
        seed=args.seed,
        mode=args.failure_mode,
    )
    out = Path(args.output_dir)
    save_csv(rows, out / "summary.csv")
    plot_results(rows, out)
    print("k  failure%  mean ECMP   mean independent  independent % remaining")
    for row in rows:
        print(f"{row['k']:2d} {row['failure_pct']:8g} {row['mean_ecmp_paths']:10.3f} "
              f"{row['mean_edge_disjoint_paths']:16.3f} "
              f"{row['edge_disjoint_remaining_pct']:16.1f}")
    print(f"\nCSV and plots written to {out.resolve()}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a k-ary Fat-Tree and study path diversity under link failures.")
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="Export topology and failed links as JSON")
    generate.add_argument("--k", type=int, default=4, help="Even switch port count >= 4")
    generate.add_argument("--failure-rate", type=float, default=0, help="Link failure percentage [0,100]")
    generate.add_argument("--failure-mode", choices=("independent", "exact"), default="independent",
                          help="Bernoulli probability or exact rounded percentage")
    generate.add_argument("--seed", type=int, default=2026)
    generate.add_argument("--output", default="results/example_topology.json")
    generate.add_argument("--plot", action="store_true", help="Plot topology (k<=8)")
    generate.set_defaults(handler=cmd_generate)

    exp = commands.add_parser("experiment", help="Monte Carlo path diversity vs failure rate")
    exp.add_argument("--k-values", nargs="+", type=int, default=[4, 8, 12])
    exp.add_argument("--failure-rates", nargs="+", type=float, default=[0, 1, 5, 10, 15, 20])
    exp.add_argument("--trials", type=int, default=100)
    exp.add_argument("--pairs", type=int, default=64, help="Fixed sampled inter-Pod host pairs per k")
    exp.add_argument("--seed", type=int, default=2026)
    exp.add_argument("--failure-mode", choices=("independent", "exact"), default="independent")
    exp.add_argument("--output-dir", default="results")
    exp.set_defaults(handler=cmd_experiment)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
