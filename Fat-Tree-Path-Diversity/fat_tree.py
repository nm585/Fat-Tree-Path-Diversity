"""Canonical three-tier k-ary fat-tree topology (Al-Fares et al., 2008)."""

from __future__ import annotations

import random
from typing import Iterable

import networkx as nx


def validate_k(k: int) -> None:
    """Use an even port count so every switch has k/2 up- and down-links."""
    if isinstance(k, bool) or not isinstance(k, int) or k < 4 or k % 2:
        raise ValueError("k must be an even integer >= 4")
    if k > 254:
        raise ValueError("k must be <= 254 for the paper's IPv4 addressing convention")


def host_node(pod: int, edge: int, host_id: int) -> str:
    return f"host:{pod}:{edge}:{host_id}"


def edge_node(pod: int, edge: int) -> str:
    return f"edge:{pod}:{edge}"


def agg_node(pod: int, agg: int) -> str:
    return f"agg:{pod}:{agg}"


def core_node(group: int, index: int) -> str:
    return f"core:{group}:{index}"


def canonical_link(u: str, v: str) -> tuple[str, str]:
    """Undirected physical link represented by an order-independent tuple."""
    return (u, v) if u < v else (v, u)


def build_fat_tree(k: int) -> nx.Graph:
    """Return an undirected graph of hosts, switches, and 1 Gbps links.

    The Core is organized in m=k/2 groups, each containing m switches.
    Core(group=a,index=i) attaches to Aggregation(a) in every Pod.
    """
    validate_k(k)
    m = k // 2
    graph = nx.Graph(k=k, link_capacity_gbps=1.0, topology="k-ary fat-tree")

    for group in range(m):
        for index in range(m):
            graph.add_node(
                core_node(group, index),
                tier="core", ip=f"10.{k}.{group+1}.{index+1}",
                group=group, index=index,
            )

    for pod in range(k):
        for edge in range(m):
            e = edge_node(pod, edge)
            graph.add_node(e, tier="edge", ip=f"10.{pod}.{edge}.1", pod=pod, index=edge)
            for host_id in range(2, m + 2):
                h = host_node(pod, edge, host_id)
                graph.add_node(
                    h, tier="host", ip=f"10.{pod}.{edge}.{host_id}",
                    pod=pod, edge=edge, host_id=host_id,
                )
                graph.add_edge(e, h, kind="host-edge", capacity_gbps=1.0)

        for a in range(m):
            agg = agg_node(pod, a)
            graph.add_node(agg, tier="aggregation", ip=f"10.{pod}.{m+a}.1", pod=pod, index=m+a)

            for e in range(m):
                graph.add_edge(edge_node(pod, e), agg, kind="edge-aggregation", capacity_gbps=1.0)
            for i in range(m):
                graph.add_edge(agg, core_node(a, i), kind="aggregation-core", capacity_gbps=1.0)

    return graph


def topology_counts(graph: nx.Graph) -> dict[str, int]:
    """Counts useful for validating the generated topology."""
    counts = {tier: 0 for tier in ("host", "edge", "aggregation", "core")}
    for _, attrs in graph.nodes(data=True):
        counts[attrs["tier"]] += 1
    counts["switches"] = counts["edge"] + counts["aggregation"] + counts["core"]
    counts["nodes"] = graph.number_of_nodes()
    counts["links"] = graph.number_of_edges()
    return counts


def sample_failed_links(
    physical_links: Iterable[tuple[str, str]],
    failure_percentage: float,
    rng: random.Random,
    mode: str = "independent",
) -> set[tuple[str, str]]:
    """Select failed physical links.

    independent: each physical link fails with probability p/100, so the
                 *expected*, not necessarily exact, failure fraction is p%.
    exact:       fail round(p/100 * number_of_links) distinct links.
    """
    if not 0 <= failure_percentage <= 100:
        raise ValueError("failure_percentage must be between 0 and 100")
    if mode not in {"independent", "exact"}:
        raise ValueError("mode must be 'independent' or 'exact'")

    links = [canonical_link(*edge) for edge in physical_links]
    if mode == "exact":
        n_failures = round(len(links) * failure_percentage / 100.0)
        return set(rng.sample(links, n_failures))
    p = failure_percentage / 100.0
    return {link for link in links if rng.random() < p}
