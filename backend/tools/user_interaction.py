"""User interaction utilities for TSP path comparison tool."""

from typing import List, Tuple, Optional
import networkx as nx

from .path_utils import expand_manual_path, calculate_path_cost, input_manual_path
from .comparison_utils import compare_paths, display_heuristic_vs_optimal_comparison


def handle_manual_path_input(
    args,
    all_nodes: List[str],
    G_map: nx.DiGraph,
    sp_graph,
    tsp_full_route: List[str],
    tsp_expanded_cost: float,
    tour: List[str],
    compact_cost: float,
    optimal_tour: Optional[List[str]],
    optimal_compact_cost: Optional[float],
    optimal_full_route: Optional[List[str]],
    optimal_expanded_cost: Optional[float],
    tsp_solve_time: float,
    optimal_computation_time: Optional[float]
):
    """Handle manual path input and comparison."""
    # Get manual path from user only if --manual flag is set
    if not args.manual:
        print("\n" + "=" * 70)
        print("Skipping manual path input (use --manual flag to enable)")
        print("=" * 70)

        # If optimal was computed, show comparison between heuristic and optimal
        if optimal_tour and optimal_compact_cost is not None:
            display_heuristic_vs_optimal_comparison(
                tour,
                compact_cost,
                optimal_tour,
                optimal_compact_cost,
                tsp_solve_time,
                optimal_computation_time,
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
                tour,
                compact_cost,
                optimal_tour,
                optimal_compact_cost,
                tsp_solve_time,
                optimal_computation_time,
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