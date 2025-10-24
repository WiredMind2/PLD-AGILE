"""Compare a manually input path with TSP-computed path.

Usage:
  python tools/compare_manual_path.py --map PATH --req PATH [--optimal] [--manual]
  python tools/compare_manual_path.py --map PATH --delivery PATH [--optimal] [--manual]

Examples:
  # Compare heuristic vs optimal (no manual input)
  python tools/compare_manual_path.py --map fichiersXMLPickupDelivery/petitPlan.xml --req fichiersXMLPickupDelivery/demandePetit1.xml --nodes 6 --optimal

  # Include manual path input
  python tools/compare_manual_path.py --map fichiersXMLPickupDelivery/petitPlan.xml --req fichiersXMLPickupDelivery/demandePetit1.xml --manual

  # Full comparison: heuristic vs optimal vs manual
  python tools/compare_manual_path.py --map petitPlan.xml --req demandePetit1.xml --nodes 6 --optimal --manual

  # Using --delivery alias
  python tools/compare_manual_path.py --map fichiersXMLPickupDelivery/moyenPlan.xml --delivery fichiersXMLPickupDelivery/demandeMoyen3.xml

  # Limit to first 10 nodes
  python tools/compare_manual_path.py --map petitPlan.xml --req demandePetit1.xml --nodes 10

This script allows you to:
1. Load a map and delivery requests
2. See the TSP-computed heuristic tour
3. Optionally compute the brute-force optimal tour (--optimal flag, slow!)
4. Optionally input your own manual path (--manual flag)
5. Compare the costs and visualize differences
"""

from __future__ import annotations

import os
import sys

# Ensure backend root is on sys.path for direct script execution
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

import argparse
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, cast, Optional
import networkx as nx
from types import SimpleNamespace

from app.utils.TSP.TSP_networkx import TSP
from app.models.schemas import Tour

# Import brute-force optimal solver functions
try:
    import compute_optimal_brute_force
    from compute_optimal_brute_force import (
        generate_all_valid_tours,
        tour_cost as brute_force_tour_cost,
    )

    BRUTE_FORCE_AVAILABLE = True
except ImportError:
    BRUTE_FORCE_AVAILABLE = False
    generate_all_valid_tours = None  # type: ignore
    brute_force_tour_cost = None  # type: ignore

# Cache directory
CACHE_DIR = Path(BACKEND_ROOT) / "data" / "optimal_tours"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# CACHING FUNCTIONS FOR OPTIMAL TOURS
# ============================================================================


def compute_file_hash(filepath: str) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()[:16]


def get_cache_key(map_path: str, req_path: str) -> str:
    """Generate cache key from map and request file paths."""
    map_hash = compute_file_hash(map_path)
    req_hash = compute_file_hash(req_path)
    map_name = Path(map_path).stem
    req_name = Path(req_path).stem
    return f"{map_name}_{req_name}_{map_hash}_{req_hash}"


def load_cached_optimal_tour(map_path: str, req_path: str) -> Optional[Dict]:
    """Load cached optimal tour if it exists."""
    if not map_path or not req_path:
        return None

    try:
        cache_key = get_cache_key(os.path.abspath(map_path), os.path.abspath(req_path))
        cache_path = CACHE_DIR / f"{cache_key}_optimal.json"

        if not cache_path.exists():
            return None

        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load cached optimal tour: {e}")
        return None


def save_cached_optimal_tour(
    map_path: str,
    req_path: str,
    tour: List[str],
    cost: float,
    num_permutations: int,
    computation_time: float,
) -> None:
    """Save optimal tour to cache."""
    if not map_path or not req_path:
        return

    try:
        cache_key = get_cache_key(os.path.abspath(map_path), os.path.abspath(req_path))
        cache_path = CACHE_DIR / f"{cache_key}_optimal.json"

        import datetime

        cache_data = {
            "tour": tour,
            "cost": cost,
            "num_nodes": len(tour),
            "num_permutations_checked": num_permutations,
            "computation_time_s": computation_time,
            "computed_at": datetime.datetime.now().isoformat(),
            "map_file": os.path.basename(map_path),
            "req_file": os.path.basename(req_path),
            "solver": "brute_force",
        }

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)

        print(f"  ✓ Cached optimal tour to: {cache_path.relative_to(BACKEND_ROOT)}")
    except Exception as e:
        print(f"  Warning: Failed to save cached optimal tour: {e}")


