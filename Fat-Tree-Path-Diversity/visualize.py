"""Figures generated from measured experiment results, not fabricated data."""

from __future__ import annotations

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_results(rows: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ks = sorted({row["k"] for row in rows})

    plots = [
        ("mean_edge_disjoint_paths", "ci95_edge_disjoint_paths",
         "Surviving independent shortest paths between Edge switches",
         "Average number of link-disjoint 4-hop routes",
         "edge_disjoint_paths.png"),
        ("edge_disjoint_remaining_pct", None,
         "Independent shortest-path diversity remaining",
         "Percentage of original independent paths (%)",
         "edge_disjoint_normalized.png"),
        ("mean_ecmp_paths", "ci95_ecmp_paths",
         "Surviving 6-hop ECMP routes between hosts in different Pods",
         "Average number of distinct host-to-host routes",
         "ecmp_paths.png"),
    ]
    for value_col, ci_col, title, ylabel, name in plots:
        fig, ax = plt.subplots(figsize=(9, 5.5))
        for k in ks:
            subset = sorted((r for r in rows if r["k"] == k), key=lambda r: r["failure_pct"])
            x = [r["failure_pct"] for r in subset]
            y = [r[value_col] for r in subset]
            if ci_col:
                err = [r[ci_col] for r in subset]
                ax.errorbar(x, y, yerr=err, marker="o", linewidth=1.8,
                            capsize=3, label=f"k={k}")
            else:
                ax.plot(x, y, marker="o", linewidth=1.8, label=f"k={k}")
        ax.set(title=title, xlabel="Failed-link probability (%)", ylabel=ylabel)
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.25)
        ax.legend(title="Switch port count")
        fig.tight_layout()
        fig.savefig(output_dir / name, dpi=180)
        plt.close(fig)


def plot_small_topology(graph, destination: Path) -> None:
    """Plot a labeled topology example (recommended for k=4 only)."""
    import networkx as nx

    k = graph.graph["k"]
    if k > 8:
        raise ValueError("Topology visualization is intentionally limited to k<=8")
    m = k // 2
    positions = {}
    labels = {}
    pod_gap = m * 1.8 + 1
    for u, attrs in graph.nodes(data=True):
        fields = u.split(":")
        typ = attrs["tier"]
        if typ == "core":
            a, i = int(fields[1]), int(fields[2])
            positions[u] = (((a*m+i)+.5) * (k*pod_gap)/(m*m), 3)
            labels[u] = f"C{a}{i}"
        else:
            pod = int(fields[1])
            if typ == "aggregation":
                a = int(fields[2])
                positions[u] = (pod*pod_gap + (a+.5)*pod_gap/m, 2)
                labels[u] = f"A{pod}.{a}"
            elif typ == "edge":
                e = int(fields[2])
                positions[u] = (pod*pod_gap + (e+.5)*pod_gap/m, 1)
                labels[u] = f"E{pod}.{e}"
            else:
                e, h = int(fields[2]), int(fields[3])
                positions[u] = (pod*pod_gap + (e+.5)*pod_gap/m + (h-(m+3)/2)*.42, 0)
                labels[u] = str(h)
    fig, ax = plt.subplots(figsize=(13, 6))
    nx.draw_networkx_edges(graph, positions, ax=ax, width=.65, alpha=.34)
    for tier, marker in (("host", "s"), ("edge", "o"), ("aggregation", "D"), ("core", "^")):
        nodes = [n for n, a in graph.nodes(data=True) if a["tier"] == tier]
        nx.draw_networkx_nodes(graph, positions, nodelist=nodes, node_shape=marker,
                               node_size=280 if tier != "host" else 150,
                               ax=ax, label=tier.title())
    nx.draw_networkx_labels(graph, positions, labels, font_size=7, ax=ax)
    ax.set_title(f"Three-tier k={k} Fat-Tree: k Pods, 1 Gbps physical links")
    ax.set_axis_off()
    ax.legend(loc="lower center", ncol=4)
    fig.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=180)
    plt.close(fig)
