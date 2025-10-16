# NetworkX-based TSP (Christofides-style) — Step-by-step overview

This file explains exactly what `app/utils/TSP/TSP_networkx.py` does, step-by-step, how to call it, and important caveats.

Target audience: developers who want to understand the algorithm and integrate the solver into the service layer.

1) Inputs
---------
- Map: XML map parsed by `app.services.XMLParser.parse_map()` → intersections and road segments.
- Nodes: explicit list of node ids (strings) to include in the TSP. Callers provide this as the `nodes` argument to `TSP.solve(nodes=...)`.
- Optional: `pickup_delivery_pairs`: list of `(pickup_node, delivery_node)` tuples. These are used only for light post-processing to enforce pickup-before-delivery ordering in the compact tour (see `Notes` below).

2) Step 0 — Build directed map graph (G_map)
-------------------------------------------
- Convert parsed map data into a directed NetworkX graph `G_map`.
- Each intersection id becomes a node (string). Each road segment becomes a directed edge with attribute `weight` set to the segment length (meters).

3) Step 1 — Pairwise shortest paths among requested nodes
---------------------------------------------------------
- For each requested source node `s` in `nodes`, run Dijkstra (NetworkX `single_source_dijkstra`) on `G_map` to compute shortest-path distances and node sequences to all other nodes.
- Build `sp_graph[s][t] = { 'path': [...], 'cost': distance }` for every requested pair (s,t). If a path is missing, cost is set to +inf and path may be None.

4) Step 2 — Build a metric complete graph for the TSP
-----------------------------------------------------
- Initialize a directed cost matrix using the `sp_graph` costs.
- Run Floyd–Warshall closure on the directed matrix to compute all-pairs shortest directed costs.
- Identify the largest mutually-reachable set of nodes (pairs u↔v both have finite costs). Restrict the problem to that set to guarantee mutual reachability.
- Symmetrize distances for that set by taking `d(u,v) = min( cost(u,v), cost(v,u) )` and create an undirected complete graph `G_metric` (NetworkX Graph) with edge weight = d(u,v). This makes the metric suitable for Christofides.

5) Step 3 — Christofides-style approximate solver (compute compact tour)
------------------------------------------------------------------------
- Compute an MST of `G_metric` (minimum spanning tree).
- Find all odd-degree vertices of the MST.
- Compute a minimum-weight perfect matching among the odd-degree vertices (on the induced subgraph, using `networkx.algorithms.matching.min_weight_matching`).
- Combine MST edges and matching edges into an Eulerian multigraph.
- Find an Eulerian circuit of this multigraph (NetworkX provides utilities for Eulerian circuits/eulerization).
- Shortcut repeated nodes in the Eulerian circuit to obtain a Hamiltonian tour — this yields the compact tour (sequence of requested node ids). Close the tour by appending the start node to its end.

6) Step 4 — Post-process pickups/deliveries (optional)
----------------------------------------------------
- If `pickup_delivery_pairs` is provided, the implementation performs a conservative post-processing step on the compact tour: for each pair `(p,d)`, if `d` appears before `p` in the compact tour, move `d` to immediately follow `p`.
- After reordering, the compact tour cost is recomputed using the metric graph edge weights.

Notes: this is a local reordering only. It enforces immediate pickup-before-delivery precedence but does not globally optimize a precedence-constrained TSP.

7) Step 5 — (Optional) Expand compact tour into full node-level route
-------------------------------------------------------------------
- Use the previously-computed `sp_graph` to replace each compact tour leg (u→v) with the full shortest-path node sequence between u and v.
- Concatenate these legs carefully to avoid duplicating repeated nodes at leg boundaries.
- Also sum the leg costs to obtain the expanded route cost in meters.

Outputs
-------
- Compact tour: list of requested node ids (first == last). This is the sequence produced by Christofides + shortcutting (and possibly post-processed for pickups/deliveries).
- Compact cost: sum of metric edge weights along the compact tour.
- Optionally, an expanded node-level route and expanded cost (meters) when using `expand_tour_with_paths` and the `sp_graph` built earlier.

Complexity and practical guidance
---------------------------------
- Building `G_map`: O(|V| + |E|) for parsing and inserting nodes/edges.
- Pairwise Dijkstra: O(k * (E + V log V)), where k = number of requested nodes (one Dijkstra per source node).
- Floyd–Warshall closure to get all-pairs shortest directed costs: O(k^3) on the chosen component. This dominates for larger k.
- Christofides steps: polynomial; matching cost depends on the number of odd-degree vertices (≤ k).

Practical recommendations
-------------------------
- Designed for medium-sized TSP instances (k in the tens, possibly low hundreds). For much larger k consider clustering, heuristics, or an external solver.
- Pre-filter node lists to remove obviously extraneous nodes; keep k small when possible.
- Surface diagnostics to callers (which nodes were dropped due to reachability or missing from the map) when integrating into services.

Limitations
-----------
- Post-processing pickup/delivery reordering is not a substitute for an exact precedence-constrained TSP solver. If precedence constraints are crucial, consider a solver that supports precedence constraints (or formulate ILP).
- Directional asymmetry in the road network is resolved by symmetrization (min forward/backward cost); this transforms the problem into a symmetric metric TSP. If you need asymmetric TSP solutions, a different approach is required.


Examples
--------
- Single call (no pickups):

  tsp = TSP()
  compact_tour, compact_cost = tsp.solve(nodes=['A','B','C'])

- With pickup-delivery pairs (light post-processing):

  pd_pairs = [('P1','D1'), ('P2','D2')]
  compact_tour, compact_cost = tsp.solve(nodes=nodes_list, pickup_delivery_pairs=pd_pairs)

When integrating into a multi-courier service, split locations into per-courier node lists and call `solve()` per courier.

