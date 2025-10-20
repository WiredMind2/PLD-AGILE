"""Simple TSPService wrapper used by endpoints.

This service currently implements a simple, deterministic compute_tours()
method which assigns deliveries to couriers in a round-robin fashion and
creates `Tour` objects saved into `app.state`. This keeps endpoints
functional while leaving the advanced solver in `app.utils.TSP` intact.
"""

from typing import List, Set, Dict, Any, Tuple, cast

import networkx as nx

from app.core import state
from app.models.schemas import Tour, Delivery, Courrier, DEFAULT_SPEED_KMH
from app.utils.TSP.TSP_networkx import TSP


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
            start_id = str(getattr(seg.start, "id", seg.start))
            end_id = str(getattr(seg.end, "id", seg.end))
            try:
                weight = float(seg.length_m)
            except Exception:
                weight = float("inf")
            if start_id in G.nodes and end_id in G.nodes:
                prev = G.get_edge_data(start_id, end_id, default=None)
                if prev is None or weight < prev.get("weight", float("inf")):
                    G.add_edge(
                        start_id,
                        end_id,
                        weight=weight,
                        street_name=getattr(seg, "street_name", ""),
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
                    sp_graph[src][tgt] = {
                        "path": paths.get(key) if isinstance(paths, dict) else None,
                        "cost": (
                            lengths.get(key, float("inf"))
                            if isinstance(lengths, dict)
                            else float("inf")
                        ),
                    }
        return sp_graph

    def compute_tours(self) -> List[Tour]:
        mp = state.get_map()
        if mp is None:
            raise RuntimeError("No map loaded")

        deliveries: List[Delivery] = list(mp.deliveries)
        couriers: List[Courrier] = list(mp.couriers)

        # If no couriers are registered but deliveries include a warehouse
        # we create a default courier located at the first warehouse found.
        # This makes the `compute_tours` endpoint usable with map + requests
        # even when the XML map did not include explicit courier entries.
        if not couriers:
            first_wh = None
            for d in deliveries:
                if getattr(d, "warehouse", None) is not None:
                    first_wh = d.warehouse
                    break
            if first_wh is not None:
                try:
                    # build a simple Courrier object and add it to map
                    default_courier = Courrier(
                        id="C1", current_location=first_wh, name="C1"
                    )
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

        # clear previous tours
        state.clear_tours()

        tsp = TSP()
        tours_result: Dict[str, Tour] = {}  # Use courier ID as key instead of Courrier object

        for d in deliveries:
            if d.courier is None:
                # ignore unassigned deliveries
                continue

            # collect nodes (pickup + delivery) for this courier
            pickup_delivery_pairs: List[Tuple[str, str]] = []

            pair: List[str] = []
            for addr in (d.pickup_addr, d.delivery_addr):
                node_id = str(getattr(addr, "id", addr))
                if node_id not in map_nodes: break

                pair.append(node_id)

            if len(pair) == 2:
                pickup_delivery_pairs.append((pair[0], pair[1]))

            courier_id = str(d.courier.id)
            if courier_id not in tours_result:
                t = Tour(courier=d.courier)
                tours_result[courier_id] = t
                state.save_tour(t)

            tours_result[courier_id].add_deliveries(pickup_delivery_pairs)


        results_list: List[Tour] = []
        for courier_id, tour in list(tours_result.items()):
            # collect assigned deliveries for this courier
            c = tour.courier

            # monkeypatch _build_networkx_map_graph to return our G_map
            tsp._build_networkx_map_graph = lambda xml_file_path=None: (
                G_map,
                list(G_map.nodes()),
            )

            # Build nodes_set (unique pickups+deliveries in order) from Tour
            nodes_set: List[str] = []
            for p, d in tour.deliveries:
                if p not in nodes_set:
                    nodes_set.append(p)
                if d not in nodes_set:
                    nodes_set.append(d)

            # Get the depot node (courier start location) to pass to TSP solver
            depot_node = None
            try:
                depot_node = str(c.current_location.id)
                if depot_node not in map_nodes:
                    depot_node = None
            except Exception:
                depot_node = None

            # run solver on the Tour object with the depot as start_node
            try:
                compact_tour, compact_cost = tsp.solve(tour=tour, start_node=depot_node)
            except Exception:
                # fallback: return nodes_set as trivial tour
                compact_tour, compact_cost = (
                    nodes_set + ([nodes_set[0]] if nodes_set else []),
                    0.0,
                )

            # build sp_graph for expansion - include depot_node if present
            expansion_nodes = list(nodes_set)
            if depot_node and depot_node not in expansion_nodes:
                expansion_nodes.append(depot_node)
            
            sp_graph = self._build_sp_graph(G_map, expansion_nodes)
            try:
                full_route, full_cost = tsp.expand_tour_with_paths(compact_tour, sp_graph)
            except Exception:
                full_route, full_cost = compact_tour, compact_cost

            # Note: The tour should already start and end at depot_node if it was provided
            # No need for additional rotation logic since solve() handles this

            # attach expanded intersection route and totals to the existing Tour
            try:
                tour.route_intersections = list(full_route) if isinstance(full_route, list) else []
            except Exception:
                tour.route_intersections = []

            tour.total_distance_m = float(full_cost)
            if DEFAULT_SPEED_KMH and DEFAULT_SPEED_KMH > 0:
                tour.total_travel_time_s = int(
                    round(full_cost * 3600.0 / (DEFAULT_SPEED_KMH * 1000.0))
                )
            else:
                tour.total_travel_time_s = 0

            state.save_tour(tour)
            results_list.append(tour)

        return results_list
