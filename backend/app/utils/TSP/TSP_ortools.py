import heapq
import os
import sys
from typing import Dict, List, Optional, Tuple, Any
import networkx as nx

try:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
except Exception:
    # If ortools isn't installed the import will fail; leave the module
    # importable but functions will raise at runtime when used.
    pywrapcp = None  # type: ignore
    routing_enums_pb2 = None  # type: ignore

try:
    # prefer using existing TSP map builder if available
    from app.utils.TSP.TSP_networkx import TSP as NX_TSP
except Exception:
    # fallback for direct script execution / tests
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from utils.TSP.TSP_networkx import TSP as NX_TSP  # type: ignore


class ORToolsTSP:
    """TSP solver using OR-Tools Routing with pickup-delivery support.

    Workflow:
    - Build/obtain the NetworkX map graph via NX_TSP._build_networkx_map_graph().
    - Compute pairwise shortest-path costs among requested nodes using an
      early-stop Dijkstra (stops when all targets have been settled).
    - Restrict to the largest mutually-reachable set of nodes (both directions finite).
    - Build OR-Tools routing model (one vehicle) with AddPickupAndDelivery
      constraints and solve to get compact tour.
    - Optionally expand compact tour to full node-level route using NetworkX shortest paths.
    """

    def __init__(self):
        self._nx_tsp = NX_TSP()
        self._G_map = None

    def _ensure_map(self, xml_file_path: Optional[str] = None):
        if self._G_map is None:
            G_map, all_nodes = self._nx_tsp._build_networkx_map_graph(xml_file_path)
            self._G_map = G_map
        return self._G_map

    def _early_stop_dijkstra(self, G, src: str, targets: set) -> Tuple[Dict[str, float], Dict[str, List[str]]]:
        # Dijkstra that stops when all targets are settled
        INF = float('inf')
        dist: Dict[str, float] = {}
        prev: Dict[str, Optional[str]] = {}
        paths: Dict[str, List[str]] = {}

        heap = [(0.0, src)]
        seen = set()

        # track remaining targets (exclude source)
        remaining = set(targets)
        if src in remaining:
            remaining.remove(src)

        while heap and remaining:
            d, u = heapq.heappop(heap)
            if u in seen:
                continue
            seen.add(u)
            dist[u] = d
            # reconstruct path lazily
            # when u is requested, build path by walking prev
            if u == src:
                paths[u] = [src]
            else:
                # build path from src to u
                seq = []
                cur = u
                while cur is not None:
                    seq.append(cur)
                    cur = prev.get(cur)
                seq.reverse()
                paths[u] = seq

            if u in remaining:
                remaining.remove(u)

            for v, ed in G[u].items():
                w = ed.get('weight', INF)
                nd = d + (w if w is not None else INF)
                if v not in seen:
                    # best-effort check: push candidate
                    heapq.heappush(heap, (nd, v))
                    # set predecessor when pushing a better tentative distance
                    if v not in prev or nd < dist.get(v, float('inf')):
                        prev[v] = u

        # fill distances/paths for nodes seen; others left absent
        return dist, paths

    def _compute_pairwise_costs(self, nodes: List[str]) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, List[str]]]]:
        G = self._ensure_map()
        sp_costs: Dict[str, Dict[str, float]] = {}
        sp_paths: Dict[str, Dict[str, List[str]]] = {}
        node_set = set(nodes)
        for src in nodes:
            lengths, paths = self._early_stop_dijkstra(G, src, node_set)
            sp_costs[src] = {t: float(lengths.get(t, float('inf'))) for t in nodes}
            # allow None values in sp_paths for unreachable entries
            sp_paths[src] = {t: (paths.get(t) if paths.get(t) is not None else None) for t in nodes}  # type: ignore[var-annotated]
        return sp_costs, sp_paths

    def _largest_mutual_component(self, nodes: List[str], costs: Dict[str, Dict[str, float]]) -> List[str]:
        INF = float('inf')
        adj_mutual = {u: set() for u in nodes}
        for u in nodes:
            for v in nodes:
                if u == v:
                    continue
                if costs[u].get(v, INF) != INF and costs[v].get(u, INF) != INF:
                    adj_mutual[u].add(v)

        seen = set()
        components = []
        for u in nodes:
            if u in seen:
                continue
            stack = [u]
            comp = set()
            while stack:
                x = stack.pop()
                if x in comp:
                    continue
                comp.add(x)
                seen.add(x)
                for nb in adj_mutual.get(x, ()):  # neighbors
                    if nb not in comp:
                        stack.append(nb)
            components.append(comp)

        if not components:
            return []
        components.sort(key=len, reverse=True)
        largest = components[0]
        if len(largest) < 2:
            return []
        return list(largest)

    def solve(self, nodes: Optional[List[str]] = None, pickup_delivery_pairs: Optional[List[Tuple[str, str]]] = None, xml_file_path: Optional[str] = None, time_limit_s: int = 10, search_params: Optional[Dict[str, Any]] = None) -> Tuple[List[str], float, Dict[str, Dict[str, List[str]]]]:
        """Solve TSP with pickup-delivery constraints using OR-Tools.

        Returns (compact_tour, total_cost, sp_paths). compact_tour is a closed
        tour (first==last). sp_paths is the pairwise path dict (may be incomplete
        for unreachable pairs).
        """
        if pywrapcp is None:
            raise RuntimeError("ortools is not installed. Please install ortools to use ORToolsTSP.")

        G = self._ensure_map(xml_file_path)

        all_nodes = list(G.nodes())
        nodes_list = list(nodes) if nodes is not None else all_nodes

        # Validate node presence
        nodes_list = [n for n in nodes_list if n in G.nodes()]

        # Ensure PD pairs' nodes are included
        pdp = pickup_delivery_pairs or []
        for p, d in pdp:
            if p in G.nodes() and p not in nodes_list:
                nodes_list.append(p)
            if d in G.nodes() and d not in nodes_list:
                nodes_list.append(d)

        # compute pairwise costs (early-stop dijkstra per source)
        costs, paths = self._compute_pairwise_costs(nodes_list)

        # restrict to largest mutual component (both-way finite costs)
        chosen = self._largest_mutual_component(nodes_list, costs)
        if not chosen:
            raise ValueError("No mutually reachable set of nodes found for TSP")

        # filter nodes and related pd pairs
        nodes_list = chosen
        node_index = {n: i for i, n in enumerate(nodes_list)}
        pd_pairs_idx = []
        for p, d in pdp:
            if p in node_index and d in node_index:
                pd_pairs_idx.append((node_index[p], node_index[d]))

        # Build cost matrix (integers for OR-Tools)
        # choose INF dynamically from max finite cost to avoid huge disparities
        finite_costs = [costs[u].get(v) for u in nodes_list for v in nodes_list if costs[u].get(v, float('inf')) != float('inf')]
        finite_costs = [f for f in finite_costs if f is not None]
        max_cost = max(finite_costs) if finite_costs else 1.0
        INF = int(max_cost * 1000) + 1000000
        matrix: List[List[int]] = []
        for u in nodes_list:
            row: List[int] = []
            for v in nodes_list:
                c = costs[u].get(v, float('inf'))
                if c == float('inf'):
                    row.append(INF)
                else:
                    # scale/round to int
                    row.append(int(round(c)))
            matrix.append(row)

        # OR-Tools setup
        manager = pywrapcp.RoutingIndexManager(len(matrix), 1, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return matrix[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Add pickup-delivery constraints
        for p_idx, d_idx in pd_pairs_idx:
            pick_index = manager.NodeToIndex(p_idx)
            del_index = manager.NodeToIndex(d_idx)
            routing.AddPickupAndDelivery(pick_index, del_index)
            routing.solver().Add(routing.VehicleVar(pick_index) == routing.VehicleVar(del_index))

        # Search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        # Apply optional search_params override (first_solution, local_search, log_search)
        sp = search_params or {}
        if routing_enums_pb2 is not None:
            # first solution strategy
            fs = sp.get('first_solution', 'PATH_CHEAPEST_ARC')
            try:
                search_parameters.first_solution_strategy = getattr(routing_enums_pb2.FirstSolutionStrategy, fs)
            except Exception:
                try:
                    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
                except Exception:
                    pass
            # local search metaheuristic (optional)
            ls = sp.get('local_search')
            if ls:
                try:
                    search_parameters.local_search_metaheuristic = getattr(routing_enums_pb2.LocalSearchMetaheuristic, ls)
                except Exception:
                    # ignore if not available
                    pass
            # enable logging of the search if requested
            if sp.get('log_search', False):
                try:
                    search_parameters.log_search = True
                except Exception:
                    pass
        # time limit: try both fields for compatibility across versions
        try:
            search_parameters.time_limit.seconds = time_limit_s
        except Exception:
            try:
                search_parameters.max_time_seconds = float(time_limit_s)
            except Exception:
                pass

        solution = routing.SolveWithParameters(search_parameters)
        if solution is None:
            # Retry with a simpler strategy and larger time limit to probe feasibility
            logger = None
            try:
                import logging
                logger = logging.getLogger(__name__)
            except Exception:
                logger = None
            if logger:
                logger.warning('Initial OR-Tools solve returned no solution; retrying with simpler params')
            fallback_params = pywrapcp.DefaultRoutingSearchParameters()
            try:
                if routing_enums_pb2 is not None:
                    fallback_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            except Exception:
                pass
            try:
                # try a larger time limit for fallback
                fallback_params.time_limit.seconds = max(30, int(time_limit_s * 2))
            except Exception:
                try:
                    fallback_params.max_time_seconds = float(max(30, int(time_limit_s * 2)))
                except Exception:
                    pass

            solution = routing.SolveWithParameters(fallback_params)

        if solution is None:
            # build diagnostics: unreachable pairs and invalid PD pairs
            INF_val = INF if 'INF' in locals() else 10**9
            unreachable = []
            for u in nodes_list:
                for v in nodes_list:
                    if matrix[nodes_list.index(u)][nodes_list.index(v)] >= INF_val:
                        unreachable.append((u, v))
            pd_issues = []
            for p_idx, d_idx in pd_pairs_idx:
                if p_idx < 0 or p_idx >= len(nodes_list) or d_idx < 0 or d_idx >= len(nodes_list):
                    pd_issues.append((p_idx, d_idx))

            diag = {
                'unreachable_pairs_count': len(unreachable),
                'example_unreachable': unreachable[:5],
                'pd_index_issues': pd_issues,
                'nodes_count': len(nodes_list),
            }
            raise RuntimeError(f"OR-Tools solver failed to find a solution within the time limit; diagnostics={diag}")

        # Extract route
        index = routing.Start(0)
        tour_nodes: List[str] = []
        while not routing.IsEnd(index):
            node_idx = manager.IndexToNode(index)
            tour_nodes.append(nodes_list[node_idx])
            index = solution.Value(routing.NextVar(index))
        # append final node (end) -> depot
        tour_nodes.append(nodes_list[manager.IndexToNode(index)])

        # close tour if not closed
        if tour_nodes and tour_nodes[0] != tour_nodes[-1]:
            tour_nodes.append(tour_nodes[0])

        # compute total cost (float) using original costs
        total = 0.0
        for i in range(len(tour_nodes) - 1):
            u, v = tour_nodes[i], tour_nodes[i+1]
            c = costs[u].get(v, float('inf'))
            if c == float('inf'):
                total += float('inf')
            else:
                total += float(c)

        return tour_nodes, total, paths

    def expand_tour(self, tour: List[str], sp_paths: Dict[str, Dict[str, List[str]]]) -> Tuple[List[str], float]:
        # Expand compact tour into node-level path using sp_paths cached earlier
        if not tour or len(tour) < 2:
            return [], 0.0
        full_route: List[str] = []
        total = 0.0
        for i in range(len(tour) - 1):
            u, v = tour[i], tour[i+1]
            info = sp_paths.get(u, {}).get(v)
            if info is None:
                # fallback: compute path with NetworkX on demand
                G = self._ensure_map()
                path = list(nx.shortest_path(G, u, v, weight='weight'))
                cost = sum(G[path[j]][path[j+1]]['weight'] for j in range(len(path)-1))
            else:
                path = info
                # compute cost by summing edges if path present
                if path is None:
                    raise ValueError(f"No path from {u} to {v}")
                G = self._ensure_map()
                cost = 0.0
                for j in range(len(path)-1):
                    cost += G[path[j]][path[j+1]]['weight']

            if full_route and full_route[-1] == path[0]:
                full_route.extend(path[1:])
            else:
                full_route.extend(path)
            total += cost

        return full_route, total


if __name__ == "__main__":
    # Simple demo usage
    solver = ORToolsTSP()
    # example node list: if None, will use the whole map
    try:
        tour, cost, sp = solver.solve(nodes=None, pickup_delivery_pairs=None, time_limit_s=5)
        print('Compact tour:', tour)
        print('Compact cost:', cost)
    except Exception as e:
        print('Failed to run OR-Tools TSP solver:', e)

# Backwards compatibility: some modules import `TSP` from this module
TSP = ORToolsTSP
