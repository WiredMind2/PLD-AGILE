"""
TSP (Traveling Salesman Problem) Solver Package.

This package contains a refactored TSP solver split into multiple focused modules:

Modules:
    - TSP_base: Core graph building and utility methods
    - TSP_metric: Metric graph construction from shortest paths
    - TSP_heuristics: Initial tour construction heuristics (Nearest Neighbor, Savings, Insertion)
    - TSP_local_search: Local search optimization operators (2-opt, Or-Opt, Simulated Annealing)
    - TSP_solver: Main solver orchestrating all components
    - TSP_networkx: Backwards-compatible entry point (re-exports TSP from TSP_solver)

Usage:
    from app.utils.TSP import TSP
    
    tsp = TSP()
    tour, cost = tsp.solve(tour_object, start_node="optional_start")
"""

from .TSP_solver import TSP

__all__ = ['TSP']
