"""TSP-specific utilities for tour solving and expansion.

This module provides higher-level TSP-specific functions.
Low-level path utilities are in path_utils.py.
"""

from typing import List, Dict, Tuple
from app.utils.TSP.TSP_networkx import TSP
from app.models.schemas import Tour

# Import canonical implementations from path_utils
from .path_utils import (
    expand_tour_with_paths,
    build_sp_graph_from_map as build_shortest_path_graph,
)

# Re-export for backwards compatibility
__all__ = ['expand_tour_with_paths', 'build_shortest_path_graph', 'solve_tsp_tour']


def solve_tsp_tour(tsp_solver: TSP, tour_pairs: List[Tuple[str, str]]) -> Tuple[List[str], float, float]:
    """Solve TSP for given tour pairs and return tour, cost, and computation time.

    Args:
        tsp_solver: Initialized TSP solver instance
        tour_pairs: List of (pickup, delivery) pairs

    Returns:
        Tuple of (tour, compact_cost, computation_time)
    """
    import time

    # Create a proper Tour object
    sample_tour = Tour(courier="default", deliveries=tour_pairs)

    tsp_start_time = time.time()
    tour, compact_cost = tsp_solver.solve(sample_tour)
    tsp_solve_time = time.time() - tsp_start_time

    return tour, compact_cost, tsp_solve_time