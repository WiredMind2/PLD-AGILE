"""
Base TSP class with graph building and utility methods.

This module contains the core TSP class with methods for:
- Building NetworkX graphs from XML map data
- Computing shortest paths
- Expanding compact tours to full routes
"""

import os
import sys
from typing import Dict, List, cast

import networkx as nx


class TSPBase:
    """Base class for TSP solver with graph construction utilities."""

    def __init__(self):
        """Initialize TSP solver with caching for map graph."""
        # Cache for the parsed/constructed map graph to avoid reparsing XML
        # on repeated calls to `solve()`.
        self.graph = None
        self._all_nodes = None

    def _build_networkx_map_graph(self, xml_file_path: str | None = None):
        """Parse the XML map and return a directed NetworkX graph and the node list.

        The returned graph uses edge attribute 'weight' with the segment length (meters).
        
        Args:
            xml_file_path: Optional path to XML file. If None, uses cached graph or default path.
            
        Returns:
            Tuple of (NetworkX DiGraph, list of node IDs)
        """
        # If no explicit xml path is provided and we have a cached graph,
        # reuse it. If an xml path is provided, always rebuild from that file.
        if xml_file_path is None and self.graph is not None:
            return self.graph, (
                list(self._all_nodes)
                if self._all_nodes is not None
                else list(self.graph.nodes())
            )

        if xml_file_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(current_dir, "..", "..", "..", "..")
            xml_file_path = os.path.join(
                project_root, "fichiersXMLPickupDelivery", "petitPlan.xml"
            )

        with open(xml_file_path, "r", encoding="utf-8") as f:
            xml_text = f.read()

        # lazy import to avoid circular imports (app.services may import this module)
        try:
            from app.services.XMLParser import XMLParser  # type: ignore
        except Exception:
            # fallback for direct script execution / tests
            sys.path.insert(
                0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            )
            from services.XMLParser import XMLParser  # type: ignore

        map_data = XMLParser.parse_map(xml_text)

        G = nx.DiGraph()
        # Add nodes (use intersection ids as strings). Accept either
        # Intersection objects or raw id strings in the parsed data.
        for inter in map_data.intersections:
            node_id = getattr(inter, "id", inter)
            G.add_node(str(node_id))

        # Add directed edges with weight = length_m. Accept both
        # RoadSegment.start/end as Intersection objects or plain ids.
        for seg in map_data.road_segments:
            start_id = getattr(seg.start, "id", seg.start)
            end_id = getattr(seg.end, "id", seg.end)
            try:
                weight = float(seg.length_m)
            except Exception:
                weight = float("inf")
            # If node ids are present, add the edge
            if start_id in G.nodes and end_id in G.nodes:
                # If multiple edges exist, keep the smallest weight
                prev = G.get_edge_data(start_id, end_id, default=None)
                if prev is None or weight < prev.get("weight", float("inf")):
                    G.add_edge(
                        str(start_id), str(end_id), weight=weight, street_name=seg.street_name
                    )

        # Cache the built graph for subsequent calls when no explicit
        # xml_file_path is provided.
        self.graph = G
        self._all_nodes = list(G.nodes())
        return G, list(self._all_nodes)

    def expand_tour_with_paths(self, tour: List[str], sp_graph: Dict):
        """Expand a compact tour (list of location nodes) into the full node-level route.
        
        Concatenates the shortest-paths between consecutive tour nodes.

        Args:
            tour: List of node IDs in tour order
            sp_graph: Dictionary with shortest path information
            
        Returns:
            Tuple of (full_route_list, total_cost)
            
        Raises:
            ValueError: If any leg is unreachable
        """
        if not tour or len(tour) < 2:
            return [], 0.0

        full_route = []
        total = 0.0
        for i in range(len(tour) - 1):
            u, v = tour[i], tour[i + 1]
            info = sp_graph.get(u, {}).get(v)
            if info is None or info.get("path") is None:
                raise ValueError(f"No shortest-path from {u} to {v}")
            path = info["path"]
            cost = info.get("cost", float("inf"))
            if full_route and full_route[-1] == path[0]:
                full_route.extend(path[1:])
            else:
                full_route.extend(path)
            total += cost
        return full_route, total
