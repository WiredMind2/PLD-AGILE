# NetworkX-based TSP (Christofides-style) — Complete Guide

This file explains exactly what `app/utils/TSP/TSP_networkx.py` does, step-by-step, how to call it, and important caveats.

**Target audience:** Developers who want to understand the algorithm and integrate the solver into the service layer.

---

## Table of Contents
1. [What is the Traveling Salesman Problem (TSP)?](#what-is-tsp)
2. [Why Christofides Algorithm?](#why-christofides)
3. [Algorithm Overview](#algorithm-overview)
4. [Implementation Details](#implementation-details)
5. [API Usage](#api-usage)
6. [Complexity Analysis](#complexity-analysis)
7. [Limitations and Recommendations](#limitations-and-recommendations)

---

## What is the Traveling Salesman Problem (TSP)?

The **Traveling Salesman Problem** is a classic optimization problem in computer science and operations research:

> **Problem Statement:** Given a list of cities (nodes) and the distances between each pair of cities, what is the shortest possible route that visits each city exactly once and returns to the starting city?

### Key Characteristics:
- **NP-hard:** No known polynomial-time algorithm for finding the optimal solution
- **Combinatorial explosion:** For n cities, there are (n-1)!/2 possible tours
- **Practical importance:** Route optimization, logistics, circuit board drilling, DNA sequencing

### Example:
```
Cities: A, B, C, D
Distances: 
  A-B: 10, A-C: 15, A-D: 20
  B-C: 35, B-D: 25, C-D: 30

One possible tour: A → B → D → C → A (total: 10 + 25 + 30 + 15 = 80)
Optimal tour:      A → B → C → D → A (total: 10 + 35 + 30 + 20 = 95)
(Note: This is illustrative; actual optimal depends on triangle inequality)
```

---

## Why Christofides Algorithm?

Since finding the optimal TSP solution is computationally infeasible for large instances, we use **approximation algorithms** that guarantee solutions within a certain factor of optimal.

### Christofides Algorithm (1976)
- **Approximation ratio:** 1.5× optimal (guaranteed to find a solution at most 50% longer than optimal)
- **Polynomial time:** O(n³) complexity
- **Best known approximation** for metric TSP until 2020
- **Requirement:** Must satisfy the triangle inequality: d(a,c) ≤ d(a,b) + d(b,c)

### Why it works:
1. Combines graph theory (MST, matching) with Eulerian circuits
2. Exploits the metric property to shortcut paths
3. Balances solution quality with computational efficiency

---

## Algorithm Overview

The Christofides algorithm consists of five main phases:

### Phase 1: Minimum Spanning Tree (MST)
**Goal:** Connect all nodes with minimum total edge weight.

**Why?** The MST provides a lower bound on the TSP tour cost (any tour must weigh at least as much as the MST).

**Algorithm:** Kruskal's or Prim's algorithm
```
MST cost ≤ Optimal TSP cost
```

### Phase 2: Find Odd-Degree Vertices
**Goal:** Identify vertices with an odd number of edges in the MST.

**Why?** An Eulerian circuit (which visits every edge exactly once) only exists in graphs where all vertices have even degree.

**Property:** The number of odd-degree vertices in any graph is always even (handshaking lemma).

### Phase 3: Minimum-Weight Perfect Matching
**Goal:** Pair up odd-degree vertices with minimum total edge weight.

**Why?** Adding these matching edges to the MST makes all vertices have even degree, creating an Eulerian multigraph.

**Algorithm:** Blossom algorithm or similar matching algorithm

### Phase 4: Build Eulerian Circuit
**Goal:** Find a circuit that traverses every edge exactly once.

**Why?** This circuit visits all nodes (but may visit some multiple times).

**Property:** Since all vertices now have even degree, an Eulerian circuit is guaranteed to exist.

### Phase 5: Shortcutting (Create Hamiltonian Circuit)
**Goal:** Convert the Eulerian circuit to a Hamiltonian circuit (visiting each node exactly once).

**How?** When the Eulerian circuit would revisit a node, skip directly to the next unvisited node.

**Why this works:** The triangle inequality ensures that the shortcut is no longer than the original path.

---

## Implementation Details

Our implementation in `TSP_networkx.py` follows the Christofides algorithm with adaptations for real-world routing on directed graphs.

### Inputs
- **Map:** XML map parsed by `app.services.XMLParser.parse_map()` → intersections and road segments
- **Nodes:** Explicit list of node IDs (strings) to include in the TSP via `nodes` argument or `Tour` object
- **Optional:** `pickup_delivery_pairs` - list of `(pickup_node, delivery_node)` tuples for post-processing to enforce pickup-before-delivery ordering

### Step 0: Build Directed Map Graph (G_map)
**Purpose:** Represent the road network as a graph structure.

**Process:**
- Convert parsed map data into a directed NetworkX graph `G_map`
- Each intersection ID becomes a node (string)
- Each road segment becomes a directed edge with `weight` attribute = segment length (meters)
- Handle one-way streets naturally with directed edges

**Output:** `G_map` - directed graph representing the entire road network

### Step 1: Compute Pairwise Shortest Paths
**Purpose:** Find shortest paths between all delivery/pickup locations.

**Algorithm:** Dijkstra's algorithm from each requested node

**Process:**
- For each requested source node `s` in `nodes`, run Dijkstra (`nx.single_source_dijkstra`) on `G_map`
- Compute shortest-path distances and node sequences to all other nodes
- Build `sp_graph[s][t] = { 'path': [...], 'cost': distance }` for every pair (s, t)
- If a path is unreachable, cost is set to `+∞` and path may be `None`

**Complexity:** O(k × (E + V log V)) where k = number of requested nodes

**Why Dijkstra?**
- Handles directed graphs with non-negative weights
- Efficient for sparse graphs (typical in road networks)
- Computes exact shortest paths (unlike heuristics)

### Step 2: Build Metric Complete Graph
**Purpose:** Transform directed road network into symmetric metric graph for Christofides.

**Process:**

1. **Initialize cost matrix** from `sp_graph` costs

2. **Floyd-Warshall closure** to compute all-pairs shortest paths
   - Ensures transitive closure of shortest paths
   - Complexity: O(k³) where k = number of nodes
   
3. **Find strongly connected component**
   - Identify largest mutually-reachable set of nodes
   - Ensures every node can reach every other node
   - Guarantees a valid TSP solution exists

4. **Symmetrization** (key step for directed → undirected)
   - For each pair (u, v): `d(u,v) = min(cost(u→v), cost(v→u))`
   - Takes the shorter of the two directed paths
   - Creates symmetric distance function

5. **Build `G_metric`**
   - Undirected complete graph with symmetric edge weights
   - Satisfies triangle inequality (metric property)
   - Ready for Christofides algorithm

**Why symmetrization?**
- Christofides requires symmetric (undirected) distances
- Real road networks are directed (one-way streets, different distances each direction)
- Taking the minimum preserves the metric property while handling asymmetry

### Step 3: Christofides Algorithm (Core TSP Solver)
**Purpose:** Compute an approximate TSP tour guaranteed to be ≤ 1.5× optimal.

**Detailed Process:**

#### 3a. Compute Minimum Spanning Tree (MST)
```python
mst = nx.minimum_spanning_tree(G_metric)
```
- Connects all nodes with minimum total edge weight
- MST cost ≤ Optimal TSP cost (lower bound)

#### 3b. Find Odd-Degree Vertices
```python
odd_vertices = [v for v in mst.nodes() if mst.degree(v) % 2 == 1]
```
- Identify vertices with odd number of edges in MST
- Count is always even (handshaking lemma)

#### 3c. Minimum-Weight Perfect Matching
```python
matching = nx.algorithms.matching.min_weight_matching(G_metric.subgraph(odd_vertices))
```
- Pair up odd-degree vertices optimally
- Uses Blossom algorithm (Edmonds, 1965)
- Adds edges to make all vertices have even degree

#### 3d. Combine MST + Matching → Eulerian Multigraph
```python
eulerian_multigraph = nx.MultiGraph(mst)
eulerian_multigraph.add_edges_from(matching)
```
- All vertices now have even degree
- Eulerian circuit guaranteed to exist

#### 3e. Find Eulerian Circuit
```python
eulerian_circuit = list(nx.eulerian_circuit(eulerian_multigraph))
```
- Traverse every edge exactly once
- May visit nodes multiple times

#### 3f. Shortcutting → Hamiltonian Tour
```python
compact_tour = []
visited = set()
for u, v in eulerian_circuit:
    if u not in visited:
        compact_tour.append(u)
        visited.add(u)
compact_tour.append(compact_tour[0])  # Close the tour
```
- Remove duplicate node visits
- Triangle inequality ensures shortcuts are valid
- Result: each node visited exactly once

**Why this gives 1.5× approximation:**
- MST ≤ OPT
- Matching ≤ 0.5 × OPT (matching odd vertices is at most half a TSP tour)
- Total: MST + Matching ≤ 1.5 × OPT
- Shortcutting doesn't increase cost (triangle inequality)

### Step 4: Post-Process Pickup/Delivery Constraints (Optional)
**Purpose:** Enforce precedence constraints for delivery logistics.

**Process:**
- If `pickup_delivery_pairs` is provided, perform conservative reordering
- For each pair `(pickup, delivery)`:
  - If `delivery` appears before `pickup` in tour, move `delivery` to immediately follow `pickup`
- Recompute compact tour cost using metric graph edge weights

**Example:**
```
Original tour: A → B → D2 → C → P2 → E → A
Constraint: P2 must come before D2
Adjusted tour: A → B → C → P2 → D2 → E → A
```

**Important Notes:**
- This is **local reordering only** (greedy approach)
- Does **not** globally optimize precedence-constrained TSP
- For exact precedence constraints, use specialized solvers (e.g., Integer Linear Programming)
- Trade-off: simplicity and speed vs. optimality

### Step 5: Expand to Full Route (Optional)
**Purpose:** Convert compact tour (delivery points only) to full turn-by-turn route.

**Process:**
1. Use pre-computed `sp_graph` shortest paths
2. For each leg (u → v) in compact tour:
   - Replace with full node sequence from `sp_graph[u][v]['path']`
3. Concatenate legs while avoiding duplicate nodes at boundaries
4. Sum leg costs to get total route distance in meters

**Example:**
```
Compact tour: A → C → E → A
Expanded route: A → B → C → D → E → F → A
                 (A→C uses path A-B-C, C→E uses path C-D-E, etc.)
```

**Use cases:**
- Turn-by-turn navigation
- Visualization on map
- Detailed route instructions
- Accurate distance/time estimates

### Outputs

1. **Compact Tour**
   - List of requested node IDs (first == last)
   - Sequence produced by Christofides + shortcutting
   - Possibly post-processed for pickup/delivery constraints
   - Example: `['A', 'C', 'E', 'B', 'A']`

2. **Compact Cost**
   - Sum of metric edge weights along compact tour
   - Measured in meters
   - Approximate (≤ 1.5× optimal for metric TSP)

3. **Expanded Route** (optional, via `expand_tour_with_paths`)
   - Full node-level route including all intersections
   - Example: `['A', 'X', 'Y', 'C', 'Z', 'E', 'W', 'B', 'A']`
   - Useful for navigation and visualization

4. **Expanded Cost** (optional)
   - Exact total distance in meters along expanded route
   - Sum of all edge weights in the path

---

## API Usage

### Basic Usage

```python
from app.utils.TSP.TSP_networkx import TSP

# Initialize solver
tsp = TSP()

# Simple TSP (just nodes)
nodes = ['A', 'B', 'C', 'D']
compact_tour, compact_cost = tsp.solve(nodes=nodes)
print(f"Tour: {compact_tour}, Cost: {compact_cost}m")
```

### With Pickup-Delivery Constraints

```python
# Define pickup-delivery pairs
pd_pairs = [('P1', 'D1'), ('P2', 'D2')]
nodes = ['P1', 'D1', 'P2', 'D2', 'E']

compact_tour, compact_cost = tsp.solve(
    nodes=nodes, 
    pickup_delivery_pairs=pd_pairs
)
```

### Using Tour Object (Service Layer)

```python
from app.models.schemas import Tour

# Tour object contains deliveries as pairs
tour = Tour(
    courier=courier,
    deliveries=[('P1', 'D1'), ('P2', 'D2')]
)

compact_tour, compact_cost = tsp.solve(tour=tour, start_node='WAREHOUSE')
```

### Expanding to Full Route

```python
# First solve to get compact tour
compact_tour, compact_cost = tsp.solve(nodes=nodes)

# Build shortest path graph
sp_graph = tsp._build_sp_graph_from_nodes(nodes)

# Expand to full route
full_route, full_cost = tsp.expand_tour_with_paths(compact_tour, sp_graph)
print(f"Full route has {len(full_route)} intersections")
```

### Service Integration (TSPService)

The `TSPService` class wraps the TSP solver for use in API endpoints:

```python
from app.services.TSPService import TSPService

service = TSPService()
tours = service.compute_tours()  # Computes tours for all couriers
```

This automatically:
- Groups deliveries by courier
- Finds warehouse locations
- Solves TSP for each courier
- Expands routes to full paths
- Calculates distance and time metrics

---

## Complexity Analysis

### Time Complexity

| Step | Operation | Complexity | Notes |
|------|-----------|------------|-------|
| 0 | Build G_map | O(V + E) | V = intersections, E = road segments |
| 1 | Pairwise Dijkstra | O(k × (E + V log V)) | k = requested nodes, dominates for large maps |
| 2 | Floyd-Warshall | O(k³) | Dominates for large k (>50 nodes) |
---

## Limitations and Recommendations

### Design Constraints

**Recommended Instance Sizes:**
- **Sweet spot:** k = 10-50 nodes (delivery locations)
- **Maximum practical:** k = 100-200 nodes
- **Beyond 200 nodes:** Consider clustering, multiple routes, or specialized solvers

### Known Limitations

#### 1. Approximation Quality
- **Guarantee:** Solution ≤ 1.5× optimal
- **Typical:** Often closer to 1.1-1.2× optimal in practice
- **Not optimal:** For guaranteed optimal solutions, use exact solvers (Branch & Bound, Dynamic Programming)

#### 2. Pickup/Delivery Constraints
- **Current approach:** Greedy local reordering
- **Not globally optimal** for precedence constraints
- **Alternative:** Use Integer Linear Programming (ILP) for exact precedence-constrained TSP

#### 3. Asymmetric Road Networks
- **Handling:** Symmetrization via min(forward, backward)
- **Loss of information:** True asymmetric costs not preserved
- **Alternative:** Use asymmetric TSP solvers if directionality is critical

#### 4. Reachability Issues
- **Problem:** Some nodes may be unreachable from others
- **Handling:** Algorithm identifies largest mutually-reachable component
- **Dropped nodes:** Not included in tour (should be reported to caller)

### Performance Optimization Tips

#### 1. Reduce Problem Size
```python
# Filter out nodes that are obviously close together
# Cluster nearby deliveries if possible
# Split large tours into multiple smaller tours
```

#### 2. Cache Shortest Paths
```python
# Reuse sp_graph if solving multiple tours on same map
sp_graph = tsp._build_sp_graph_from_nodes(all_nodes)
```

#### 3. Parallel Processing
```python
# Solve multiple courier tours in parallel
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor() as executor:
    futures = [executor.submit(tsp.solve, tour=t) for t in tours]
    results = [f.result() for f in futures]
```

#### 4. Pre-filter Nodes
```python
# Remove nodes not in map before solving
valid_nodes = [n for n in nodes if n in G_map.nodes()]
```

### When to Use Alternatives

| Scenario | Recommendation |
|----------|----------------|
| k > 200 nodes | Use metaheuristics (genetic algorithms, simulated annealing) |
| Need exact optimal | Branch & Bound, Dynamic Programming, ILP solvers |
| Hard precedence constraints | ILP with precedence constraints, CP-SAT solver |
| Real-time routing | Heuristics (nearest neighbor + local search) |
| Multiple vehicles | Vehicle Routing Problem (VRP) solvers |

### Diagnostic Recommendations

When integrating into services, surface diagnostics:
- Which nodes were dropped due to unreachability
- Which nodes are missing from the map
- Approximation quality metrics
- Computation time statistics

### Example: Handling Errors

```python
try:
    compact_tour, compact_cost = tsp.solve(nodes=nodes)
except Exception as e:
    # Handle unreachable nodes, empty tours, etc.
    logger.error(f"TSP solving failed: {e}")
    # Fallback: use simple sequential tour
    compact_tour = nodes + [nodes[0]]
    compact_cost = sum_sequential_distances(nodes)
```

---

## Mathematical Foundation

### Triangle Inequality
**Definition:** For any three points a, b, c:
```
d(a, c) ≤ d(a, b) + d(b, c)
```

**Why it matters:**
- Enables shortcutting in Eulerian circuit
- Guarantees approximation ratio
- Ensures metric space properties

### Eulerian Circuit Theorem
**Theorem:** A connected graph has an Eulerian circuit if and only if every vertex has even degree.

**Application:** By combining MST + matching, we create a graph where all vertices have even degree, guaranteeing an Eulerian circuit exists.

### Handshaking Lemma
**Lemma:** The sum of all vertex degrees in a graph is even, so the number of odd-degree vertices must be even.

**Application:** Guarantees we can always pair up odd-degree vertices for matching.

---

## References

### Academic Papers
- **Christofides, N.** (1976). "Worst-case analysis of a new heuristic for the travelling salesman problem"
- **Edmonds, J.** (1965). "Paths, trees, and flowers" (Blossom algorithm)

### Books
- **Cormen et al.** - "Introduction to Algorithms" (MIT Press)
- **Schrijver, A.** - "Combinatorial Optimization" (Springer)

### Online Resources
- NetworkX Documentation: https://networkx.org/
- TSP Visualization: https://www.math.uwaterloo.ca/tsp/

---

## Glossary

- **TSP:** Traveling Salesman Problem
- **MST:** Minimum Spanning Tree
- **Eulerian Circuit:** Path that visits every edge exactly once
- **Hamiltonian Circuit:** Path that visits every vertex exactly once
- **Metric:** Distance function satisfying triangle inequality
- **Approximation Ratio:** Worst-case ratio of algorithm solution to optimal solution
- **Dijkstra's Algorithm:** Single-source shortest path algorithm
- **Floyd-Warshall:** All-pairs shortest path algorithm
- **Blossom Algorithm:** Polynomial-time matching algorithm

---

*Last updated: October 2025*  
*For questions or improvements, contact the development team.*
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

