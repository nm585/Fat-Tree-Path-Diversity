# Fat-Tree Path Diversity Under Link Failures


## Overview

This project generates a three-tier Fat-Tree topology and investigates:

**How does the probability of link failure affect the number of alternative paths, and how does the switch port count (`k`) change the result?**

The implementation uses Python, NetworkX, and Matplotlib. It models the network structure and link failures, **not** packet forwarding or measured throughput.

## Topology

The generator follows the three-tier Fat-Tree architecture in Al-Fares et al. (2008): Core, Aggregation, and Edge switches, with hosts connected to Edge switches. Let `k` be the **even number of ports per switch**, and `m = k/2`.

| Property | General formula |
|---|---:|
| Pods | `k` |
| Edge switches per Pod | `m` |
| Aggregation switches per Pod | `m` |
| Hosts per Edge switch | `m` |
| Total hosts | `k³/4` |
| Total Core switches | `k²/4` |
| Total switches | `5k²/4` |
| Total physical links | `3k³/4` |
| Original six-hop ECMP routes between hosts in different Pods | `k²/4` |
| Original four-hop link-disjoint routes between Edge switches in different Pods | `k/2` |

For example, `k=4, 8, 12` gives **16, 128, 432 hosts** and **20, 80, 180 switches**, respectively. All formulas describe the intact topology **before failures**. The last two rows refer to a pair of endpoints in *different Pods*, not to network-wide totals.

Each link has a nominal capacity of 1 Gbps in the graph metadata. IP addresses encode the Pod, switch, and host location, following the paper.

![Example Fat-Tree topology](results/example_topology.png)

*Example: a generated `k=4` Fat-Tree, containing 16 hosts and 20 switches.*

## Installation and Usage

Requires Python 3.10 or later.

```bash
pip install -r requirements.txt
```

Generate a network and export link-failure flags to JSON (the optional PNG shows the intact topology):

```bash
python main.py generate --k 4 --failure-rate 10 --seed 2026 --plot
```

Run the full experiment and generate the CSV and plots:

```bash
python main.py experiment --k-values 4 8 12 --failure-rates 0 1 5 10 15 20 --trials 100 --pairs 64 --seed 2026
```

Run the tests:

```bash
python -m unittest discover -s tests -v
```

**Input parameters:** The `generate` command accepts `--k`, `--failure-rate`, `--seed`, and the optional `--failure-mode`. The `experiment` command accepts `--k-values`, `--failure-rates`, `--trials`, `--pairs`, `--seed`, and the optional `--failure-mode`. Failure rates are expressed as percentages from 0 to 100 (so `--failure-rate 10` means **10%**, not 0.10%).

**Failure modes:** The default `independent` mode gives *each physical link* a 10% chance of failing when the rate is 10%; the number of failed links varies between runs. In `exact` mode, the program selects `round(total_links × percentage / 100)` links. For example, a `k=4` network has 48 links, so `--failure-rate 10 --failure-mode exact` selects exactly 5 failed links. The JSON records which links failed; `--plot` currently draws the full original topology rather than highlighting failed links.

## Experimental Method

We tested `k = 4, 8, 12` and failure probabilities of `0%, 1%, 5%, 10%, 15%, 20%`.

For each configuration, we simulated **100 random failure realizations** and measured the average over **64 sampled host pairs in different Pods**. A fixed seed (`2026`) makes the results reproducible.

We calculated two metrics:

1. **ECMP paths:** the number of surviving original six-link shortest routes between two hosts. Paths may share physical links. Without failures there are `(k/2)²` routes.
2. **Independent paths:** the maximum number of surviving, mutually link-disjoint original four-link shortest routes **between the two Edge switches** hosting those servers. Without failures there are `k/2` routes.

We use Edge-to-Edge endpoints for the second metric because each host has only one access link, which all its end-to-end routes share. For the independent metric, each Aggregation group contributes one route if at least one of its Core choices survives.

**How the two metrics differ:** Both are computed from the *same* link-failure simulations; they are not separate experiments.

| | ECMP paths | Independent paths |
|---|---|---|
| Endpoints | Host to Host | Edge switch to Edge switch |
| Links per original shortest route | 6 (including host access links) | 4 (excluding host access links) |
| Can counted routes share links? | Yes | No |
| Intact network, `k=8` | 16 | 4 |
| 20% failure probability, `k=8` (average) | 4.292 | 2.536 |

Thus, **ECMP measures how many shortest routing alternatives remain**, while **independent paths measure how many non-overlapping alternatives remain within the switching fabric**. Neither metric directly measures throughput or the percentage of connected hosts.

## Results

### 1. Surviving independent paths (absolute count)

![Independent paths](results/edge_disjoint_paths.png)

**Example:** With `k=8`, the average drops from **4.000** independent Edge-to-Edge routes with no failures to **3.219** at 10% failure probability and **2.536** at 20%.

**Meaning:** Larger switches provide more independent route choices in absolute numbers, even after failures.

### Why independent-path survival approaches a limit

