# Brute-Force Optimal TSP Solver

## Overview
`compute_optimal_brute_force.py` computes the truly optimal TSP tour by exhaustively searching all valid permutations while respecting pickup-delivery precedence constraints.

## Purpose
This script is designed for **comparison and validation purposes** where you need a known optimal solution to:
- Validate heuristic algorithms
- Measure optimality gap of faster methods
- Understand worst-case behavior
- Educational/research purposes

## Algorithm
The script uses a brute-force approach:
1. Generates all permutations of pickup/delivery nodes
2. Filters permutations that respect precedence (pickup before delivery)
3. Calculates cost for each valid permutation
4. Returns the minimum-cost tour

## Performance Warning
⚠️ **Exponentially slow!** Only practical for small instances:

| Deliveries | Nodes | Permutations | Time Estimate |
|-----------|-------|--------------|---------------|
| 2 | 4 | ~10 | < 1 second |
| 3 | 6 | ~90 | < 1 second |
| 4 | 8 | ~2,500 | < 1 second |
| 5 | 10 | ~113,000 | few seconds |
| 6 | 12 | ~7 million | minutes |
| 7 | 14 | ~600 million | hours |
| 8 | 16 | ~63 billion | days |

**Recommendation:** Limit to ≤5 deliveries (10 nodes) for practical use.

## Usage

### Basic Usage
```bash
# Compute optimal for small instance
python tools/compute_optimal_brute_force.py \
  --map fichiersXMLPickupDelivery/petitPlan.xml \
  --req fichiersXMLPickupDelivery/demandePetit1.xml
```

### Limit Number of Deliveries
```bash
# Only use first 3 deliveries (6 nodes)
python tools/compute_optimal_brute_force.py \
  --map fichiersXMLPickupDelivery/petitPlan.xml \
  --req fichiersXMLPickupDelivery/demandePetit1.xml \
  --nodes 6
```

### With Start Node (Depot)
```bash
# Specify a depot/warehouse start node
python tools/compute_optimal_brute_force.py \
  --map fichiersXMLPickupDelivery/petitPlan.xml \
  --req fichiersXMLPickupDelivery/demandePetit1.xml \
  --start 123456789
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `--map PATH` | Path to map XML file (required) |
| `--req PATH`<br>`--delivery PATH` | Path to delivery requests XML file (required) |
| `--nodes N` | Limit to first N nodes (default: 0 = all) |
| `--start NODE_ID` | Optional depot/start node ID |

## Output

The script outputs:
1. Map and delivery loading information
2. Number of nodes and delivery pairs
3. Performance warning if instance is large
4. Progress updates during search
5. Best solution found so far (updated as better solutions are discovered)
6. Final optimal tour and cost

### Example Output
```
======================================================================
BRUTE-FORCE OPTIMAL TSP SOLVER
======================================================================

Loading map from: fichiersXMLPickupDelivery/petitPlan.xml
Map loaded: 217 nodes, 432 edges

Loading delivery requests from: fichiersXMLPickupDelivery/demandePetit1.xml
Loaded 5 delivery requests

Working with 5 delivery pairs (10 nodes)

Searching for optimal tour...
  Generating valid permutations (this may take a while)...
  New best: cost=12345.67, tour=N1 -> N2 -> N3...
  Checked 10,000 permutations in 2.3s (rate: 4348/s)...
  New best: cost=11234.56, tour=N1 -> N4 -> N2...
  Checked 20,000 permutations in 4.6s (rate: 4348/s)...

======================================================================
OPTIMAL SOLUTION FOUND
======================================================================
Checked 113,400 valid permutations in 26.1s
Optimal cost: 10987.65
Optimal tour (11 nodes):
  N1 -> N2 -> N4 -> N5 -> N3 -> N6 -> N8 -> N7 -> N9 -> N10 -> N1

✓ Optimal solution computed successfully!
```

## Comparison with Heuristics

Use this script alongside `compare_manual_path.py` to measure optimality gap:

```bash
# 1. Compute optimal (brute-force)
python tools/compute_optimal_brute_force.py \
  --map petitPlan.xml --req demandePetit1.xml --nodes 6

# 2. Compare heuristic solution
python tools/compare_manual_path.py \
  --map petitPlan.xml --req demandePetit1.xml
# (The heuristic solution is computed and displayed)

# 3. Calculate gap manually:
#    Gap = (Heuristic Cost - Optimal Cost) / Optimal Cost * 100%
```

## Implementation Details

### Precedence Constraints
For each pickup-delivery pair `(P, D)`:
- Pickup `P` must appear **before** delivery `D` in the tour
- No other constraints on ordering between different pairs

### Tour Construction
Tours are constructed as:
- **With start node:** `start -> nodes... -> start`
- **Without start node:** `first_node -> nodes... -> first_node`

This matches the behavior of `TSP_networkx.py`.

### Cost Calculation
Costs are computed using NetworkX shortest paths between consecutive tour nodes, identical to the heuristic solver.

## Limitations

1. **Exponential Time Complexity:** O(n!) where n is number of nodes
2. **Memory:** Stores all nodes and shortest paths in memory
3. **No Early Termination:** Checks all permutations (could add branch-and-bound)
4. **Not Suitable for Production:** Use heuristic solvers for real applications

## When to Use

✅ **Use this script when:**
- Testing/validating heuristic algorithms
- Need proven optimal solution for comparison
- Educational purposes
- Research/analysis
- Instance size ≤10 nodes

❌ **Do NOT use when:**
- Instance size >12 nodes (too slow)
- Production/real-time requirements
- Customer-facing applications
- Time-sensitive computations

## Related Tools

- **`TSP_networkx.py`**: Fast heuristic solver (Christofides-style)
- **`compare_manual_path.py`**: Compare manual paths with heuristic
- **`demo_tsp_networkx.py`**: Benchmark heuristic performance
- **`compare_tsp_methods.py`**: Compare different TSP methods

## Algorithm Choice Guide

| Instance Size | Recommended Solver |
|--------------|-------------------|
| ≤10 nodes | Brute-force (optimal) |
| 10-100 nodes | TSP_networkx (heuristic) |
| 100-1000 nodes | TSP_networkx with optimizations |
| >1000 nodes | Consider clustering/decomposition |

## Technical Notes

### Why This is Useful
Even though brute-force is impractical for large instances, it's valuable for:
1. **Validation**: Prove heuristic correctness on small instances
2. **Benchmarking**: Measure optimality gap of approximation algorithms
3. **Debugging**: Verify path expansion and cost calculation logic
4. **Education**: Understand TSP complexity firsthand

### Complexity Analysis
- **Permutations:** (2n)! / (2^n * n!) for n pickup-delivery pairs
  - This accounts for precedence constraints reducing the search space
  - Still exponential but smaller than full (2n)! permutations
- **Per-permutation cost:** O(n) to calculate tour cost
- **Total:** O(n! * n) effective complexity

---
**Created:** 2024-10-22  
**Purpose:** Optimal TSP solver for comparison/validation  
**Status:** Active - Use with caution for small instances only
