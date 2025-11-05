# NetworkX-based TSP — Implementation Guide (updated)

This document explains the current behavior of `app/utils/TSP/TSP_networkx.py`, the available solver options, how to call the solver from the service layer, and important caveats.

Target audience: Developers integrating or maintaining the TSP solver and service code.

---

## Highlights of the updated implementation

- The solver now supports multiple modes: a Christofides-based solver (approximation), a heuristic path-improvement flow (Christofides + 2-opt), and an exact Held–Karp (dynamic programming) fallback for very small instances.
- Pickup/delivery precedence constraints are integrated into the solver pipeline (repair/insertion + constrained 2-opt) instead of being only a greedy post-process.
- Pairwise shortest-path computation is parallelized and cached across solver calls to speed repeated solves on the same map.
- The solver returns richer metadata (which solver was used, runtime statistics, diagnostics about dropped/unreachable nodes).

This page documents the updated design, how to call the solver, complexity trade-offs, and recommendations.

## Table of contents
1. What changed and why
2. Algorithm overview (new pipeline)
3. Implementation details and solver options
4. API usage examples
5. Complexity analysis and performance notes
6. Limitations and recommendations
7. Diagnostics and outputs

---

## 1. What changed and why

- Solver selection: callers can choose mode="christofides", mode="heuristic", or mode="held_karp". The heuristic mode runs Christofides then applies 2-opt (and constrained 2-opt when pickup/delivery pairs are present) to improve the tour.
- Exact solving: Held–Karp (exponential DP) is available for small k (default cutoff k ≤ 12) when callers require an exact solution.
- Pickup/delivery handling: precedence constraints are enforced during tour improvement (repair + constrained local search) producing higher-quality and more reliable tours than the earlier one-pass greedy move.
- Performance: pairwise Dijkstra runs are executed in parallel and their results cached in `sp_graph` (caller can reuse this cache across multiple solves).
- Outputs: in addition to the compact/expanded tour and costs, the solver returns `solver_used`, `stats` (times, node counts), and `warnings` (e.g., dropped nodes, unreachable pairs).

These changes trade a small bit of code complexity for better solution quality and more predictable behavior in service contexts (multi-courier batching, repeated calls, and precedence-constrained deliveries).

## 2. Algorithm overview (new pipeline)

High-level pipeline used by `TSP_networkx.TSP.solve()`:

1. Build `G_map` (directed) from parsed XML map data.
2. Compute pairwise shortest paths between requested nodes in parallel; store `sp_graph` with path and cost for each ordered pair.
3. If necessary, identify largest strongly-connected component and drop unreachable nodes (reported in diagnostics).
4. Build a metric complete graph `G_metric` (symmetric) from `sp_graph` (symmetrization uses min(forward, backward) by default but diagnostic flags note strong asymmetry).
5. Choose solver based on `mode`:
    - held_karp: exact Held–Karp DP (only for small k; caller can set cutoff)
    - christofides: classical Christofides pipeline producing a compact tour
    - heuristic: Christofides + local search (2-opt) with optional constrained 2-opt for pickup/delivery pairs
6. If pickup/delivery pairs are present, apply constrained insertion/repair and constrained 2-opt moves to satisfy precedence while trying to keep cost low.
7. Optionally expand compact tour into a full intersection-level route using `sp_graph` paths.
8. Return compact tour, compact cost, (optional) expanded route & expanded cost, and metadata: solver_used, stats, warnings.

Notes:
- The heuristic mode is the default in typical service usage because it gives improved practical results over pure Christofides while keeping runtime reasonable.
- Held–Karp is intended for testing and verification on small instances; it is exponential and will be refused for larger k by default.

## 3. Implementation details and solver options

Inputs accepted by `TSP.solve()` (typical):
- nodes: list of node IDs to include in the tour
- tour: optional Tour object containing courier and deliveries
- pickup_delivery_pairs: list of (pickup, delivery) tuples (optional)
- start_node: optional designated start/warehouse node
- mode: one of `"heuristic"` (default), `"christofides"`, `"held_karp"`
- held_karp_cutoff: integer threshold for exact solver (default: 12)
- use_2opt: bool to enable 2-opt local search in heuristic mode (default: True)
- sp_graph_cache: optional precomputed shortest-path graph to reuse between calls

Core implementation notes:

- Pairwise shortest paths
   - Dijkstra is used from each requested node; runs are parallelized (ThreadPoolExecutor) and cached in `sp_graph`.
   - Each entry sp_graph[u][v] includes: `path` (list of intersections), `cost` (meters), and `reachable` flag.

- Metric graph construction
   - For each unordered pair (u, v), the symmetric cost is computed as min(cost(u→v), cost(v→u)).
   - A `reachability` diagnostic is computed: if a large asymmetry appears the solver adds a warning; nodes with no mutual reachability are excluded.

- Christofides core (unchanged in theory)
   - MST on `G_metric`, find odd-degree vertices, compute minimum-weight perfect matching (Blossom), form Eulerian multigraph, and shortcut to Hamiltonian cycle.

- Local improvement (2-opt and constrained 2-opt)
   - In heuristic mode, the compact tour returned by Christofides is passed through iterative 2-opt swaps to reduce cost.
   - When pickup/delivery pairs are present, constrained 2-opt (disallowing swaps that violate precedence) or a repair/insertion step ensures precedence is satisfied.
   - 2-opt continues until no improving moves are found or a move limit / time limit is reached.

- Held–Karp
   - Exact dynamic programming (O(n^2 2^n)) implementation used only when `mode='held_karp'` and k ≤ `held_karp_cutoff`.
   - Returns provably optimal compact tour and cost when used.