def build_sp_graph_from_map(G_map: nx.DiGraph, nodes_list: List[str]):
    """Utility: compute pairwise shortest-path lengths and paths among nodes_list."""
    sp_graph = {}
    for src in nodes_list:
        try:
            lengths_raw, paths_raw = nx.single_source_dijkstra(
                G_map, src, weight="weight"
            )
            if isinstance(lengths_raw, dict):
                lengths = cast(Dict[str, float], lengths_raw)
            else:
                lengths = {}
            if isinstance(paths_raw, dict):
                paths = cast(Dict[str, List[str]], paths_raw)
            else:
                paths = {}
        except Exception:
            lengths = {}
            paths = {}
        sp_graph[src] = {}
        for tgt in nodes_list:
            if tgt == src:
                sp_graph[src][tgt] = {"path": [src], "cost": 0.0}
            else:
                sp_graph[src][tgt] = {
                    "path": paths.get(tgt),
                    "cost": lengths.get(tgt, float("inf")),
                }
    return sp_graph


def calculate_path_cost(
    path: List[str], sp_graph: Optional[Dict] = None, G_map: Optional[nx.DiGraph] = None
) -> float:
    """Calculate the total cost of a path using either the shortest-path graph or the map graph.

    If sp_graph is provided and contains all necessary nodes, use it for fast lookup.
    Otherwise, use G_map to calculate shortest paths on-the-fly.
    """
    if not path or len(path) < 2:
        return 0.0

    total_cost = 0.0

    # Try using sp_graph first if available
    if sp_graph:
        for i in range(len(path) - 1):
            src = path[i]
            tgt = path[i + 1]
            if src in sp_graph and tgt in sp_graph[src]:
                cost = sp_graph[src][tgt].get("cost", float("inf"))
                total_cost += cost
            elif G_map is not None:
                # Fall back to calculating shortest path in the map
                try:
                    cost = nx.shortest_path_length(G_map, src, tgt, weight="weight")
                    total_cost += cost
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    return float("inf")
            else:
                return float("inf")
    elif G_map is not None:
        # Use G_map directly
        for i in range(len(path) - 1):
            src = path[i]
            tgt = path[i + 1]
            try:
                cost = nx.shortest_path_length(G_map, src, tgt, weight="weight")
                total_cost += cost
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                return float("inf")
    else:
        return float("inf")

    return total_cost


def expand_manual_path(path: List[str], G_map: nx.DiGraph) -> Tuple[List[str], float]:
    """Expand a manual path to include all intermediate nodes using shortest paths.

    Args:
        path: List of waypoint node IDs
        G_map: NetworkX graph representing the map

    Returns:
        Tuple of (expanded_path, total_cost)
    """
    if not path or len(path) < 2:
        return path, 0.0

    expanded_path = []
    total_cost = 0.0

    for i in range(len(path) - 1):
        src = path[i]
        tgt = path[i + 1]

        try:
            # Get shortest path between consecutive waypoints
            segment = nx.shortest_path(G_map, src, tgt, weight="weight")
            segment_cost = nx.shortest_path_length(G_map, src, tgt, weight="weight")

            # Add segment to expanded path (avoid duplicating nodes at junctions)
            if i == 0:
                expanded_path.extend(segment)
            else:
                # Skip first node of segment as it's already the last node of previous segment
                expanded_path.extend(segment[1:])

            total_cost += segment_cost

        except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
            print(f"Warning: No path found from {src} to {tgt}: {e}")
            return [], float("inf")

    return expanded_path, total_cost