The normalized independent-path results have a theoretical explanation under the **independent link-failure** model. Let `p` be the per-link failure probability, `s = 1-p` the survival probability, and `m = k/2`.

For one Aggregation group to contribute an intact four-hop Edge-to-Edge route:

1. Its two shared Edge–Aggregation links (at the source and destination) must survive, with probability `s²`.
2. At least one of the `m` Core alternatives must have both Aggregation–Core links intact. Each alternative succeeds with probability `s²`; because these alternatives use different links, the probability at least one succeeds is `1-(1-s²)^m`.

Therefore, the probability that one group supplies a surviving route is:

$$
P_{\mathrm{group}} = (1-p)^2 \left[1-\left(1-(1-p)^2\right)^{k/2}\right].
$$

Different Aggregation groups can each contribute **one** link-disjoint route. Hence the expected absolute count is `(k/2) × P_group`, and the **expected fraction of original independent paths remaining is `P_group`**.

At **20% per-link failure probability**, this prediction compares with our measured simulation as follows:

| `k` | Theory: independent paths remaining | Simulation: independent paths remaining |
|---:|---:|---:|
| 4 | 55.71% | 57.75% |
| 8 | 62.93% | 63.40% |
| 12 | 63.86% | 63.47% |

The simulation varies because each configuration uses a finite number of random failure realizations. The formula also predicts the following values **beyond our tested `k` values** (these are calculations, **not extra simulations**):

| `k` | Theoretical fraction at 20% failures |
|---:|---:|
| 16 | 63.98% |
| 20 | 64.00% |
| 24 | 64.00% |

As `k` increases (for `0 < p < 1`), the probability that every Core alternative fails tends to zero, so the surviving fraction approaches `(1-p)²`, or **64% for `p=0.20`**. The two shared Edge–Aggregation links in each group remain a bottleneck even when there are many Core choices. Meanwhile, the **absolute number** of surviving independent paths can still grow with `k`.

**Interpretation limits:** The 64% limit concerns only our metric: the fraction of *original shortest, four-hop, link-disjoint Edge-to-Edge paths* remaining under independent physical-link failures. It is **not** a limit on host-to-host connectivity, longer backup routes, or actual throughput. It does not apply unchanged to the `exact` failure mode or correlated failures.

### 2. Independent paths remaining (percentage)

![Independent paths percentage](results/edge_disjoint_normalized.png)

This is the first metric divided by the healthy baseline `k/2`, allowing a comparison across network sizes.

**Example:** At 20% failure probability, **57.8%**, **63.4%**, and **63.5%** of the original independent routes remain for `k=4`, `8`, and `12`, respectively.

**Meaning:** Increasing `k` improves the survival percentage somewhat, but the improvement from `k=8` to `k=12` is small.

### 3. Surviving ECMP paths between hosts

![ECMP paths](results/ecmp_paths.png)

**Example:** With `k=8`, the number of original shortest host-to-host routes decreases from **16.000** to **8.637** at 10% failure probability and **4.292** at 20%.

**Meaning:** These six-link host-to-host routes include both access links, so they can be disrupted by any failed link along the path.

**Theory check (not a separate experiment):** If each link fails independently with probability `p` (expressed as a fraction), an original six-link route survives with probability `(1-p)⁶`. By linearity of expectation, the expected number of surviving ECMP routes is:

```text
E[ECMP paths] = (k² / 4) × (1-p)⁶
```

For `k=8` and `p=0.20`, the prediction is `16 × 0.8⁶ = 4.194`, versus `4.292` in the simulation. The small difference is consistent with finite random sampling. This formula applies to the **ECMP metric**, not directly to the independent-path metric.

| `k` | Failure probability | Avg. independent Edge paths | Avg. host ECMP paths |
|---:|---:|---:|---:|
| 4 | 0% / 20% | 2.000 / 1.155 | 4.000 / 1.130 |
| 8 | 0% / 20% | 4.000 / 2.536 | 16.000 / 4.292 |
| 12 | 0% / 20% | 6.000 / 3.808 | 36.000 / 9.260 |

The complete results, including intermediate failure rates, are available in [`results/summary.csv`](results/summary.csv).

## Conclusions and Limitations

Increasing the Fat-Tree size improves the absolute number of surviving independent paths. However, for any fixed independent link-failure probability, the expected surviving fraction approaches a theoretical limit of \((1-p)^2\). The simulations for \(k=4,8,12\) are consistent with this behavior.

This suggests that increasing network size provides greater absolute path redundancy, while the relative improvement in path survival gradually diminishes.

The experiment counts **original shortest paths only**, not longer fallback routes. A missing shortest route does not necessarily mean the hosts are disconnected. Failures are assumed independent, and the project does not simulate throughput, congestion, delay, or the routing algorithms in the paper.

## AI Usage

**OpenAI ChatGPT was used to assist with implementing the Python code,  and drafting this README.** 

## Reference

M. Al-Fares, A. Loukissas, and A. Vahdat, “A Scalable, Commodity Data Center Network Architecture,” *ACM SIGCOMM*, 2008. [DOI: 10.1145/1402946.1402967](https://doi.org/10.1145/1402946.1402967).
