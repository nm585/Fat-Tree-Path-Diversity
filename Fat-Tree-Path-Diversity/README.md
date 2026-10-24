# Fat-Tree Network Topology Generation and Path-Diversity Analysis

**Homework 1 (version 2)** — Data Center and AI Networks (361.2.2460), Semester A 2026–27  
**Reference:** M. Al-Fares, A. Loukissas, and A. Vahdat, *A Scalable, Commodity Data Center Network Architecture*, ACM SIGCOMM 2008, [DOI: 10.1145/1402946.1402967](https://doi.org/10.1145/1402946.1402967).

## 1. Research question and key distinction

**Research question:** How does the probability of physical link failures affect path diversity in a three-tier fat-tree? Does increasing the switch port count `k` improve the fraction of alternative paths that survive?

We measure **two complementary metrics** for pairs of hosts located in *different* Pods:

1. **Surviving equal-cost shortest paths (ECMP paths), host-to-host.** Count all distinct, originally six-hop paths that remain fully operational. For a healthy `k`-ary fat-tree there are `(k/2)^2` such paths per inter-Pod host pair. These paths are **not necessarily link-disjoint**.
2. **Surviving pairwise link-disjoint shortest paths, Edge-to-Edge.** For the two Edge switches hosting the selected servers, count how many *mutually link-disjoint four-hop routes* remain. With no failures, the count is `k/2`.

**Why not call host-to-host paths link-disjoint?** Every host has a **single** access cable to its Edge switch. Hence, regardless of the number of network-core routes, any two host-to-host routes share both host access links. A pair of hosts has at most **one** fully link-disjoint end-to-end path. To meaningfully study *independent* network paths, we exclude access links and place the endpoints at the **Edge switches**. The experiment reports both metrics rather than conflating them.

The metrics count surviving **original-length shortest routes**. If those routes disappear, longer paths through other switches might still exist; thus, zero here does **not** necessarily mean that the two hosts are disconnected in the general graph.

## 2. Topology generation

The implementation follows the paper's canonical three-tier fat-tree. Each switch has `k` physical **1-Gbps** ports; `k` must be even, with `k >= 4`. Let `m = k/2`.

| Item | Formula | `k=4` | `k=8` | `k=12` |
|---|---:|---:|---:|---:|
| Pods | `k` | 4 | 8 | 12 |
| Edge switches per Pod | `m` | 2 | 4 | 6 |
| Aggregation switches per Pod | `m` | 2 | 4 | 6 |
| Hosts per Edge | `m` | 2 | 4 | 6 |
| Total hosts | `k³/4` | 16 | 128 | 432 |
| Total Core switches | `k²/4` | 4 | 16 | 36 |
| Total switches | `5k²/4` | 20 | 80 | 180 |
| Total physical links | `3k³/4` | 48 | 384 | 1,296 |
| Distinct inter-Pod six-hop routes | `k²/4` | 4 | 16 | 36 |
| Independent four-hop Edge routes | `k/2` | 2 | 4 | 6 |

**Construction:**

- Each Pod has `m` Edge and `m` Aggregation switches, with each Edge connected to **every** Aggregation switch in the same Pod.
- Each Edge connects to `m` directly attached hosts.
- The Core consists of `m` groups of `m` switches. Core switch `(group=a, index=i)` connects to Aggregation switch `a` in **every** Pod.
- Edges are **undirected physical links** with metadata `capacity_gbps=1.0`. Core switches do not connect directly to each other.
- The generated graph is a `networkx.Graph`, with node attributes `tier`, `ip`, and location indices, and link attributes `kind` and `capacity_gbps`.

The IP convention follows the paper:

```text
Host:         10.<pod>.<edge>.<host_id>
Edge:         10.<pod>.<edge>.1
Aggregation:  10.<pod>.<m + aggregation_index>.1
Core:         10.<k>.<group + 1>.<index + 1>
```

The graph structure, not IP-based forwarding, is used to calculate the path metrics. We deliberately do **not** simulate TCP, packets, or the paper's TwoLevelTable/FlowClassifier/FlowScheduler because the assignment asks for topology generation, failure modeling, and a quantitative structural metric.

### Illustrative topology example

Run `python main.py generate --k 4 --failure-rate 10 --seed 2026 --plot`. The generated topology contains **16 hosts, 20 switches, and 48 links**. The example JSON records **2 failed links** with this seed (in independent-failure mode, the realized failure count is random).

![Generated k=4 fat-tree topology](results/example_topology.png)

The figure demonstrates four groups (Pods) of Edge and Aggregation switches, with four Core switches. All switches have exactly four graph links, while every host has one access link. The overlapping upper lines are the intended multi-path interconnections, not unintended duplicate edges.

## 3. Failure model and program inputs

A user selects a failed-link probability `p` in percent. By default, **every physical link fails independently** with probability `p/100` for each Monte Carlo trial (Bernoulli model). This is a *probability*, so the realized fraction of failed links in a small network will not necessarily equal exactly `p%`.

An optional `--failure-mode exact` removes `round(p/100 * number_of_links)` randomly selected links, with no replacement. Either mode can be used for standalone generation and for experiments. Each run is reproducible with the same seed.

### Inputs

| Argument | Subcommand | Meaning | Default |
|---|---|---|---|
| `--k` | `generate` | Even number of physical ports per switch | `4` |
| `--failure-rate` | `generate` | Percentage of links failing, or failure probability | `0` |
| `--failure-mode` | Both | `independent` or `exact` | `independent` |
| `--seed` | Both | Random generator seed | `2026` |
| `--output` | `generate` | JSON output path | `results/example_topology.json` |
| `--plot` | `generate` | Draw the topology (`k<=8`) | disabled |
| `--k-values` | `experiment` | List of switch port counts | `4 8 12` |
| `--failure-rates` | `experiment` | Failure percentages to test | `0 1 5 10 15 20` |
| `--trials` | `experiment` | Independent realizations per configuration | `100` |
| `--pairs` | `experiment` | Sampled inter-Pod host pairs per `k` | `64` |
| `--output-dir` | `experiment` | Output folder | `results` |

The port count must be even, `4 <= k <= 254`; the upper limit preserves the article's IPv4 address convention. Invalid failure rates outside 0–100% are rejected.

### Install and run

Requires **Python 3.10+**.

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Export a small topology with failed-link metadata and a diagram
python main.py generate --k 4 --failure-rate 10 --seed 2026 --plot

# Reproduce all plots and summary.csv
python main.py experiment --k-values 4 8 12 --failure-rates 0 1 5 10 15 20 --trials 100 --pairs 64 --seed 2026

# Run all automated tests
python -m unittest discover -s tests -v
```

You can also test a custom configuration, for example:

```bash
python main.py experiment --k-values 8 16 --failure-rates 0 2 5 10 25 --trials 200 --pairs 100 --seed 42 --output-dir my_results
```

**Reproducibility:** The reference run uses the default settings, with 100 independent network-failure realizations per `(k, p)` and a fixed, uniformly sampled set of 64 unique inter-Pod host pairs for each `k`. A 95% confidence half-width is calculated as `1.96 * sample_standard_deviation(trial_means) / sqrt(trials)`. It reflects variation across sampled failure realizations; it does not account for uncertainty from selecting a different host-pair sample.

## 4. How the path metric is computed

For hosts in different Pods, a shortest six-link host-to-host route is:

```text
Host(src) → Edge(src) → Aggregation(src,a) → Core(a,i)
          → Aggregation(dst,a) → Edge(dst) → Host(dst)
```

The group index `a` ranges from `0` to `m-1`; Core index `i` ranges from `0` to `m-1`. Thus there are `m²` candidate ECMP routes, each containing six links.

For every sampled host pair:

1. Generate its `m²` candidate paths as tuples of physical links.
2. A path survives only if **none** of its four switch-level links has failed.
3. **Host-level ECMP** additionally requires both host access links to survive; otherwise its count is zero.
4. For **Edge-level link-disjoint diversity**, group paths by Aggregation/Core group `a`. Count **one** independent route for each group having at least one surviving candidate. Different groups do not share any switch-level link.

In symbols, with `P(a,i)` denoting the four-switch-link portion of a route:

```text
ECMP(host1,host2) = 1[access links survive] * sum_a sum_i 1[P(a,i) survives]
Independent(Edge1,Edge2) = sum_a 1[there exists i with P(a,i) surviving]
```

This is a **specific shortest-path structural metric**. The Edge-to-Edge independent count is **at most `m`**, the Edge degree toward Aggregation, and is exactly `m` for an intact network. Even if one Core link fails, the group can remain available through another Core switch in that group.

For performance, the candidate routes are precomputed once per sampled pair, and trials check them against a set of failed physical links. This avoids expensive all-simple-path enumeration for every Monte Carlo trial. Tests cross-check the `k=4` six-hop path count against `networkx.all_simple_paths`.

## 5. Experimental design and measured results

**Experiment:** Hold each `k` fixed in turn (`4`, `8`, `12`) and vary `p` across `0, 1, 5, 10, 15, 20%`. For each point, perform 100 Bernoulli link-failure realizations and average the metrics over 64 sampled inter-Pod host pairs. All physical links (including host access) can fail. The Edge-only independent metric intentionally excludes the host access links from its endpoint definition.

The outputs in this repository were produced by executing the code with `--seed 2026`. Numbers below are **measured simulation results**, rounded for clarity, rather than illustrative invented data.

### Plot A — Edge-to-Edge link-disjoint shortest paths

![Average surviving independent Edge routes](results/edge_disjoint_paths.png)

**Setup:** `k = 4, 8, 12`; 0–20% link-failure probability; 100 trials at each setting; 64 fixed host pairs per `k`. The vertical axis is the **average number of surviving link-disjoint shortest paths between their two Edge switches**. Error bars denote approximate 95% confidence intervals across trial means.

**Example and interpretation:** For `k=8`, the healthy network has **4** independent four-hop Edge routes. At `p=10%`, the experiment found **3.219** on average; at `p=20%`, **2.536** remain. For `k=12`, the count decreases from **6** to **3.808** at 20%. Larger `k` produces more absolute redundant paths, although it also makes the network larger.

### Plot B — Fraction of original independent paths remaining

![Normalized independent path diversity](results/edge_disjoint_normalized.png)

**Setup:** Identical experimental parameters, but divide each measured Edge-level count by its healthy baseline `k/2`, then multiply by 100. This makes the different topologies directly comparable.

**Example and interpretation:** At `p=20%`, approximately **57.8%**, **63.4%**, and **63.5%** of the initial independent paths remain for `k=4`, `8`, and `12`, respectively. Increasing `k` improves relative resilience somewhat, but the gain is not proportional to `k`: most improvement from `k=8` to `k=12` is in the **absolute** number of choices, rather than a large change in survival fraction. The curve is not a measure of packet throughput.

### Plot C — Surviving six-hop ECMP paths between hosts

![Average surviving host ECMP paths](results/ecmp_paths.png)

**Setup:** Same configurations and trials. Here the endpoint includes each host's **single access link** and all six physical links of the path. Error bars again show approximate 95% confidence intervals across trials.

**Example and interpretation:** For `k=8`, the initial number of distinct six-hop routes is **16**. At `p=10%`, only **8.637** remain on average; at `p=20%`, **4.292** remain. This metric decays more quickly because every route requires six intact links and both host access links are single points of failure. The ECMP paths counted here share links; they are **not** fully independent end-to-end paths.

### Compact numerical summary

| `k` | Failure probability | Avg. ECMP routes per host pair | Avg. independent Edge routes | Independent routes remaining |
|---:|---:|---:|---:|---:|
| 4 | 0% | 4.000 | 2.000 | 100.0% |
| 4 | 10% | 2.108 | 1.542 | 77.1% |
| 4 | 20% | 1.130 | 1.155 | 57.8% |
| 8 | 0% | 16.000 | 4.000 | 100.0% |
| 8 | 10% | 8.637 | 3.219 | 80.5% |
| 8 | 20% | 4.292 | 2.536 | 63.4% |
| 12 | 0% | 36.000 | 6.000 | 100.0% |
| 12 | 10% | 19.343 | 4.856 | 80.9% |
| 12 | 20% | 9.260 | 3.808 | 63.5% |

Complete unrounded intermediate measures, including the confidence half-widths, number of failed links and sample sizes, are in [`results/summary.csv`](results/summary.csv).

### Why does a network remain multi-path after failures?

There are `m` independent Aggregation groups between any two Edge switches in different Pods, and each group can use any of `m` Core switches. Losing **one** of those Core connections does not necessarily destroy that entire group. A group becomes unavailable when its source Edge uplink fails, its destination Edge downlink fails, or **every** two-link Aggregation–Core–Aggregation option for that group is broken. This explains why the independent shortest-path metric declines relatively gradually.

## 6. Limitations and conclusions

1. **Link-failure model:** All physical links fail independently with the same probability. Real data-center faults can be correlated by rack, power domain, or common hardware.
2. **No traffic-performance simulation:** Links carry 1-Gbps capacity metadata, but this assignment measures structural route availability, not TCP throughput, congestion, latency, or scheduling.
3. **Shortest paths only:** Longer fallback routes are not counted. The results do not directly report connected host pairs or general graph edge connectivity after failures.
4. **Single-homed hosts:** Failure of a host's only access link destroys all host-to-host shortest routes for that endpoint; this is different from loss of redundant switch-fabric routes.
5. **Sampling:** The estimates use 64 host pairs per configuration, not every possible pair. Running additional pairs or trials improves statistical precision.

**Conclusion:** A canonical fat-tree provides multiple alternate routes. The absolute number of independent shortest routes increases with `k`. When links fail, the average number of usable routes drops, but different Core choices within an Aggregation group often preserve an independent route. The difference between host-level ECMP route count and Edge-level truly link-disjoint route count is crucial when interpreting fault tolerance.

## 7. Project files

```text
Fat-Tree-Path-Diversity/
├── main.py               # Command-line generation and experiment driver
├── fat_tree.py           # Topology generator and randomized failures
├── path_metrics.py       # ECMP and independent Edge path counting
├── experiments.py        # Monte Carlo trials and CSV summaries
├── visualize.py          # Topology image and results charts
├── tests/
│   ├── test_fat_tree.py
│   └── test_path_metrics.py
├── results/
│   ├── summary.csv
│   ├── edge_disjoint_paths.png
│   ├── edge_disjoint_normalized.png
│   ├── ecmp_paths.png
│   ├── example_topology.json
│   └── example_topology.png
├── requirements.txt
└── README.md
```

The test suite verifies: topology counts, switch degrees, address uniqueness, link capacities, deterministic failure injection, ECMP counts, independent Edge-route counts, host-access failures, and consistency with shortest paths enumerated by NetworkX for `k=4`.

## 8. AI usage disclosure

OpenAI ChatGPT (GPT-6) was used to assist with code drafting, experiment design, test generation, and README writing. The submitted code and its numerical results must be reviewed and understood by the student; responsibility for accuracy and any final edits remains with the student.