Outputs (expanded):
- compact_tour: list of node IDs with compact_tour[0] == compact_tour[-1]
- compact_cost: metric cost in meters
- expanded_route (optional): list of intersections (full path)
- expanded_cost (optional): meters
- solver_used: one of `"heuristic"`, `"christofides"`, `"held_karp"`
- stats: { build_time, sp_time, solve_time, n_nodes, n_dropped }
- warnings: list of strings (e.g., unreachable nodes, asymmetry notices)

## 4. API usage examples

Basic (heuristic) usage — default behavior returns improved tours via 2-opt:

```python
from app.utils.TSP.TSP_networkx import TSP

tsp = TSP()
nodes = ['A', 'B', 'C', 'D']
result = tsp.solve(nodes=nodes)  # default mode='heuristic'
compact_tour = result.compact_tour
compact_cost = result.compact_cost
print(f"Tour: {compact_tour}, Cost: {compact_cost}m, solver={result.solver_used}")
```

Force Christofides-only (no 2-opt):

```python
result = tsp.solve(nodes=nodes, mode='christofides', use_2opt=False)
```

Exact (Held–Karp) for small instances:

```python
result = tsp.solve(nodes=nodes, mode='held_karp', held_karp_cutoff=12)
# if len(nodes) > held_karp_cutoff this will raise or return an informative warning
```

With pickup/delivery pairs (precedence enforced during solving):

```python
pd_pairs = [('P1', 'D1'), ('P2', 'D2')]
result = tsp.solve(nodes=nodes, pickup_delivery_pairs=pd_pairs, mode='heuristic')
# result will contain warnings if any pair could not be satisfied
```

Expanding to a full intersection-level route (after solve):

```python
full_route, full_cost = tsp.expand_tour_with_paths(result.compact_tour, result.sp_graph)
```

Service-layer usage (TSPService typically uses `mode='heuristic'` for production runs):

```python
from app.services.TSPService import TSPService
service = TSPService()
tours = service.compute_tours(mode='heuristic')
```

## 5. Complexity analysis and performance notes

Time complexity considerations (updated):

- Build G_map: O(V + E)
- Pairwise Dijkstra: O(k × (E + V log V)) — still dominates for large maps; now parallelized across sources
- Floyd–Warshall closure (if used): O(k³) — only used conditionally; for large k we rely on Dijkstra-derived metric edges and do not run O(k³) closure in most paths
- Christofides: polynomial steps dominated by matching; matching can be O(n^3) in worst cases depending on the algorithm used
- 2-opt: iterative local search; worst-case many iterations, but typically much faster and limited by move/time caps
- Held–Karp: O(n^2 2^n) — exponential, only for small n

Practical guidance:

- Default `heuristic` mode is a good balance for k in [10, 100].
- Use `held_karp` only for verification and unit tests (k ≤ 12 by default).
- Cache and reuse `sp_graph` when solving many tours on the same map (saves repeated shortest-path computations).

## 6. Limitations and recommendations

- The heuristic mode (Christofides + 2-opt + constrained repair) yields much better practical tours than naive Christofides but still has no optimality guarantee in general.
- Precedence-constrained TSP: our constrained 2-opt and insertion repair are pragmatic; for strict global optimality under complex precedence constraints you should use ILP/CP solvers.
- Asymmetric costs: symmetrization by min(forward, backward) remains the default for metric solvers. If the directionality of roads must be preserved, consider an asymmetric TSP method (not currently provided in this module).
- Reachability: nodes without mutual reachability are removed and reported; callers should handle or pre-validate node sets.

Optimization tips:

- Reuse `sp_graph` cache across multiple calls.
- If you have many nodes (>100), cluster them and solve subproblems or use a metaheuristic VRP solver for multi-vehicle routing.

## 7. Diagnostics and outputs

The solver returns a small metadata object with keys:

- `solver_used` — which algorithm was run
- `stats` — timings (seconds) for build, sp, solve; node counts; iteration counts for 2-opt
- `warnings` — e.g., dropped nodes, unreachable pairs, asymmetry warnings, held_karp refusal due to size
- `sp_graph` — the shortest-path cache used for expansion (returned so callers can persist it)

Example result shape (Python dataclass-like):

```
Result(
   compact_tour=['A','B','C','A'],
   compact_cost=1234.5,
   expanded_route=[...],
   expanded_cost=1300.2,
   solver_used='heuristic',
   stats={'build_time':0.02, 'sp_time':0.7, 'solve_time':0.15, 'n_nodes':4, 'n_dropped':0},
   warnings=[],
   sp_graph=sp_graph
)
```

---

## References (unchanged)

- Christofides, N. (1976). "Worst-case analysis of a new heuristic for the travelling salesman problem"
- Edmonds, J. (1965). "Paths, trees, and flowers" (Blossom algorithm)
- NetworkX Documentation: https://networkx.org/

---

*Last updated: November 5, 2025*  
For questions or improvements, contact the development team.

Limitations
-----------
- The integrated repair and constrained 2-opt are pragmatic improvements but are not a substitute for a full precedence-constrained solver when strict optimality is required. Use ILP/CP for those cases.
- Asymmetric cost information is summarized and a symmetric metric is used for metric solvers; this may discard direction-specific costs. Consider an asymmetric TSP solver if directionality is critical.

Examples
--------
- Single call (heuristic default):

   tsp = TSP()
   result = tsp.solve(nodes=['A','B','C'])

- With pickup-delivery and explicit solver choice:

   pd_pairs = [('P1','D1'), ('P2','D2')]
   result = tsp.solve(nodes=nodes_list, pickup_delivery_pairs=pd_pairs, mode='heuristic')

When integrating into a multi-courier service, split locations into per-courier node lists and call `solve()` per courier; reuse `sp_graph` to save repeated shortest-path work.

