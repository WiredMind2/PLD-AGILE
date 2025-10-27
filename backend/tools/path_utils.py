"""Path utility functions for TSP path comparison tool."""

from __future__ import annotations

import networkx as nx
from typing import List, Dict, Tuple, cast, Optional


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