"""Simple TSPService wrapper used by endpoints.

This service currently implements a simple, deterministic compute_tours()
method which creates `Tour` objects saved into `app.state`.
"""

from typing import List, Set, Dict, Any, Tuple, cast

import networkx as nx

from app.core import state
from app.models.schemas import Map, Tour, Delivery, DEFAULT_SPEED_KMH
from app.utils.TSP.TSP_networkx import TSP


class TSPService:
    def __init__(self) -> None:
        pass

    def _build_nx_graph_from_map(self, mp: Map) -> nx.DiGraph:
        G = nx.DiGraph()
        # add nodes
        for inter in mp.intersections:
            node_id = inter.id
            G.add_node(str(node_id))
        # add edges
        for seg in mp.road_segments:
            start_id = getattr(seg.start, "id", seg.start)
            end_id = getattr(seg.end, "id", seg.end)
            try:
                weight = float(seg.length_m)
            except Exception:
                weight = float("inf")
            if start_id in G.nodes and end_id in G.nodes:
                prev = G.get_edge_data(start_id, end_id, default=None)
                if prev is None or weight < prev.get("weight", float("inf")):
                    G.add_edge(
                        str(start_id),
                        str(end_id),
                        weight=weight
                    )
        return G

    def _build_sp_graph(self, G_map: nx.DiGraph, nodes_list: List[str]):
        sp_graph: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for src in nodes_list:
            try:
                # single_source_dijkstra returns (lengths_dict, paths_dict)
                lengths_raw, paths_raw = nx.single_source_dijkstra(
                    G_map, src, weight="weight"
                )
                # cast to expected typing to satisfy static checkers
                lengths: Dict[str, float] = cast(Dict[str, float], lengths_raw)
                paths: Dict[str, List[str]] = cast(Dict[str, List[str]], paths_raw)
            except Exception:
                lengths = {}
                paths = {}

            sp_graph[src] = {}
            for tgt in nodes_list:
                if tgt == src:
                    sp_graph[src][tgt] = {"path": [src], "cost": 0.0}
                else:
                    # ensure we use string keys
                    key = str(tgt)
                    cost_value = (
                        lengths.get(key, float("inf"))
                        if isinstance(lengths, dict)
                        else float("inf")
                    )
                    path_value = paths.get(key) if isinstance(paths, dict) else None
                    sp_graph[src][tgt] = {"path": path_value, "cost": cost_value}
        return sp_graph

    def _find_warehouse_for_courier(self, mp: Map, courier_id: str, map_nodes: Set[str]) -> str | None:
        # sourcery skip: use-next
        """Find the warehouse node for a given courier."""
        from contextlib import suppress
        
        # First try: find a delivery assigned to this courier that has a warehouse
        for dd in mp.deliveries:
            with suppress(Exception):
                dd_cid = dd.courier
                if dd_cid is None:
                    continue
                if dd_cid == courier_id:
                    warehouse_node = dd.warehouse
                    if warehouse_node is not None and warehouse_node in map_nodes:
                        return warehouse_node

        # Fallback to any warehouse present on the map deliveries
        for dd in mp.deliveries:
            if dd.warehouse is not None and dd.warehouse in map_nodes:
                return dd.warehouse
        
        return None

    def _extract_pickup_delivery_pair(self, delivery: Delivery, map_nodes: Set[str]) -> Tuple[str, str] | None:
        """Extract pickup and delivery node pair if both exist in the map."""
        pair = []
        for node_id in (delivery.pickup_addr, delivery.delivery_addr):
            if node_id not in map_nodes:
                return None
            pair.append(node_id)
        
        return (pair[0], pair[1]) if len(pair) == 2 else None

    def _group_deliveries_by_courier(self, deliveries: List[Delivery], map_nodes: Set[str]) -> Dict[str, Tour]:
        """Group deliveries by courier and create Tour objects."""
        tours_by_courier: Dict[str, Tour] = {}
        
        for delivery in deliveries:
            if delivery.courier is None:
                continue

            pair = self._extract_pickup_delivery_pair(delivery, map_nodes)
            if pair is None:
                continue

            # normalize courier id whether courier is a string or a Courrier object
            courier_id = delivery.courier

            if courier_id not in tours_by_courier:
                # store the original courier object or id in the Tour (Tour accepts either)
                tour = Tour(courier=courier_id)
                tours_by_courier[courier_id] = tour
                state.save_tour(tour)

            tours_by_courier[courier_id].add_deliveries([pair])
        
        return tours_by_courier

    def _build_nodes_set_from_tour(self, tour: Tour) -> List[str]:
        """Extract unique ordered nodes from tour deliveries."""
        nodes_set = []
        for pickup, delivery in tour.deliveries:
            if pickup not in nodes_set:
                nodes_set.append(pickup)
            if delivery not in nodes_set:
                nodes_set.append(delivery)
        return nodes_set

    def _solve_tsp_for_tour(self, tsp: TSP, tour: Tour, depot_node: str | None, nodes_set: List[str]) -> Tuple[List[str], float]:
        """Solve TSP for a given tour."""
        try:
            return tsp.solve(tour=tour, start_node=depot_node)
        except Exception:
            # Fallback: return nodes_set as trivial tour
            fallback_tour = nodes_set + ([nodes_set[0]] if nodes_set else [])
            return fallback_tour, 0.0

    def _expand_tour_route(self, tsp: TSP, compact_tour: List[str], sp_graph: Dict, compact_cost: float) -> Tuple[List[str], float]:
        """Expand compact tour to full route with all intersections."""
        try:
            return tsp.expand_tour_with_paths(compact_tour, sp_graph)
        except Exception:
            return compact_tour, compact_cost

    def _calculate_total_service_time(self, deliveries: List[Delivery], courier_id: str) -> int:
        """Calculate total service time for all deliveries of a courier."""
        total = 0
        for delivery in deliveries:
            c = delivery.courier
            cid = c if isinstance(c, str) else getattr(c, "id", str(c))
            if cid == courier_id:
                total += (delivery.pickup_service_s or 0) + (delivery.delivery_service_s or 0)
        return total

    def _set_tour_route(self, tour: Tour, full_route: List[str]) -> None:
        """Safely set the route intersections on a tour."""
        try:
            tour.route_intersections = list(full_route) if isinstance(full_route, list) else []
        except Exception:
            print("[TSPService.compute_tours] failed to set route_intersections")
            tour.route_intersections = []

    def _calculate_travel_time(self, distance_m: float) -> int:
        """Calculate travel time based on distance and default speed."""
        if DEFAULT_SPEED_KMH and DEFAULT_SPEED_KMH > 0:
            return int(round(distance_m * 3600.0 / (DEFAULT_SPEED_KMH * 1000.0)))
        return 0

    def _process_single_tour(
        self, 
        tsp: TSP, 
        courier_id: str, 
        tour: Tour, 
        G_map: nx.DiGraph,
        map_nodes: Set[str],
        mp,
        deliveries: List[Delivery]
    ) -> Tour:
        """Process a single tour: solve TSP, expand route, and set metrics."""
        # Monkeypatch TSP to use our graph
        tsp._build_networkx_map_graph = lambda xml_file_path=None: (G_map, list(G_map.nodes()))

        # Build nodes set and find depot
        nodes_set = self._build_nodes_set_from_tour(tour)
        depot_node = self._find_warehouse_for_courier(mp, courier_id, map_nodes)

        # Solve TSP
        compact_tour, compact_cost = self._solve_tsp_for_tour(tsp, tour, depot_node, nodes_set)

        # Build shortest path graph for expansion
        expansion_nodes = list(nodes_set)
        if depot_node and depot_node not in expansion_nodes:
            expansion_nodes.append(depot_node)
        sp_graph = self._build_sp_graph(G_map, expansion_nodes)

        # Expand tour to full route
        full_route, full_cost = self._expand_tour_route(tsp, compact_tour, sp_graph, compact_cost)

        # Set tour properties
        self._set_tour_route(tour, full_route)
        tour.total_distance_m = full_cost
        tour.total_travel_time_s = self._calculate_travel_time(full_cost)
        tour.total_service_time_s = self._calculate_total_service_time(deliveries, courier_id)

        state.save_tour(tour)
        return tour

    def compute_tours(self) -> List[Tour]:
        """Compute optimized delivery tours for all couriers."""
        mp = state.get_map()
        if mp is None:
            raise RuntimeError("No map loaded")

        # Setup
        deliveries = list(mp.deliveries)
        G_map = self._build_nx_graph_from_map(mp)
        map_nodes = set(G_map.nodes())
        state.clear_tours()

        # Group deliveries by courier
        tours_by_courier = self._group_deliveries_by_courier(deliveries, map_nodes)

        # Process each courier's tour
        tsp = TSP()
        return [
            self._process_single_tour(tsp, courier_id, tour, G_map, map_nodes, mp, deliveries)
            for courier_id, tour in tours_by_courier.items()
        ]
