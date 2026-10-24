"""Surviving ECMP and link-disjoint shortest paths for inter-Pod pairs."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Sequence

from fat_tree import (
    agg_node, canonical_link, core_node, edge_node, host_node,
    validate_k,
)

Link = tuple[str, str]


@dataclass(frozen=True)
class PreparedPair:
    """A fixed host pair and all its *original* six-hop fat-tree routes.

    Each core_group contains m candidate 4-link paths between the two Edge
    switches. A shortest Edge-to-Edge route takes one Aggregation/Core group.
    Routes within a group share access to its source/destination Aggregation,
    so at most one path per group can be link-disjoint from other groups.
    """
    source_host: str
    destination_host: str
    host_access_links: tuple[Link, Link]
    core_groups: tuple[tuple[tuple[Link, Link, Link, Link], ...], ...]


def sample_interpod_host_pairs(k: int, count: int, rng: random.Random) -> list[tuple[str, str]]:
    """Uniform random unique unordered host pairs in different Pods."""
    validate_k(k)
    if count < 1:
        raise ValueError("count must be >= 1")
    m = k // 2
    hosts_per_pod = m * m
    max_pairs = (k * (k - 1) // 2) * hosts_per_pod * hosts_per_pod
    count = min(count, max_pairs)
    seen: set[tuple[str, str]] = set()
    while len(seen) < count:
        p1, p2 = sorted(rng.sample(range(k), 2))
        h1 = host_node(p1, rng.randrange(m), rng.randrange(2, m + 2))
        h2 = host_node(p2, rng.randrange(m), rng.randrange(2, m + 2))
        seen.add((h1, h2))
    return sorted(seen)


def prepare_pair(k: int, host1: str, host2: str) -> PreparedPair:
    validate_k(k)
    m = k // 2
    def parse(host: str) -> tuple[int, int, int]:
        fields = host.split(":")
        if len(fields) != 4 or fields[0] != "host":
            raise ValueError(f"Not a host node: {host}")
        pod, edge, hid = (int(x) for x in fields[1:])
        if not (0 <= pod < k and 0 <= edge < m and 2 <= hid < m + 2):
            raise ValueError(f"Host not valid for k={k}: {host}")
        return pod, edge, hid

    p1, e1, _ = parse(host1)
    p2, e2, _ = parse(host2)
    if p1 == p2:
        raise ValueError("This experiment requires hosts in different Pods")
    src_e = edge_node(p1, e1)
    dst_e = edge_node(p2, e2)
    access = (canonical_link(host1, src_e), canonical_link(dst_e, host2))

    groups = []
    for a in range(m):
        src_a = agg_node(p1, a)
        dst_a = agg_node(p2, a)
        paths = []
        for i in range(m):
            core = core_node(a, i)
            paths.append((
                canonical_link(src_e, src_a),
                canonical_link(src_a, core),
                canonical_link(core, dst_a),
                canonical_link(dst_a, dst_e),
            ))
        groups.append(tuple(paths))
    return PreparedPair(host1, host2, access, tuple(groups))


def count_surviving_paths(pair: PreparedPair, failed_links: set[Link]) -> tuple[int, int]:
    """Return (host-to-host shortest ECMP paths, Edge-to-Edge disjoint paths).

    ECMP counts distinct six-hop routes (NOT mutually link-disjoint routes).
    Independent paths count link-disjoint shortest routes BETWEEN EDGE SWITCHES:
    one per Aggregation group with at least one surviving four-hop route.
    Hosts are single-homed; they can have at most 1 truly link-disjoint path
    end-to-end, so they are excluded from the independent-path endpoints.
    """
    edge_disjoint = 0
    ecmp_switch = 0
    for group in pair.core_groups:
        surviving_group = sum(all(link not in failed_links for link in path) for path in group)
        ecmp_switch += surviving_group
        edge_disjoint += int(surviving_group > 0)

    host_connected = all(link not in failed_links for link in pair.host_access_links)
    return (ecmp_switch if host_connected else 0), edge_disjoint


def prepare_sample(k: int, n_pairs: int, rng: random.Random) -> list[PreparedPair]:
    pairs = sample_interpod_host_pairs(k, n_pairs, rng)
    return [prepare_pair(k, a, b) for a, b in pairs]