def format_path(path: List[str], max_display: int = 20) -> str:
    """Format a path for display."""
    if not path:
        return "<empty>"

    if len(path) <= max_display:
        return " -> ".join(path)

    head = " -> ".join(path[: max_display // 2])
    tail = " -> ".join(path[-(max_display // 2) :])
    return f"{head} -> ... ({len(path) - max_display} nodes) ... -> {tail}"


def validate_path(path: List[str], valid_nodes: set) -> Tuple[bool, str]:
    """Validate that all nodes in the path exist in the map."""
    invalid_nodes = [n for n in path if n not in valid_nodes]
    if invalid_nodes:
        return False, f"Invalid nodes: {', '.join(invalid_nodes[:5])}" + (
            f" and {len(invalid_nodes) - 5} more" if len(invalid_nodes) > 5 else ""
        )
    return True, ""


def input_manual_path(valid_nodes: set) -> List[str]:
    """Prompt user to input a manual path."""
    print("\n" + "=" * 70)
    print("MANUAL PATH INPUT (Optional)")
    print("=" * 70)
    print("\nEnter your path as a sequence of node IDs separated by spaces or commas.")
    print("Available nodes:", ", ".join(sorted(list(valid_nodes))[:20]), "...")
    print("\nExamples:")
    print("  N1 N2 N3 N4")
    print("  N1, N2, N3, N4")
    print("  N1->N2->N3->N4")
    print("\nPress Enter to skip manual path input, or type 'cancel' to skip.")

    while True:
        user_input = input("\nEnter path: ").strip()

        if user_input.lower() == "cancel" or not user_input:
            return []

        # Parse the input - support multiple delimiters
        path = user_input.replace(",", " ").replace("->", " ").split()
        path = [p.strip() for p in path if p.strip()]

        if not path:
            print(
                "Error: No valid nodes found. Please try again or press Enter to skip."
            )
            continue

        # Validate nodes
        is_valid, error_msg = validate_path(path, valid_nodes)
        if not is_valid:
            print(f"Error: {error_msg}")
            print("Please try again or type 'cancel'.")
            continue

        return path


def display_path_info(label: str, compact_path: Optional[List[str]], compact_cost: Optional[float],
                      expanded_path: Optional[List[str]] = None, expanded_cost: Optional[float] = None):
    """Helper to display path information consistently."""
    if compact_path and compact_cost is not None:
        print(f"\n{label} (compact: {len(compact_path)} waypoints):")
        print(f"  {format_path(compact_path, max_display=40)}")
        print(f"  Direct cost: {compact_cost:.2f}")

        if expanded_path and expanded_cost is not None:
            print(f"\n{label} (expanded: {len(expanded_path)} nodes):")
            print(f"  {format_path(expanded_path)}")
            print(f"  Full cost: {expanded_cost:.2f}")
    elif expanded_path and expanded_cost is not None:
        print(f"\n{label} ({len(expanded_path)} nodes):")
        print(f"  {format_path(expanded_path)}")
        print(f"  Cost: {expanded_cost:.2f}")


def compare_paths(
    tsp_path: List[str],
    tsp_cost: float,
    manual_path: List[str],
    manual_cost: float,
    manual_compact: Optional[List[str]] = None,
    manual_compact_cost: Optional[float] = None,
    tsp_compact: Optional[List[str]] = None,
    tsp_compact_cost: Optional[float] = None,
    optimal_path: Optional[List[str]] = None,
    optimal_cost: Optional[float] = None,
    optimal_compact: Optional[List[str]] = None,
    optimal_compact_cost: Optional[float] = None,
):
    """Display comparison between TSP and manual paths."""
    print("\n" + "=" * 70)
    print("COMPARISON RESULTS")
    print("=" * 70)

    # Display TSP paths
    display_path_info("TSP Heuristic", tsp_compact, tsp_compact_cost, tsp_path, tsp_cost)

    # Display optimal solution if available
    display_path_info("Brute-Force Optimal", optimal_compact, optimal_compact_cost, optimal_path, optimal_cost)

    # Display manual paths
    display_path_info("Manual Path", manual_compact, manual_compact_cost, manual_path, manual_cost)

    print("\n" + "-" * 70)

    # Compare manual vs heuristic
    diff_heuristic = manual_cost - tsp_cost
    print("Manual vs TSP Heuristic:")
    if diff_heuristic == 0:
        print("  ✓ IDENTICAL: Your path has the same cost as TSP!")
    elif diff_heuristic < 0:
        print(
            f"  ★ BETTER: Your path is {abs(diff_heuristic):.2f} units shorter! ({abs(diff_heuristic/tsp_cost*100):.1f}% improvement)"
        )
    else:
        print(
            f"  ✗ LONGER: Your path is {diff_heuristic:.2f} units longer ({diff_heuristic/tsp_cost*100:.1f}% more)"
        )

    # Compare manual vs optimal if available
    if optimal_cost is not None:
        diff_optimal = manual_cost - optimal_cost
        print("\nManual vs Brute-Force Optimal:")
        if diff_optimal == 0:
            print("  ✓ OPTIMAL: Your path matches the brute-force optimal solution!")
        elif diff_optimal < 0:
            print(
                f"  ★★ BETTER: Your path is {abs(diff_optimal):.2f} units shorter than optimal! (check for errors)"
            )
        else:
            print(
                f"  Gap to optimal: {diff_optimal:.2f} units ({diff_optimal/optimal_cost*100:.1f}% suboptimal)"
            )

    # Check if paths are identical
    if tsp_path == manual_path:
        print("\n✓ Expanded paths are identical to heuristic!")
    else:
        # Find common segments
        common_count = len([
            i
            for i in range(min(len(tsp_path), len(manual_path)))
            if tsp_path[i] == manual_path[i]
        ])
        print(f"\n  First {common_count} nodes match with heuristic in expanded paths")

    print("=" * 70)


def display_heuristic_vs_optimal_comparison(tour, compact_cost, optimal_tour, optimal_compact_cost, 
                                             tsp_time=None, optimal_time=None):
    """Display comparison between heuristic and optimal solutions."""
    separator = "=" * 70
    print(f"\n{separator}")
    print("HEURISTIC VS OPTIMAL COMPARISON")
    print(separator)

    print(f"\nTSP Heuristic (compact: {len(tour)} waypoints):")
    print(f"  Cost: {compact_cost:.2f}")
    if tsp_time is not None:
        print(f"  Computation time: {tsp_time:.3f}s")

    print(f"\nBrute-Force Optimal (compact: {len(optimal_tour)} waypoints):")
    print(f"  Cost: {optimal_compact_cost:.2f}")
    if optimal_time is not None:
        print(f"  Computation time: {optimal_time:.3f}s")

    improvement = compact_cost - optimal_compact_cost
    if improvement > 0.01:
        print(
            f"\nOptimality Gap: {improvement:.2f} units ({improvement/optimal_compact_cost*100:.1f}% suboptimal)"
        )
    else:
        print("\n✓ Heuristic found the optimal solution!")

    # Display timing comparison if both times are available
    if tsp_time is not None and optimal_time is not None:
        speedup = optimal_time / tsp_time if tsp_time > 0 else float('inf')
        print(f"\nTiming Comparison:")
        print(f"  Heuristic is {speedup:.1f}× faster than brute-force")
        print(f"  Time saved: {optimal_time - tsp_time:.3f}s")

    print(separator)


def main():
    parser = argparse.ArgumentParser(
        description="Compare manual path with TSP solution"
    )
    parser.add_argument("--map", type=str, default=None, help="Map XML file to use")
    parser.add_argument(
        "--req",
        "--delivery",
        type=str,
        default=None,
        dest="req",
        help="Delivery requests XML file (contains <livraison> elements)",
    )
    parser.add_argument(
        "--nodes",
        type=int,
        default=0,
        help="Limit number of nodes (0 = use all from requests)",
    )
    parser.add_argument(
        "--optimal",
        action="store_true",
        help="Compute optimal solution using brute-force (slow, only for small instances ≤10 nodes)",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Prompt for manual path input (otherwise skip manual path)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recomputation of optimal solution (ignore cache)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("TSP PATH COMPARISON TOOL")
    print("=" * 70)

    # Initialize TSP solver
    tsp = TSP()

    # Load map
    if args.map:
        print(f"\nLoading map from: {args.map}")
        orig_builder = tsp._build_networkx_map_graph
        tsp._build_networkx_map_graph = (
            lambda xml_file_path=None, p=args.map: orig_builder(p)
        )
    else:
        print("\nUsing embedded default map")
    
    G_map, all_nodes = tsp._build_networkx_map_graph(None)
    print(f"Map loaded: {len(all_nodes)} nodes")

    # Load delivery requests or use all nodes
    deliveries = []
    nodes_list = []

    if args.req:
        print(f"\nLoading delivery requests from: {args.req}")
        try:
            from app.services.XMLParser import XMLParser

            with open(args.req, "r", encoding="utf-8") as rf:
                req_text = rf.read()
            deliveries = XMLParser.parse_deliveries(req_text)
            print(f"Loaded {len(deliveries)} delivery requests")

            # Show first few deliveries
            print("\nDelivery details:")
            for i, d in enumerate(deliveries[:5], 1):
                pickup = str(getattr(d.pickup_addr, "id", d.pickup_addr))
                delivery = str(getattr(d.delivery_addr, "id", d.delivery_addr))
                print(
                    f"  {i}. Pickup: {pickup} -> Delivery: {delivery} "
                    f"(service: {d.pickup_service_s}s + {d.delivery_service_s}s)"
                )
            if len(deliveries) > 5:
                print(f"  ... and {len(deliveries) - 5} more deliveries")

            # Extract nodes from deliveries
            nodes_from_reqs = []
            for d in deliveries:
                nodes_from_reqs.extend([
                    str(getattr(addr, "id", addr))
                    for addr in (d.pickup_addr, d.delivery_addr)
                ])

            # Keep order and uniqueness
            seen = set()
            nodes_list = [n for n in nodes_from_reqs if not (n in seen or seen.add(n))]

            # Filter to nodes present in map
            map_nodes = set(all_nodes)
            nodes_list = [n for n in nodes_list if n in map_nodes]

            if args.nodes and args.nodes > 0:
                nodes_list = nodes_list[: args.nodes]

        except Exception as e:
            print(f"Error loading requests: {e}")
            nodes_list = (
                list(all_nodes)[: args.nodes] if args.nodes > 0 else list(all_nodes)
            )
    else:
        print("\nNo delivery requests provided, using map nodes")
        nodes_list = (
            list(all_nodes)[: args.nodes] if args.nodes > 0 else list(all_nodes)
        )

    if len(nodes_list) < 2:
        print("Error: Need at least 2 nodes to create a path")
        return

    print(f"\nWorking with {len(nodes_list)} nodes:")
    print(
        f"  {', '.join(nodes_list[:20])}"
        + (f" ... and {len(nodes_list) - 20} more" if len(nodes_list) > 20 else "")
    )

    # Build tour pairs
    if deliveries:
        tour_pairs = [
            (
                str(getattr(d.pickup_addr, "id", d.pickup_addr)),
                str(getattr(d.delivery_addr, "id", d.delivery_addr)),
            )
            for d in deliveries
        ]
    else:
        # Pair adjacent nodes
        tour_pairs = []
        for k in range(0, len(nodes_list), 2):
            a = nodes_list[k]
            b = nodes_list[k + 1] if k + 1 < len(nodes_list) else nodes_list[0]
            tour_pairs.append((a, b))

    sample_tour = cast(Tour, SimpleNamespace(deliveries=tour_pairs))

    # Compute TSP solution
    print("\nComputing TSP optimal tour...")
    import time
    tsp_start_time = time.time()
    tour, compact_cost = tsp.solve(sample_tour)
    tsp_solve_time = time.time() - tsp_start_time

    # Build shortest-path graph for TSP nodes
    print("Building shortest-path graph for TSP nodes...")
    sp_graph = build_sp_graph_from_map(G_map, nodes_list)

    # Expand tour
    print("Expanding tour to full path...")
    try:
        tsp_full_route, tsp_expanded_cost = tsp.expand_tour_with_paths(tour, sp_graph)
    except Exception as e:
        print(f"Error expanding tour: {e}")
        return

    print(f"\nTSP Solution computed:")
    print(f"  Compact tour: {len(tour)} nodes, cost: {compact_cost:.2f}")
    print(
        f"  Expanded path: {len(tsp_full_route)} nodes, cost: {tsp_expanded_cost:.2f}"
    )
    print(f"  Tour order: {' -> '.join(tour)}")
    print(f"  Computation time: {tsp_solve_time:.3f}s")

    # Optionally compute brute-force optimal solution
    optimal_tour = None
    optimal_compact_cost = None
    optimal_full_route = None
    optimal_expanded_cost = None
    optimal_computation_time = None

    if not args.optimal:
        pass  # Skip optimal computation
    elif not BRUTE_FORCE_AVAILABLE:
        print(
            "\n⚠️  Brute-force module not available. Check compute_optimal_brute_force.py exists."
        )
    elif len(tour_pairs) > 6:
        print(
            f"\n⚠️  WARNING: {len(tour_pairs)} deliveries is too large for brute-force!"
        )
        print(f"   This would require checking ~{len(tour_pairs)}! permutations.")
        response = input("\nContinue anyway? (yes/no): ").strip().lower()
        if response not in ["yes", "y"]:
            print("Skipping optimal solver...")
    else:
        # First check cache (unless --force is set)
        cached_optimal = None
        if not args.force and args.map and args.req:
            cached_optimal = load_cached_optimal_tour(args.map, args.req)
        elif args.force:
            print(
                    "\n⚠️  --force flag set: Ignoring cache, will recompute optimal solution"
                )

        if cached_optimal:
            separator = "=" * 70
            print(f"\n{separator}")
            print("LOADED CACHED OPTIMAL SOLUTION")
            print(separator)
            print("✓ Found cached optimal tour!")
            print(f"  Computed: {cached_optimal.get('computed_at', 'unknown')}")
            print(
                f"  Computation time: {cached_optimal.get('computation_time_s', 0):.2f}s"
            )
            print(
                f"  Permutations checked: {cached_optimal.get('num_permutations_checked', 0):,}"
            )

            optimal_tour = cached_optimal["tour"]
            optimal_compact_cost = cached_optimal["cost"]
            optimal_computation_time = cached_optimal.get("computation_time_s", 0)

            print(
                f"  Compact tour: {len(optimal_tour)} nodes, cost: {optimal_compact_cost:.2f}"
            )
            print(f"  Tour order: {' -> '.join(optimal_tour)}")

            # Expand the cached tour
            print("  Expanding cached tour to full path...")
            try:
                optimal_full_route, optimal_expanded_cost = (
                    tsp.expand_tour_with_paths(optimal_tour, sp_graph)
                )
                print(
                    f"  Expanded path: {len(optimal_full_route)} nodes, cost: {optimal_expanded_cost:.2f}"
                )

                # Compare with heuristic
                improvement = compact_cost - optimal_compact_cost
                if improvement > 0.01:
                    print(
                        f"  ⚠️  Heuristic was {improvement:.2f} units longer ({improvement/optimal_compact_cost*100:.1f}% suboptimal)"
                    )
                else:
                    print("  ✓ Heuristic found the optimal solution!")
            except Exception as e:
                print(f"  Error expanding cached tour: {e}")
        else:
                # No cache found, compute optimal solution
                print(f"\n{'='*70}")
                print("COMPUTING OPTIMAL SOLUTION (Brute-Force)")
                print(f"{'='*70}")
                print(
                    f"This will check all valid permutations for {len(nodes_list)} nodes..."
                )

                import time

                start_time = time.time()

                best_tour = None
                best_cost = float("inf")
                count = 0

                try:
                    # Use brute-force generator
                    if generate_all_valid_tours is None or brute_force_tour_cost is None:
                        raise RuntimeError("Brute-force functions not available")
                    
                    for candidate_tour in generate_all_valid_tours(
                        tour_pairs, start_node=None
                    ):
                        count += 1

                        if count % 10000 == 0:
                            elapsed = time.time() - start_time
                            print(
                                f"  Checked {count:,} permutations in {elapsed:.1f}s..."
                            )

                        # Calculate cost
                        cost = brute_force_tour_cost(candidate_tour, sp_graph)

                        if cost < best_cost:
                            best_tour = candidate_tour
                            best_cost = cost
                            if count < 1000:  # Only print early finds
                                print(f"  New best: cost={best_cost:.2f}")

                    elapsed = time.time() - start_time

                    if best_tour:
                        optimal_tour = best_tour
                        optimal_compact_cost = best_cost
                        optimal_computation_time = elapsed

                        print(f"\n✓ Optimal solution found!")
                        print(f"  Checked {count:,} permutations in {elapsed:.1f}s")
                        print(
                            f"  Compact tour: {len(optimal_tour)} nodes, cost: {optimal_compact_cost:.2f}"
                        )
                        print(f"  Tour order: {' -> '.join(optimal_tour)}")

                        # Save to cache
                        if args.map and args.req:
                            save_cached_optimal_tour(
                                args.map,
                                args.req,
                                optimal_tour,
                                optimal_compact_cost,
                                count,
                                elapsed,
                            )

                        # Expand the optimal tour
                        print("  Expanding optimal tour to full path...")
                        try:
                            optimal_full_route, optimal_expanded_cost = (
                                tsp.expand_tour_with_paths(optimal_tour, sp_graph)
                            )
                            print(
                                f"  Expanded path: {len(optimal_full_route)} nodes, cost: {optimal_expanded_cost:.2f}"
                            )

                            # Compare with heuristic
                            improvement = compact_cost - optimal_compact_cost
                            if improvement > 0.01:
                                print(
                                    f"  ⚠️  Heuristic was {improvement:.2f} units longer ({improvement/optimal_compact_cost*100:.1f}% suboptimal)"
                                )
                            else:
                                print("  ✓ Heuristic found the optimal solution!")
                        except Exception as e:
                            print(f"  Error expanding optimal tour: {e}")
                    else:
                        print("  No valid tour found")

                except Exception as e:
                    print(f"\n⚠️  Error running brute-force solver: {e}")
                    print("Continuing with heuristic solution...")

    # Get manual path from user only if --manual flag is set
    if not args.manual:
        print("\n" + "=" * 70)
        print("Skipping manual path input (use --manual flag to enable)")
        print("=" * 70)

        # If optimal was computed, show comparison between heuristic and optimal
        if optimal_tour and optimal_compact_cost is not None:
            display_heuristic_vs_optimal_comparison(
                tour, compact_cost, optimal_tour, optimal_compact_cost,
                tsp_solve_time, optimal_computation_time
            )

        print("\nThank you for using the TSP comparison tool!")
        return

    # Manual path input enabled
    valid_nodes = set(all_nodes)
    manual_path_compact = input_manual_path(valid_nodes)

    if not manual_path_compact:
        print("\nNo manual path provided.")

        # If optimal was computed, show comparison between heuristic and optimal
        if optimal_tour and optimal_compact_cost is not None:
            display_heuristic_vs_optimal_comparison(
                tour, compact_cost, optimal_tour, optimal_compact_cost,
                tsp_solve_time, optimal_computation_time
            )

        print("\nThank you for using the TSP comparison tool!")
        return

    # Expand manual path to include all intermediate nodes
    print("\nExpanding manual path with shortest paths...")
    manual_path_expanded, manual_expanded_cost = expand_manual_path(
        manual_path_compact, G_map
    )

    if manual_expanded_cost == float("inf"):
        print("Error: Manual path contains unreachable segments")
        return

    # Also calculate direct cost (between waypoints only)
    manual_compact_cost = calculate_path_cost(manual_path_compact, sp_graph, G_map)

    # Compare paths (include TSP compact tour and optimal if computed)
    compare_paths(
        tsp_full_route,
        tsp_expanded_cost,
        manual_path_expanded,
        manual_expanded_cost,
        manual_path_compact,
        manual_compact_cost,
        tour,
        compact_cost,
        optimal_full_route,
        optimal_expanded_cost,
        optimal_tour,
        optimal_compact_cost,
    )

    # Option to try another path
    while True:
        again = input("\nTry another path? (y/n): ").strip().lower()
        if again not in ["y", "yes"]:
            break

        manual_path_compact = input_manual_path(valid_nodes)
        if not manual_path_compact:
            break

        print("\nExpanding manual path with shortest paths...")
        manual_path_expanded, manual_expanded_cost = expand_manual_path(
            manual_path_compact, G_map
        )

        if manual_expanded_cost == float("inf"):
            print("Error: Manual path contains unreachable segments")
            continue

        manual_compact_cost = calculate_path_cost(manual_path_compact, sp_graph, G_map)

        compare_paths(
            tsp_full_route,
            tsp_expanded_cost,
            manual_path_expanded,
            manual_expanded_cost,
            manual_path_compact,
            manual_compact_cost,
            tour,
            compact_cost,
            optimal_full_route,
            optimal_expanded_cost,
            optimal_tour,
            optimal_compact_cost,
        )

    print("\nThank you for using the TSP comparison tool!")


if __name__ == "__main__":
    main()
