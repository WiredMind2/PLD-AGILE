"""
Main TSP solver orchestrating all components.

This module ties together all the TSP components:
- Base graph building (TSP_base)
- Metric graph construction (TSP_metric)
- Initial tour heuristics (TSP_heuristics)
- Local search optimization (TSP_local_search)
"""

from typing import Optional, List, Dict, cast, Tuple

import networkx as nx

from app.models.schemas import Tour
from .TSP_base import TSPBase
from .TSP_metric import MetricGraphBuilder
from .TSP_heuristics import TourHeuristics
from .TSP_local_search import LocalSearchOptimizer


class TSP(TSPBase):
    """Main TSP solver with adaptive strategies based on problem size."""

    def _build_metric_complete_graph(self, graph):
        """Build a symmetric metric complete graph (backwards compatibility wrapper).
        
        This method delegates to MetricGraphBuilder for backwards compatibility
        with existing tests and code.
        
        Args:
            graph: Dictionary with shortest path information between nodes
            
        Returns:
            NetworkX Graph representing the symmetric metric
        """
        return MetricGraphBuilder.build_metric_complete_graph(graph)

    def solve(self, tour: Tour, start_node: Optional[str] = None):
        """Adaptive TSP solver that switches strategies based on problem size.
        
        Problem Size Strategy:
        - Small (≤4 nodes): Fast greedy with light 2-opt
        - Medium (5-12 nodes): Multi-heuristic with moderate local search
        - Large (>12 nodes): Best single heuristic with focused 2-opt
        
        This implementation uses:
        1. Multiple initial solution strategies (greedy, savings, nearest neighbor)
        2. Enhanced local search with 2-opt, Or-Opt, and node insertion moves
        3. Precedence constraints (pickup before delivery)
        4. Adaptive iteration budgets based on problem complexity
        
        Args:
            tour: Tour object containing pickup-delivery pairs
            start_node: Optional depot/start node ID. If provided, the tour will
                       start and end at this node.
                       
        Returns:
            Tuple of (tour_sequence, tour_cost)
        """
        # Extract pickup-delivery pairs from the provided Tour object
        pd_pairs = list(tour.deliveries)
        if not pd_pairs:
            return [], 0.0
        
        # Determine problem size for adaptive strategy selection
        num_nodes = len(pd_pairs) * 2  # Each pair has pickup + delivery
        
        # Adaptive parameters based on problem size
        params = self._get_strategy_parameters(num_nodes)
        
        # Build the set/list of all involved nodes (pickups and deliveries)
        nodes_list = self._extract_nodes_from_pairs(pd_pairs)
        
        # Build map graph and validate nodes
        G_map, nodes_list, start_node = self._prepare_map_graph(nodes_list, start_node)
        
        # Compute pairwise shortest-paths among nodes of interest
        sp_graph = self._compute_shortest_paths(G_map, nodes_list)
        
        # Build symmetric metric among the requested nodes
        G = MetricGraphBuilder.build_metric_complete_graph(sp_graph)
        if G.number_of_nodes() == 0:
            return [], 0.0
        
        # Filter pickup-delivery pairs to those fully present in the metric graph
        pd_pairs = [(p, d) for (p, d) in pd_pairs if p in G.nodes() and d in G.nodes()]
        if not pd_pairs:
            return [], 0.0
        
        # Build helper functions and data structures
        pickups = [p for p, _ in pd_pairs]
        deliveries = [d for _, d in pd_pairs]
        delivery_map = {d: p for p, d in pd_pairs if p in nodes_list and d in nodes_list}
        
        tour_cost_fn = self._make_tour_cost_function(G)
        is_valid_tour_fn = self._make_validation_function(delivery_map)
        
        # Generate initial solutions using heuristics
        tour_seq, total = self._generate_initial_tour(
            G, pd_pairs, pickups, deliveries, delivery_map,
            tour_cost_fn, is_valid_tour_fn, start_node, params
        )
        
        if not tour_seq:
            return [], 0.0
        
        # Apply local search optimization
        final_tour = self._optimize_tour(
            tour_seq, total, tour_cost_fn, is_valid_tour_fn, params
        )
        
        return final_tour

    def _get_strategy_parameters(self, num_nodes: int) -> dict:
        """Determine optimization parameters based on problem size."""
        if num_nodes <= 4:
            return {
                "strategy": "fast",
                "num_heuristics": 1,
                "num_restarts": 1,
                "iterations_per_restart": 200,
                "use_simulated_annealing": False,
                "use_or_opt": False
            }
        elif num_nodes <= 12:
            return {
                "strategy": "balanced",
                "num_heuristics": 2,
                "num_restarts": 2,
                "iterations_per_restart": 800,
                "use_simulated_annealing": True,
                "use_or_opt": True
            }
        else:
            return {
                "strategy": "focused",
                "num_heuristics": 1,
                "num_restarts": 1,
                "iterations_per_restart": 500,
                "use_simulated_annealing": False,
                "use_or_opt": False
            }

    def _extract_nodes_from_pairs(self, pd_pairs: List[Tuple[str, str]]) -> List[str]:
        """Extract unique nodes from pickup-delivery pairs."""
        nodes_list = []
        for p, d in pd_pairs:
            if p not in nodes_list:
                nodes_list.append(p)
            if d not in nodes_list:
                nodes_list.append(d)
        return nodes_list

    def _prepare_map_graph(self, nodes_list: List[str], start_node: Optional[str]):
        """Build map graph and validate nodes."""
        G_map, _ = self._build_networkx_map_graph()
        
        # Validate nodes
        missing = [n for n in nodes_list if n not in G_map.nodes()]
        if missing:
            print(
                f"Warning: {len(missing)} requested TSP nodes not present in map "
                f"(examples: {missing[:5]})"
            )
            nodes_list = [n for n in nodes_list if n in G_map.nodes()]
        
        # Validate and add start_node
        if start_node is not None:
            start_node = str(start_node)
            if start_node not in G_map.nodes():
                print(f"Warning: start_node {start_node} not in map, ignoring")
                start_node = None
            elif start_node not in nodes_list:
                nodes_list.append(start_node)
        
        return G_map, nodes_list, start_node

    def _compute_shortest_paths(self, G_map: nx.DiGraph, nodes_list: List[str]) -> Dict:
        """Compute pairwise shortest paths among nodes of interest."""
        sp_graph = {}
        for src in nodes_list:
            try:
                lengths_raw, paths_raw = nx.single_source_dijkstra(
                    G_map, src, weight="weight"
                )
                lengths = cast(Dict[str, float], lengths_raw) if isinstance(lengths_raw, dict) else {}
                paths = cast(Dict[str, List[str]], paths_raw) if isinstance(paths_raw, dict) else {}
            except Exception:
                lengths = {}
                paths = {}
            sp_graph[src] = {}
            for tgt in nodes_list:
                sp_graph[src][tgt] = {
                    "path": [src] if src == tgt else paths.get(tgt),
                    "cost": 0.0 if src == tgt else lengths.get(tgt, float("inf")),
                }
        return sp_graph

    def _make_tour_cost_function(self, G: nx.Graph):
        """Create a function to compute tour cost on the metric graph."""
        def tour_cost(seq: List[str]) -> float:
            if not seq or len(seq) < 2:
                return 0.0
            s = 0.0
            for i in range(len(seq) - 1):
                u, v = seq[i], seq[i + 1]
                s += G[u][v]["weight"]
            return s
        return tour_cost

    def _make_validation_function(self, delivery_map: Dict[str, str]):
        """Create a function to check if a tour respects pickup-before-delivery precedence."""
        def is_valid_tour(seq: List[str]) -> bool:
            for d, p in delivery_map.items():
                try:
                    idx_p = seq.index(p)
                    idx_d = seq.index(d)
                    if idx_p >= idx_d:
                        return False
                except ValueError:
                    return False
            return True
        return is_valid_tour

    def _generate_initial_tour(
        self, G, pd_pairs, pickups, deliveries, delivery_map,
        tour_cost_fn, is_valid_tour_fn, start_node, params
    ):
        """Generate initial tour using one or more heuristics."""
        candidate_tours = []
        
        # Always use Nearest Neighbor (fast and reliable)
        nn_tour, nn_cost = TourHeuristics.build_nearest_neighbor_tour(
            G, pickups, deliveries, delivery_map,
            tour_cost_fn, is_valid_tour_fn, start_node
        )
        if nn_tour:
            candidate_tours.append((nn_tour, nn_cost))
        
        # Add more heuristics for medium problems
        if params["num_heuristics"] >= 2:
            ins_tour, ins_cost = TourHeuristics.build_insertion_tour(
                G, pd_pairs, tour_cost_fn, is_valid_tour_fn, start_node
            )
            core = ins_tour[:-1] if ins_tour and ins_tour[0] == ins_tour[-1] else ins_tour
            if ins_tour and is_valid_tour_fn(core):
                candidate_tours.append((ins_tour, ins_cost))
        
        if params["num_heuristics"] >= 3:
            sv_tour, sv_cost = TourHeuristics.build_savings_tour(
                G, pd_pairs, tour_cost_fn, is_valid_tour_fn, start_node
            )
            core = sv_tour[:-1] if sv_tour and sv_tour[0] == sv_tour[-1] else sv_tour
            if sv_tour and is_valid_tour_fn(core):
                candidate_tours.append((sv_tour, sv_cost))
        
        if not candidate_tours:
            return [], 0.0
        
        # Pick best initial tour
        candidate_tours.sort(key=lambda x: x[1])
        return candidate_tours[0]

    def _optimize_tour(self, tour_seq, total, tour_cost_fn, is_valid_tour_fn, params):
        """Apply local search optimization to improve the tour."""
        closed = len(tour_seq) >= 2 and tour_seq[0] == tour_seq[-1]
        core = tour_seq[:-1] if closed else list(tour_seq)
        
        # Handle small tours (less than 3 nodes can't be improved much)
        if len(core) < 3:
            if closed and core and core[0] != core[-1]:
                core.append(core[0])
            return core, tour_cost_fn(core) if core else 0.0
        
        # Apply multi-start local search
        best_core, best_cost = LocalSearchOptimizer.multi_start_local_search(
            core, total, tour_cost_fn, is_valid_tour_fn, closed,
            params["num_restarts"], params["iterations_per_restart"],
            params["use_simulated_annealing"], params["use_or_opt"],
            params["strategy"]
        )
        
        # Re-close tour if needed
        if closed and best_core:
            best_core.append(best_core[0])
        
        return best_core, best_cost
