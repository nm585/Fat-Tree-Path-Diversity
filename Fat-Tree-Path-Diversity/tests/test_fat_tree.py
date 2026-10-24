import random
import unittest

import networkx as nx

from fat_tree import (build_fat_tree, canonical_link, topology_counts,
                      sample_failed_links, host_node, edge_node)


class FatTreeTests(unittest.TestCase):
    def test_expected_counts_and_degrees(self):
        for k in (4, 8, 12):
            with self.subTest(k=k):
                g = build_fat_tree(k)
                counts = topology_counts(g)
                self.assertEqual(counts["host"], k**3 // 4)
                self.assertEqual(counts["edge"], k*k // 2)
                self.assertEqual(counts["aggregation"], k*k // 2)
                self.assertEqual(counts["core"], k*k // 4)
                self.assertEqual(counts["links"], 3*k**3 // 4)
                self.assertTrue(nx.is_connected(g))
                self.assertEqual(len({a["ip"] for _, a in g.nodes(data=True)}), g.number_of_nodes())
                for _, a in g.nodes(data=True):
                    self.assertEqual(g.degree[_], 1 if a["tier"] == "host" else k)
                for _, _, a in g.edges(data=True):
                    self.assertEqual(a["capacity_gbps"], 1.0)

    def test_specific_host_connection(self):
        g = build_fat_tree(4)
        h = host_node(2, 0, 3)
        self.assertEqual(g.nodes[h]["ip"], "10.2.0.3")
        self.assertEqual(set(g.neighbors(h)), {edge_node(2, 0)})

    def test_invalid_k(self):
        for k in (1, 2, 3, 5, 255, 256):
            with self.assertRaises(ValueError):
                build_fat_tree(k)

    def test_failure_generation_reproducibility_and_modes(self):
        g = build_fat_tree(4)
        a = sample_failed_links(g.edges(), 20, random.Random(7))
        b = sample_failed_links(g.edges(), 20, random.Random(7))
        self.assertEqual(a, b)
        failed_all = sample_failed_links(g.edges(), 100, random.Random(7))
        self.assertEqual(len(failed_all), g.number_of_edges())
        exact = sample_failed_links(g.edges(), 20, random.Random(7), "exact")
        self.assertEqual(len(exact), round(g.number_of_edges()*0.2))
        self.assertTrue(all(canonical_link(*link) in {canonical_link(*x) for x in g.edges()}
                            for link in exact))


if __name__ == "__main__":
    unittest.main()
