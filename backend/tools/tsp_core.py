"""TSP Core Utilities: Core functions for TSP operations.

This module provides core TSP utilities that are used across multiple tools.
It imports canonical implementations from specialized modules:
- path_utils: Path and graph operations
- cache_utils: Caching functionality

Legacy functions are maintained here only for backwards compatibility.
"""

import os
import sys
from typing import List, Tuple, Optional
from itertools import permutations

# Ensure backend root is on sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# Import canonical implementations
from .path_utils import (
    build_sp_graph_from_map as build_sp_graph,
    tour_cost,
    expand_path,
    expand_manual_path,
    calculate_path_cost,
    format_path,
    validate_path,
    input_manual_path,
)

# Re-export for backwards compatibility
__all__ = [
    'build_sp_graph',
    'tour_cost',
    'expand_path',
    'expand_manual_path',
    'calculate_path_cost',
    'format_path',
    'validate_path',
    'input_manual_path',
    'generate_all_valid_tours',
    'is_valid_tour',
    'compute_optimal_brute_force',
]


def is_valid_tour(tour: List[str], pd_pairs: List[Tuple[str, str]], start_node: Optional[str]) -> bool:
    """Check if a tour respects pickup-before-delivery constraints.
    
    Args:
        tour: List of nodes in visit order
        pd_pairs: List of (pickup, delivery) tuples
        start_node: Optional start node that should be first
        
    Returns:
        True if tour is valid, False otherwise
    """
    if start_node and tour[0] != start_node:
        return False
    pos = {node: idx for idx, node in enumerate(tour)}
    for pickup, delivery in pd_pairs:
        if pickup not in pos or delivery not in pos or pos[pickup] >= pos[delivery]:
            return False
    return True


def generate_all_valid_tours(pd_pairs: List[Tuple[str, str]], start_node: Optional[str] = None):
    """Generate all valid tours respecting pickup-delivery constraints.
    
    Yields all permutations of pickup-delivery pairs where each pickup
    comes before its corresponding delivery.
    
    Args:
        pd_pairs: List of (pickup, delivery) tuples
        start_node: Optional start node to prepend/append to tours
        
    Yields:
        Valid tour sequences
    """
    all_nodes = []
    delivery_to_pickup = {d: p for p, d in pd_pairs}
    for p, d in pd_pairs:
        all_nodes.extend([p, d])
    for perm in permutations(all_nodes):
        node_positions = {node: idx for idx, node in enumerate(perm)}
        if all(node_positions[pickup] < node_positions[delivery] for delivery, pickup in delivery_to_pickup.items()):
            tour = list(perm)
            if start_node:
                tour = [start_node] + tour + [start_node]
            else:
                tour += [tour[0]]
            yield tour


def compute_optimal_brute_force(map_path: str, req_path: str, max_nodes: int = 0, start_node: Optional[str] = None) -> Tuple[List[str], float]:
    """Compute optimal tour using brute force exhaustive search.
    
    This is a convenience wrapper that imports and calls the full implementation
    from compute_optimal_brute_force.py module.
    
    Args:
        map_path: Path to map XML file
        req_path: Path to delivery requests XML file
        max_nodes: Limit number of nodes (0 = use all)
        start_node: Optional start node
        
    Returns:
        Tuple of (best_tour, best_cost)
    """
    try:
        from . import compute_optimal_brute_force as optimal_module
        return optimal_module.compute_optimal_brute_force(map_path, req_path, max_nodes, start_node)
    except ImportError:
        raise ImportError("compute_optimal_brute_force module not available")