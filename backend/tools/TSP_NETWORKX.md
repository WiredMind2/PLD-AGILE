# NetworkX-based TSP (Christofides-style) — Overview

This document briefly explains the TSP implementation in `app/utils/TSP/TSP_networkx.py`, how it is used, its complexity characteristics, and practical notes for usage.

## Purpose

Provide a fast, practical approximation of the Travelling Salesman Problem (TSP) over a road map parsed from the repository XML maps. The implementation computes a compact tour of required locations and can expand that compact tour into a full node-level driving route.

## High-level pipeline

1. Map → directed graph
   - Parse the XML map to build a directed NetworkX graph `G_map` where nodes are intersection ids (strings) and directed edges have attribute `weight` (segment length in meters).

2. Pairwise shortest paths
   - For each requested TSP location `src`, run Dijkstra (`nx.single_source_dijkstra`) on `G_map` to obtain distances and shortest-path node sequences to all other nodes.
   - Build `sp_graph[src][tgt] = { 'path': [...], 'cost': distance }` for all requested pairs.

3. Metric complete graph construction
   - Form a directed cost matrix and run Floyd–Warshall closure to ensure shortest directed costs between all pairs.
   - Restrict to the largest mutually-reachable component (pairs with finite cost both directions) to guarantee a metric symmetric subproblem.
   - Symmetrize distances with `min(cost(u,v), cost(v,u))` and return an undirected metric complete graph suitable for Christofides.

4. Christofides-style approximate solver
   - Compute an MST of the metric graph.
   - Find odd-degree nodes of the MST and compute a minimum-weight perfect matching among them.
   - Combine MST + matching into an Eulerian multigraph, extract an Eulerian circuit and shortcut repeated nodes to obtain a Hamiltonian (compact) tour.

5. Expansion (optional)
   - Use `sp_graph` to expand the compact tour into a full node-level route by concatenating the shortest-path legs between consecutive tour nodes.

## Complexity notes

- Building `G_map`: O(|V| + |E|) for parsing and insertion.
- Pairwise Dijkstra: O(k * (E + V log V)) where k is number of TSP nodes (one Dijkstra per `src`).
- Floyd–Warshall closure: O(k^3) on the chosen component (can be heavy for large k).
- Christofides steps: polynomial (MST, matching, Eulerian tour) but matching cost depends on the odd-node subset size.

Practical implication: designed for medium-size k (tens to low hundreds). For very large k you may prefer heuristics, clustering, or specialized TSP solvers.

## Robustness & limitations

- The algorithm filters out requested nodes that are not present in `G_map` (it logs a warning).
- If nodes are not mutually reachable, the implementation restricts the problem to the largest mutually-reachable component (some requested nodes may be dropped).
- Directional asymmetry is resolved by symmetrization (min of forward/backward costs). If asymmetry matters, consider an asymmetric TSP approach.
- If a shortest-path leg is missing when expanding the compact tour, the expansion raises an error (caller should handle this case).

## Inputs and outputs

- Input: XML map file (road network) and a list of TSP node ids (locations to visit). Delivery requests can be used to build the list of nodes.
- Output: Compact tour (sequence of location node ids) and metric cost. Optionally, an expanded node-level route and expanded cost.

## Practical suggestions

- Pre-filter or cluster locations when k is large.
- Surface diagnostics to callers (which nodes were dropped and why). The demo script and service can be extended to return that information.
- Consider integrating an external high-performance solver (LKH/Concorde) if you need near-optimal tours for large instances.

## Related files

- Implementation: `app/utils/TSP/TSP_networkx.py`
- Service wrapper: `app/services/TSPService.py`
- Demo/benchmark: `backend/tools/demo_tsp_networkx.py`

---
Short and focused — ask if you want this expanded into a longer README with diagrams, sample inputs/outputs, or benchmarking recommendations.
