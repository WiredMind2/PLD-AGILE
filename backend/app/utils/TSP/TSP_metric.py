"""
Metric graph construction utilities for TSP solver.

This module handles the construction of symmetric metric complete graphs
from directed shortest-path graphs.
"""

import networkx as nx
from typing import Dict, List, Set


class MetricGraphBuilder:
    """Builds symmetric metric complete graphs for TSP solving."""

    @staticmethod
    def initialize_cost_matrix(graph: Dict, nodes: List[str]) -> Dict[str, Dict[str, float]]:
        """Initialize cost matrix from graph entries.
        
        Args:
            graph: Dictionary mapping source nodes to their target nodes and costs
            nodes: List of all nodes to include in the matrix
            
        Returns:
            Dictionary C where C[u][v] is the cost from u to v.
        """
        INF = float("inf")
        C = {u: {v: (0.0 if u == v else INF) for v in nodes} for u in nodes}
        
        for u in nodes:
            for v, info in graph.get(u, {}).items():
                try:
                    c = float(info.get("cost", INF))
                except Exception:
                    c = INF
                if c < C[u].get(v, INF):
                    C[u][v] = c
        
        return C

    @staticmethod
    def build_mutual_reachability_graph(
        cost_matrix: Dict[str, Dict[str, float]], 
        nodes: List[str]
    ) -> Dict[str, Set[str]]:
        """Build adjacency list for mutually reachable nodes.
        
        Two nodes are mutually reachable if there's a finite-cost path in both directions.
        
        Args:
            cost_matrix: Cost matrix where cost_matrix[u][v] is cost from u to v
            nodes: List of all nodes
            
        Returns:
            Dictionary mapping each node to its set of mutually reachable neighbors
        """
        INF = float("inf")
        adj_mutual = {u: set() for u in nodes}
        
        for u in nodes:
            for v in nodes:
                if u != v and cost_matrix[u][v] != INF and cost_matrix[v][u] != INF:
                    adj_mutual[u].add(v)
        
        return adj_mutual

    @staticmethod
    def find_connected_component(
        start_node: str, 
        adjacency: Dict[str, Set[str]], 
        seen: Set[str]
    ) -> Set[str]:
        """Find connected component starting from start_node using DFS.
        
        Args:
            start_node: Node to start the search from
            adjacency: Adjacency list representation of the graph
            seen: Set of already visited nodes (will be modified)
            
        Returns:
            Set of nodes in the connected component
        """
        stack = [start_node]
        component = set()
        
        while stack:
            node = stack.pop()
            if node in component:
                continue
            
            component.add(node)
            seen.add(node)
            
            for neighbor in adjacency.get(node, ()):
                if neighbor not in component:
                    stack.append(neighbor)
        
        return component

    @staticmethod
    def find_all_connected_components(
        adjacency: Dict[str, Set[str]], 
        nodes: List[str]
    ) -> List[Set[str]]:
        """Find all connected components in the adjacency graph.
        
        Args:
            adjacency: Adjacency list representation of the graph
            nodes: List of all nodes to consider
            
        Returns:
            List of sets, where each set contains nodes in a connected component
        """
        seen = set()
        components = []
        
        for node in nodes:
            if node not in seen:
                component = MetricGraphBuilder.find_connected_component(
                    node, adjacency, seen
                )
                components.append(component)
        
        return components

    @staticmethod
    def build_symmetric_metric_graph(
        cost_matrix: Dict[str, Dict[str, float]], 
        nodes: List[str]
    ) -> nx.Graph:
        """Build symmetric graph by taking min(C[u][v], C[v][u]) for all node pairs.
        
        Args:
            cost_matrix: Cost matrix with directed costs
            nodes: List of nodes to include in the graph
            
        Returns:
            NetworkX Graph with symmetric edge weights
        """
        G = nx.Graph()
        
        for u in nodes:
            G.add_node(u)
        
        for i, u in enumerate(nodes):
            for v in nodes[i + 1:]:
                weight = float(min(cost_matrix[u][v], cost_matrix[v][u]))
                G.add_edge(u, v, weight=weight)
        
        return G

    @staticmethod
    def build_metric_complete_graph(graph: Dict) -> nx.Graph:
        """Build a symmetric metric complete graph from a directed sp_graph.

        Steps:
        - Initialize directed cost matrix from `graph` entries.
        - Build mutual reachability adjacency (nodes with finite costs both ways).
        - Select the largest mutually-reachable connected component.
        - Symmetrize distances by taking min(cost(u,v), cost(v,u)) and return a NetworkX Graph.

        Unlike earlier code, this function will not raise on missing pairs; instead it
        restricts the metric to the largest mutually-reachable component so callers
        may 'ignore' problematic nodes that prevent a complete metric.
        
        Args:
            graph: Dictionary with shortest path information between nodes
            
        Returns:
            NetworkX Graph representing the symmetric metric
        """
        nodes = list(graph.keys())
        if not nodes:
            return nx.Graph()

        # Initialize cost matrix from graph
        cost_matrix = MetricGraphBuilder.initialize_cost_matrix(graph, nodes)

        # Build adjacency for mutual reachability
        adj_mutual = MetricGraphBuilder.build_mutual_reachability_graph(
            cost_matrix, nodes
        )

        # Find all connected components
        components = MetricGraphBuilder.find_all_connected_components(
            adj_mutual, nodes
        )
        if not components:
            return nx.Graph()

        # Select the largest component
        largest_component = max(components, key=len)
        if len(largest_component) < 2:
            return nx.Graph()

        # Build symmetric metric graph for the largest component
        chosen_nodes = list(largest_component)
        return MetricGraphBuilder.build_symmetric_metric_graph(
            cost_matrix, chosen_nodes
        )
