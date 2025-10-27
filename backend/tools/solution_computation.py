"""Solution computation utilities for TSP path comparison tool."""

from typing import List, Tuple, Optional
import time
import networkx as nx

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

from .tsp_utils import solve_tsp_tour, expand_tour_with_paths
from .path_utils import build_sp_graph_from_map
from .cache_utils import load_cached_optimal_tour, save_cached_optimal_tour
from .comparison_utils import display_heuristic_vs_optimal_comparison


def compute_tsp_solution(tsp_solver, tour_pairs: List[Tuple[str, str]], G_map: nx.DiGraph, nodes_list: List[str]):
    """Compute TSP heuristic solution."""
    # Compute TSP solution
    print("\nComputing TSP heuristic tour...")
    tour, compact_cost, tsp_solve_time = solve_tsp_tour(tsp_solver, tour_pairs)

    # Build shortest-path graph for TSP nodes
    print("Building shortest-path graph for TSP nodes...")
    sp_graph = build_sp_graph_from_map(G_map, nodes_list)

    # Expand tour
    print("Expanding tour to full path...")
    try:
        tsp_full_route, tsp_expanded_cost = expand_tour_with_paths(tour, sp_graph)
    except Exception as e:
        print(f"Error expanding tour: {e}")
        return None, None, None, None, None, None

    print(f"\nTSP Solution computed:")
    print(f"  Compact tour: {len(tour)} nodes, cost: {compact_cost:.2f}")
    print(
        f"  Expanded path: {len(tsp_full_route)} nodes, cost: {tsp_expanded_cost:.2f}"
    )
    print(f"  Tour order: {' -> '.join(tour)}")
    print(f"  Computation time: {tsp_solve_time:.3f}s")

    return tour, compact_cost, tsp_solve_time, tsp_full_route, tsp_expanded_cost, sp_graph


def compute_optimal_solution(args, tour_pairs: List[Tuple[str, str]], sp_graph, compact_cost: float, tsp_solve_time: float):
    """Compute brute-force optimal solution if requested."""
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
                from app.utils.TSP.TSP_networkx import TSP
                tsp = TSP()
                optimal_full_route, optimal_expanded_cost = expand_tour_with_paths(
                    optimal_tour, sp_graph
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
                f"This will check all valid permutations for {len(tour_pairs)} nodes..."
            )

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
                        print(f"  Checked {count:,} permutations in {elapsed:.1f}s...")

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
                        from app.utils.TSP.TSP_networkx import TSP
                        tsp = TSP()
                        optimal_full_route, optimal_expanded_cost = (
                            expand_tour_with_paths(optimal_tour, sp_graph)
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

    return optimal_tour, optimal_compact_cost, optimal_full_route, optimal_expanded_cost, optimal_computation_time