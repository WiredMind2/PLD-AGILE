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
import time
from typing import List, Tuple

from app.utils.TSP.TSP_networkx import TSP

# Import extracted utility modules
from .setup_utils import parse_arguments, initialize_tsp_solver, print_header
from .data_loading import load_map_graph, load_delivery_requests, build_tour_pairs, validate_nodes
from .solution_computation import compute_tsp_solution, compute_optimal_solution
from .user_interaction import handle_manual_path_input

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


def main():
    # Parse arguments and print header
    args = parse_arguments()
    print_header()

    # Initialize TSP solver and load map
    tsp = initialize_tsp_solver(args)
    G_map, all_nodes = load_map_graph(tsp)

    # Load delivery requests and extract nodes
    deliveries, nodes_list = load_delivery_requests(args, all_nodes)

    # Validate we have enough nodes
    if not validate_nodes(nodes_list):
        return

    # Build tour pairs
    tour_pairs = build_tour_pairs(deliveries, nodes_list)

    # Compute TSP solution
    tsp_result = compute_tsp_solution(tsp, tour_pairs, G_map, nodes_list)
    if tsp_result[0] is None:
        return

    tour, compact_cost, tsp_solve_time, tsp_full_route, tsp_expanded_cost, sp_graph = tsp_result

    # Compute optimal solution if requested
    optimal_tour, optimal_compact_cost, optimal_full_route, optimal_expanded_cost, optimal_computation_time = compute_optimal_solution(
        args, tour_pairs, sp_graph, compact_cost, tsp_solve_time
    )

    # Handle manual path input and comparison
    handle_manual_path_input(
        args, all_nodes, G_map, sp_graph,
        tsp_full_route, tsp_expanded_cost, tour, compact_cost,
        optimal_tour, optimal_compact_cost, optimal_full_route, optimal_expanded_cost,
        tsp_solve_time, optimal_computation_time
    )


if __name__ == "__main__":
    main()
