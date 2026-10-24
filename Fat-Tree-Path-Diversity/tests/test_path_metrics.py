import random
import unittest

import networkx as nx

from fat_tree import (agg_node, build_fat_tree, canonical_link, edge_node,
                      host_node, sample_failed_links)
from path_metrics import (count_surviving_paths, prepare_pair,
                          sample_interpod_host_pairs)
from experiments import run_experiment


class MetricTests(unittest.TestCase):
    def setUp(self):
        self.h1 = host_node(0, 0, 2)
        self.h2 = host_node(2, 1, 3)
        self.pair = prepare_pair(4, self.h1, self.h2)

    def test_zero_failures_gives_expected_ecmp_and_edge_disjoint(self):
        for k in (4, 8, 12):
            a = host_node(0, 0, 2)
            b = host_node(1, 1, 3)
            self.assertEqual(count_surviving_paths(prepare_pair(k, a, b), set()),
                             ((k//2)**2, k//2))

    def test_host_access_failure_does_not_change_edge_diversity(self):
        failed = {canonical_link(self.h1, edge_node(0, 0))}
        self.assertEqual(count_surviving_paths(self.pair, failed), (0, 2))

    def test_losing_one_aggregation_group(self):
        failed = {canonical_link(edge_node(0, 0), agg_node(0, 0))}
        self.assertEqual(count_surviving_paths(self.pair, failed), (2, 1))

    def test_all_source_edge_uplinks_failed(self):
        failed = {canonical_link(edge_node(0, 0), agg_node(0, i)) for i in range(2)}
        self.assertEqual(count_surviving_paths(self.pair, failed), (0, 0))

    def test_all_possible_six_hop_paths_agree_with_networkx(self):
        g = build_fat_tree(4)
        # There may be many longer simple routes; exactly six hops are ECMP routes.
        six_hop = list(nx.all_simple_paths(g, self.h1, self.h2, cutoff=6))
        six_hop = [p for p in six_hop if len(p) == 7]
        self.assertEqual(len(six_hop), 4)
        self.assertEqual(count_surviving_paths(self.pair, set())[0], len(six_hop))
        failed = sample_failed_links(g.edges(), 15, random.Random(110))
        reduced = g.copy()
        reduced.remove_edges_from(failed)
        active = [p for p in nx.all_simple_paths(reduced, self.h1, self.h2, cutoff=6)
                  if len(p) == 7]
        self.assertEqual(count_surviving_paths(self.pair, failed)[0], len(active))

    def test_independent_shortest_path_count_matches_max_flow(self):
        # Build a directed layered subgraph of *originally shortest* routes.
        # Unit-capacity max flow equals the number of link-disjoint routes.
        g = build_fat_tree(8)
        pair = prepare_pair(8, host_node(0, 0, 2), host_node(3, 1, 4))
        for seed in range(15):
            failed = sample_failed_links(g.edges(), 20, random.Random(seed))
            layer = nx.DiGraph()
            for group in pair.core_groups:
                for links in group:
                    # The 4 edges are already ordered from source Edge to destination Edge.
                    route_nodes = [edge_node(0, 0)]
                    for link in links:
                        candidates = [n for n in link if n != route_nodes[-1]]
                        self.assertEqual(len(candidates), 1)
                        route_nodes.append(candidates[0])
                    for u, v in zip(route_nodes, route_nodes[1:]):
                        if canonical_link(u, v) not in failed:
                            layer.add_edge(u, v, capacity=1)
            src, dst = edge_node(0, 0), edge_node(3, 1)
            if src in layer and dst in layer:
                expected = int(nx.maximum_flow_value(layer, src, dst))
            else:
                expected = 0
            self.assertEqual(count_surviving_paths(pair, failed)[1], expected)

    def test_sampling_different_pods(self):
        pairs = sample_interpod_host_pairs(4, 64, random.Random(3))
        self.assertEqual(len(pairs), len(set(pairs)))
        self.assertTrue(all(a.split(":")[1] != b.split(":")[1] for a, b in pairs))

    def test_reproducible_experiments(self):
        args = dict(k_values=[4], failure_rates=[0, 10, 100], trials=4, n_pairs=8, seed=123)
        x = run_experiment(**args)
        y = run_experiment(**args)
        self.assertEqual(x, y)
        self.assertEqual(x[0]["mean_ecmp_paths"], 4)
        self.assertEqual(x[0]["mean_edge_disjoint_paths"], 2)
        self.assertEqual(x[-1]["mean_ecmp_paths"], 0)
        self.assertEqual(x[-1]["mean_edge_disjoint_paths"], 0)


if __name__ == "__main__":
    unittest.main()
