"""
TSP solver - Main entry point.

This module provides backwards compatibility by re-exporting the TSP class
from the refactored TSP_solver module.

The TSP solver has been refactored into multiple focused modules:
- TSP_base: Core graph building functionality
- TSP_metric: Metric graph construction
- TSP_heuristics: Initial tour construction heuristics
- TSP_local_search: Local search optimization operators
- TSP_solver: Main solver orchestrating all components
"""

from .TSP_solver import TSP

__all__ = ["TSP"]

#  For backwards compatibility, also allow running this file directly
if __name__ == "__main__":
    from types import SimpleNamespace
    from typing import cast
    from app.models.schemas import Tour
    
    # Example usage
    tsp = TSP()
    # create a minimal Tour-like object from available map nodes
    G_map, nodes = tsp._build_networkx_map_graph()
    if len(nodes) < 2:
        print("Map does not contain enough nodes for a sample tour")
    else:
        # build up to 3 sample pickup-delivery pairs from map nodes
        sample_pairs = []
        for i in range(0, min(6, len(nodes)), 2):
            a = nodes[i]
            b = nodes[i + 1] if i + 1 < len(nodes) else nodes[0]
            sample_pairs.append((a, b))

        sample_tour = cast(Tour, SimpleNamespace(deliveries=sample_pairs))

        path, cost = tsp.solve(sample_tour)
        print("Compact tour:", path)
        print("Compact cost:", cost)
