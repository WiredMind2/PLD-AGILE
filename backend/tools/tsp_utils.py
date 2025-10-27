"""TSP-specific utilities for tour solving and expansion."""

from typing import List, Dict, Tuple
import networkx as nx
from types import SimpleNamespace
from app.utils.TSP.TSP_networkx import TSP
from app.models.schemas import Tour


def expand_tour_with_paths(tour: List[str], sp_graph: Dict) -> Tuple[List[str], float]:
    """Expand a compact tour to include all intermediate nodes using shortest paths.

    Args:
        tour: List of waypoint node IDs in order
        sp_graph: Shortest path graph containing paths and costs between nodes

    Returns:
        Tuple of (expanded_path, total_cost)
    """
    if not tour or len(tour) < 2:
        return tour, 0.0

    expanded_path = []
    total_cost = 0.0

    for i in range(len(tour) - 1):
        src = tour[i]
        tgt = tour[i + 1]

        if src in sp_graph and tgt in sp_graph[src]:
            segment_info = sp_graph[src][tgt]
            segment_path = segment_info.get("path")
            segment_cost = segment_info.get("cost", float("inf"))

            if segment_path and segment_cost != float("inf"):
                # Add segment to expanded path (avoid duplicating nodes at junctions)
                if i == 0:
                    expanded_path.extend(segment_path)
                else:
                    # Skip first node of segment as it's already the last node of previous segment
                    expanded_path.extend(segment_path[1:])

                total_cost += segment_cost
            else:
                raise ValueError(f"No valid path found from {src} to {tgt}")
        else:
            raise ValueError(f"Nodes {src} and {tgt} not found in shortest path graph")

    return expanded_path, total_cost


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


def build_shortest_path_graph(G_map: nx.DiGraph, nodes_list: List[str]) -> Dict:
    """Build shortest path graph for efficient path calculations.

    Args:
        G_map: NetworkX graph representing the map
        nodes_list: List of nodes to include in the graph

    Returns:
        Dictionary containing shortest paths and costs between all node pairs
    """
    sp_graph = {}
    for src in nodes_list:
        try:
            lengths_raw, paths_raw = nx.single_source_dijkstra(
                G_map, src, weight="weight"
            )
            lengths = lengths_raw if isinstance(lengths_raw, dict) else {}
            paths = paths_raw if isinstance(paths_raw, dict) else {}
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