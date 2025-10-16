"""Simple TSPService wrapper used by endpoints.

This service currently implements a simple, deterministic compute_tours()
method which assigns deliveries to couriers in a round-robin fashion and
creates `Tour` objects saved into `app.state`. This keeps endpoints
functional while leaving the advanced solver in `app.utils.TSP` intact.
"""
from typing import List, Set, Dict, Any, cast

import networkx as nx

from app.core import state
from app.models.schemas import Tour, Delivery, Courrier, DEFAULT_SPEED_KMH
from app.utils.TSP.TSP_ortools import TSP


class TSPService:
    def __init__(self) -> None:
        pass

    def _build_nx_graph_from_map(self, mp) -> nx.DiGraph:
        G = nx.DiGraph()
        # add nodes
        for inter in mp.intersections:
            G.add_node(str(inter.id))
        # add edges
        for seg in mp.road_segments:
            start_id = str(getattr(seg.start, 'id', seg.start))
            end_id = str(getattr(seg.end, 'id', seg.end))
            try:
                weight = float(seg.length_m)
            except Exception:
                weight = float('inf')
            if start_id in G.nodes and end_id in G.nodes:
                prev = G.get_edge_data(start_id, end_id, default=None)
                if prev is None or weight < prev.get('weight', float('inf')):
                    G.add_edge(start_id, end_id, weight=weight, street_name=getattr(seg, 'street_name', ''))
        return G

    def _build_sp_graph(self, G_map: nx.DiGraph, nodes_list: List[str]):
        sp_graph: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for src in nodes_list:
            try:
                # single_source_dijkstra returns (lengths_dict, paths_dict)
                lengths_raw, paths_raw = nx.single_source_dijkstra(G_map, src, weight='weight')
                # cast to expected typing to satisfy static checkers
                lengths: Dict[str, float] = cast(Dict[str, float], lengths_raw)
                paths: Dict[str, List[str]] = cast(Dict[str, List[str]], paths_raw)
            except Exception:
                lengths = {}
                paths = {}

            sp_graph[src] = {}
            for tgt in nodes_list:
                if tgt == src:
                    sp_graph[src][tgt] = {'path': [src], 'cost': 0.0}
                else:
                    # ensure we use string keys
                    key = str(tgt)
                    sp_graph[src][tgt] = {
                        'path': paths.get(key) if isinstance(paths, dict) else None,
                        'cost': lengths.get(key, float('inf')) if isinstance(lengths, dict) else float('inf')
                    }
        return sp_graph

    def compute_tours(self) -> List[Tour]:
        mp = state.get_map()
        if mp is None:
            raise RuntimeError('No map loaded')

        deliveries: List[Delivery] = list(mp.deliveries)
        couriers: List[Courrier] = list(mp.couriers)

        # If no couriers are registered but deliveries include a warehouse
        # we create a default courier located at the first warehouse found.
        # This makes the `compute_tours` endpoint usable with map + requests
        # even when the XML map did not include explicit courier entries.
        if not couriers:
            first_wh = None
            for d in deliveries:
                if getattr(d, 'warehouse', None) is not None:
                    first_wh = d.warehouse
                    break
            if first_wh is not None:
                try:
                    # build a simple Courrier object and add it to map
                    default_courier = Courrier(id='C1', current_location=first_wh, name='C1', phone_number='')
                    try:
                        mp.add_courier(default_courier)
                    except Exception:
                        # fallback: if Map doesn't expose add_courier, mutate list directly
                        try:
                            mp.couriers.append(default_courier)
                        except Exception:
                            pass
                    couriers = [default_courier]
                except Exception:
                    # if anything goes wrong just return empty result
                    return []
            else:
                return []

        # Graph for shortest paths
        G_map = self._build_nx_graph_from_map(mp)

        # helper: ensure a node exists in map
        map_nodes: Set[str] = set(G_map.nodes())

        # prepare assignments: if multiple couriers, round-robin assign deliveries
        assignments = {c.id: [] for c in couriers}
        for idx, d in enumerate(deliveries):
            c = couriers[idx % len(couriers)]
            assignments[c.id].append(d)

        # clear previous tours
        state.clear_tours()

        tsp = TSP()
        tours_result: List[Tour] = []

        for c in couriers:
            assigned = assignments.get(c.id, [])
            # collect nodes (pickup + delivery) for this courier
            nodes_set = []
            # include courier current location (warehouse) as depot if available
            try:
                depot_node = str(getattr(c.current_location, 'id', None)) if getattr(c, 'current_location', None) is not None else None
            except Exception:
                depot_node = None
            if depot_node and depot_node not in nodes_set:
                nodes_set.append(depot_node)
            for d in assigned:
                for addr in (d.pickup_addr, d.delivery_addr):
                    node_id = str(getattr(addr, 'id', addr))
                    if node_id in map_nodes and node_id not in nodes_set:
                        nodes_set.append(node_id)

            if not nodes_set:
                # create empty tour for courier
                t = Tour(courier=c)
                tours_result.append(t)
                state.save_tour(t)
                continue

            # monkeypatch _build_networkx_map_graph to return our G_map
            tsp._build_networkx_map_graph = lambda xml_file_path=None: (G_map, list(G_map.nodes()))

            # run solver on nodes_set
            try:
                # prefer depot as start: call solve on nodes_set and then rotate resulting full route
                compact_tour, compact_cost = tsp.solve(nodes=nodes_set)
            except Exception:
                # fallback: no tour computed
                compact_tour, compact_cost = nodes_set + ([nodes_set[0]] if nodes_set else []), 0.0

            # build sp_graph for expansion
            sp_graph = self._build_sp_graph(G_map, nodes_set)
            try:
                full_route, full_cost = tsp.expand_tour_with_paths(compact_tour, sp_graph)
            except Exception:
                full_route, full_cost = compact_tour, compact_cost

            # Ensure tour starts (and ends) at depot_node when available
            if depot_node and isinstance(full_route, list) and depot_node in full_route:
                # rotate so first element is depot_node
                try:
                    idx = full_route.index(depot_node)
                    # rotate so tour starts at depot_node; do not force it to end at depot
                    rotated = full_route[idx:] + full_route[:idx]
                    full_route = rotated
                except Exception:
                    pass

            # create Tour and assign deliveries to courier
            tour = Tour(courier=c)
            for d in assigned:
                d.courier = c
                tour.add_delivery(d)

            # attach expanded intersection route to the Tour so frontend can draw it
            try:
                tour.route_intersections = list(full_route) if isinstance(full_route, list) else []
            except Exception:
                tour.route_intersections = []

            tour.total_distance_m = float(full_cost)
            # compute travel time in seconds from distance using DEFAULT_SPEED_KMH
            if DEFAULT_SPEED_KMH and DEFAULT_SPEED_KMH > 0:
                tour.total_travel_time_s = int(round(full_cost * 3600.0 / (DEFAULT_SPEED_KMH * 1000.0)))
            else:
                tour.total_travel_time_s = 0

            state.save_tour(tour)
            tours_result.append(tour)

        return tours_result
