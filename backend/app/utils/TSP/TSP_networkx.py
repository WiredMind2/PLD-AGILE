import os
import sys
import random
import math
from typing import Dict, List, Optional, Any, cast, Tuple
from types import SimpleNamespace

from app.models.schemas import Tour

import networkx as nx

class TSP:
    def __init__(self):
        # We'll build a NetworkX graph from XML map
        # data and use NetworkX shortest-path routines which are C-optimized
        # and much faster than the Python A* implementation for this workload.
        # cache for the parsed/constructed map graph to avoid reparsing XML
        # on repeated calls to `solve()`.
        self.graph = None
        self._all_nodes = None

    def _build_networkx_map_graph(self, xml_file_path: str | None = None):
        """Parse the XML map and return a directed NetworkX graph and the node list.

        The returned graph uses edge attribute 'weight' with the segment length (meters).
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
        # Add nodes (use intersection ids as strings)
        for inter in map_data.intersections:
            G.add_node(str(inter.id))

        # Add directed edges with weight = length_m
        for seg in map_data.road_segments:
            start_id = str(getattr(seg.start, "id", seg.start))
            end_id = str(getattr(seg.end, "id", seg.end))
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
                        start_id, end_id, weight=weight, street_name=seg.street_name
                    )

        # Cache the built graph for subsequent calls when no explicit
        # xml_file_path is provided.
        self.graph = G
        self._all_nodes = list(G.nodes())
        return G, list(self._all_nodes)

    # Christofides-style polynomial-time approximate solver is used below.

    def _build_metric_complete_graph(self, graph):
        """Build a symmetric metric complete graph from a directed sp_graph.

        Steps:
        - Initialize directed cost matrix from `graph` entries.
        - Run Floyd–Warshall closure to compute shortest directed path costs.
        - Select the largest mutually-reachable undirected component (pairs with finite costs both ways).
        - Symmetrize distances by taking min(cost(u,v), cost(v,u)) and return a NetworkX Graph.

        Unlike earlier code, this function will not raise on missing pairs; instead it
        restricts the metric to the largest mutually-reachable component so callers
        may 'ignore' problematic nodes that prevent a complete metric.
        """
        INF = float("inf")
        nodes = list(graph.keys())
        if not nodes:
            return nx.Graph()

        # Initialize cost matrix C[u][v]
        C = {u: {v: (0.0 if u == v else INF) for v in nodes} for u in nodes}
        for u in nodes:
            for v, info in graph.get(u, {}).items():
                try:
                    c = float(info.get("cost", INF))
                except Exception:
                    c = INF
                if c < C[u].get(v, INF):
                    C[u][v] = c

        # `graph` (sp_graph) is expected to contain shortest-path costs from
        # each source to all targets computed with Dijkstra in the caller.
        # Therefore an additional Floyd–Warshall closure is redundant and
        # removed to avoid the O(k^3) cost. C[u][v] already holds the shortest
        # directed distances among the requested nodes (or INF when
        # unreachable).

        # Build undirected adjacency for mutual reachability
        adj_mutual = {u: set() for u in nodes}
        for u in nodes:
            for v in nodes:
                if u == v:
                    continue
                if C[u][v] != INF and C[v][u] != INF:
                    adj_mutual[u].add(v)

        # Find connected components in the undirected mutual graph
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
            # No mutual reachability; return empty graph
            return nx.Graph()

        # choose the largest component
        components.sort(key=len, reverse=True)
        largest = components[0]
        if len(largest) < 2:
            # Nothing useful to build
            return nx.Graph()

        chosen_nodes = list(largest)

        # Symmetrize to metric: D[u][v] = min(C[u][v], C[v][u]) for chosen nodes
        G = nx.Graph()
        for u in chosen_nodes:
            G.add_node(u)

        for i, u in enumerate(chosen_nodes):
            for v in chosen_nodes[i + 1 :]:
                d = float(min(C[u][v], C[v][u]))
                # by construction via mutual reachability, d should be finite
                G.add_edge(u, v, weight=d)

        return G

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
        
        The function uses NetworkX shortest-paths for pairwise distances and
        the existing metric builder `_build_metric_complete_graph` to obtain
        symmetric metric distances between the involved nodes.
        
        Args:
            tour: Tour object containing pickup-delivery pairs
            start_node: Optional depot/start node ID. If provided, the tour will
                       start and end at this node. The algorithm will find the
                       closest pickup/delivery points to this start node.
        """
        # Extract pickup-delivery pairs from the provided Tour object
        pd_pairs = list(tour.deliveries)
        if not pd_pairs:
            return [], 0.0
        
        # Determine problem size for adaptive strategy selection
        num_nodes = len(pd_pairs) * 2  # Each pair has pickup + delivery
        
        # Adaptive parameters based on problem size
        if num_nodes <= 4:
            # Small problem: Fast greedy
            strategy = "fast"
            num_heuristics = 1
            num_restarts = 1
            iterations_per_restart = 200
            use_simulated_annealing = False
            use_or_opt = False
        elif num_nodes <= 12:
            # Medium problem: Balanced approach
            strategy = "balanced"
            num_heuristics = 2
            num_restarts = 2
            iterations_per_restart = 800
            use_simulated_annealing = True
            use_or_opt = True
        else:
            # Large problem: Best single heuristic, focused search
            strategy = "focused"
            num_heuristics = 1
            num_restarts = 1
            iterations_per_restart = 500
            use_simulated_annealing = False
            use_or_opt = False

        # Build the set/list of all involved nodes (pickups and deliveries)
        pickups = [p for p, _ in pd_pairs]
        deliveries = [d for _, d in pd_pairs]
        nodes_list = []
        for p, d in pd_pairs:
            if p not in nodes_list:
                nodes_list.append(p)
            if d not in nodes_list:
                nodes_list.append(d)

        # Build map graph and validate nodes
        G_map, _ = self._build_networkx_map_graph()
        missing = [n for n in nodes_list if n not in G_map.nodes()]
        if missing:
            print(
                f"Warning: {len(missing)} requested TSP nodes not present in map (examples: {missing[:5]})"
            )
            nodes_list = [n for n in nodes_list if n in G_map.nodes()]
        
        # If start_node is provided, add it to nodes_list for shortest path computation
        if start_node is not None:
            start_node = str(start_node)
            if start_node not in G_map.nodes():
                print(f"Warning: start_node {start_node} not in map, ignoring")
                start_node = None
            elif start_node not in nodes_list:
                nodes_list.append(start_node)

        # Compute pairwise shortest-paths among nodes of interest
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

        # Build symmetric metric among the requested nodes
        G = self._build_metric_complete_graph(sp_graph)
        if G.number_of_nodes() == 0:
            return [], 0.0

        # Filter pickup-delivery pairs to those fully present in the metric graph
        pd_pairs = [(p, d) for (p, d) in pd_pairs if p in G.nodes() and d in G.nodes()]
        if not pd_pairs:
            # nothing mutually-reachable; return empty
            return [], 0.0

        # Prepare pickup/delivery data structures
        pickups = [p for p, _ in pd_pairs]
        deliveries = [d for _, d in pd_pairs]
        pair_of = {p: d for p, d in pd_pairs}

        # Helper: compute compact tour cost on the metric graph G
        def tour_cost(seq: List[str]) -> float:
            if not seq or len(seq) < 2:
                return 0.0
            s = 0.0
            for i in range(len(seq) - 1):
                u, v = seq[i], seq[i + 1]
                s += G[u][v]["weight"]
            return s

        # Helper: check if a tour respects pickup-before-delivery precedence
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

        # Build quick lookup for precedence
        pickup_set = set(p for p, _ in pd_pairs if p in nodes_list)
        delivery_map = {d: p for p, d in pd_pairs if p in nodes_list and d in nodes_list}

        INF = float("inf")

        # =================================================================
        # STRATEGY 1: Nearest Neighbor from best starting point
        # =================================================================
        def build_nearest_neighbor_tour() -> Tuple[List[str], float]:
            """Build tour by nearest neighbor, considering all unvisited nodes."""
            # Try starting from each pickup and keep best
            best_tour = None
            best_cost = INF
            
            for start_pickup in pickups[:3]:  # Try first 3 pickups as starts
                if start_pickup not in G.nodes():
                    continue
                    
                unvisited = set(pickups + deliveries)
                if start_node is not None and start_node in G.nodes():
                    current = start_node
                    route = [start_node]
                else:
                    current = start_pickup
                    route = []
                    
                # Always start with a pickup
                if current != start_pickup:
                    route.append(start_pickup)
                    unvisited.discard(start_pickup)
                    current = start_pickup
                else:
                    unvisited.discard(start_pickup)
                
                while unvisited:
                    # Find nearest node that maintains precedence
                    best_next = None
                    best_dist = INF
                    
                    for node in unvisited:
                        # Check if we can visit this node (precedence)
                        can_visit = True
                        if node in deliveries:
                            # Check if pickup was already visited
                            req_pickup = delivery_map[node]
                            if req_pickup in unvisited:
                                can_visit = False
                        
                        if can_visit:
                            dist = G[current][node]["weight"]
                            if dist < best_dist:
                                best_dist = dist
                                best_next = node
                    
                    if best_next is None:
                        # Forced to add remaining (shouldn't happen with valid precedence)
                        best_next = list(unvisited)[0]
                    
                    route.append(best_next)
                    unvisited.discard(best_next)
                    current = best_next
                
                # Close tour
                if start_node is not None and start_node in G.nodes():
                    if route[-1] != start_node:
                        route.append(start_node)
                else:
                    if route[0] != route[-1]:
                        route.append(route[0])
                
                cost = tour_cost(route)
                if cost < best_cost and is_valid_tour(route[:-1] if route[0] == route[-1] else route):
                    best_cost = cost
                    best_tour = route
            
            return best_tour or [], best_cost

        # =================================================================
        # STRATEGY 2: Savings algorithm adaptation
        # =================================================================
        def build_savings_tour() -> Tuple[List[str], float]:
            """Build tour using Clarke-Wright savings heuristic adapted for precedence."""
            # Start with individual pickup->delivery routes
            routes = []
            depot = start_node if start_node and start_node in G.nodes() else pickups[0]
            
            for p, d in pd_pairs:
                if p in G.nodes() and d in G.nodes():
                    routes.append([p, d])
            
            # Calculate savings for merging routes
            savings = []
            for i in range(len(routes)):
                for j in range(i + 1, len(routes)):
                    route_i, route_j = routes[i], routes[j]
                    # Try merging: depot -> route_i -> route_j -> depot
                    # Savings = dist(i_end, depot) + dist(depot, j_start) - dist(i_end, j_start)
                    i_end = route_i[-1]
                    j_start = route_j[0]
                    s = (G[i_end][depot]["weight"] + G[depot][j_start]["weight"] - 
                         G[i_end][j_start]["weight"])
                    savings.append((s, i, j))
            
            savings.sort(reverse=True)
            
            # Merge routes greedily
            merged = [False] * len(routes)
            final_route = []
            
            for s, i, j in savings[:len(routes)//2]:  # Limit merges
                if not merged[i] and not merged[j]:
                    routes[i].extend(routes[j])
                    merged[j] = True
            
            # Combine remaining routes
            for i, route in enumerate(routes):
                if not merged[i]:
                    final_route.extend(route)
            
            if not final_route:
                return [], INF
            
            # Add depot if needed
            if start_node and start_node in G.nodes():
                final_route = [start_node] + final_route + [start_node]
            else:
                final_route.append(final_route[0])
            
            cost = tour_cost(final_route)
            return final_route, cost

        # =================================================================
        # STRATEGY 3: Insertion heuristic with smart ordering
        # =================================================================
        def build_insertion_tour() -> Tuple[List[str], float]:
            """Build tour by inserting pickup-delivery pairs in best positions."""
            depot = start_node if start_node and start_node in G.nodes() else pickups[0]
            
            # Start with first pickup-delivery pair
            if not pd_pairs:
                return [], INF
            
            # Find pair closest to depot
            best_pair = None
            best_dist = INF
            for p, d in pd_pairs:
                if p in G.nodes() and d in G.nodes():
                    dist = G[depot][p]["weight"] if depot != p else 0
                    if dist < best_dist:
                        best_dist = dist
                        best_pair = (p, d)
            
            if not best_pair:
                return [], INF
            
            p0, d0 = best_pair
            if start_node and start_node in G.nodes():
                route = [start_node, p0, d0, start_node]
            else:
                route = [p0, d0, p0]
            
            remaining = [(p, d) for (p, d) in pd_pairs if (p, d) != best_pair 
                        and p in G.nodes() and d in G.nodes()]
            
            # Insert remaining pairs at best positions
            while remaining:
                best_insertion = None
                best_cost_increase = INF
                best_pair_idx = -1
                
                for pair_idx, (p, d) in enumerate(remaining):
                    # Try inserting p and d at all valid positions
                    for i in range(1, len(route)):
                        for j in range(i, len(route)):
                            # Insert p at position i, d at position j
                            new_route = route[:i] + [p] + route[i:j] + [d] + route[j:]
                            
                            if not is_valid_tour(new_route[:-1] if new_route[0] == new_route[-1] else new_route):
                                continue
                            
                            new_cost = tour_cost(new_route)
                            old_cost = tour_cost(route)
                            cost_increase = new_cost - old_cost
                            
                            if cost_increase < best_cost_increase:
                                best_cost_increase = cost_increase
                                best_insertion = new_route
                                best_pair_idx = pair_idx
                
                if best_insertion is None:
                    # No valid insertion found, append remaining
                    for p, d in remaining:
                        route.insert(-1, p)
                        route.insert(-1, d)
                    break
                
                route = best_insertion
                remaining.pop(best_pair_idx)
            
            cost = tour_cost(route)
            return route, cost

        # =================================================================
        # Generate initial solutions (adaptive based on strategy)
        # =================================================================
        candidate_tours = []
        
        # Always use Nearest Neighbor (fast and reliable)
        nn_tour, nn_cost = build_nearest_neighbor_tour()
        if nn_tour:
            candidate_tours.append((nn_tour, nn_cost))
        
        # Add more heuristics for medium problems
        if num_heuristics >= 2:
            # Strategy 2: Insertion (better quality, slower)
            ins_tour, ins_cost = build_insertion_tour()
            if ins_tour and is_valid_tour(ins_tour[:-1] if ins_tour[0] == ins_tour[-1] else ins_tour):
                candidate_tours.append((ins_tour, ins_cost))
        
        if num_heuristics >= 3:
            # Strategy 3: Savings (good for clustered deliveries)
            sv_tour, sv_cost = build_savings_tour()
            if sv_tour and is_valid_tour(sv_tour[:-1] if sv_tour[0] == sv_tour[-1] else sv_tour):
                candidate_tours.append((sv_tour, sv_cost))
        
        # Pick best initial tour
        if not candidate_tours:
            return [], 0.0
        
        candidate_tours.sort(key=lambda x: x[1])
        tour_seq, total = candidate_tours[0]
        
        # =================================================================
        # Adaptive local search with multiple operators
        # =================================================================
        closed = len(tour_seq) >= 2 and tour_seq[0] == tour_seq[-1]
        core = tour_seq[:-1] if closed else list(tour_seq)
        
        # Handle small tours (less than 3 nodes can't be improved much)
        if len(core) < 3:
            if closed and core:
                core.append(core[0])
            return core, tour_cost(core) if core else 0.0
        
        # Multi-start with adaptive parameters
        best_core = list(core)
        best_cost = total
        
        for restart in range(num_restarts):
            if restart > 0 and len(best_core) >= 3:
                # Perturb by doing random swaps that maintain precedence
                perturbed = list(best_core)
                num_swaps = min(3, len(perturbed) // 3)
                for _ in range(num_swaps):
                    if len(perturbed) < 3:
                        break
                    i = random.randint(1, len(perturbed) - 2)
                    j = random.randint(1, len(perturbed) - 2)
                    if i != j:
                        perturbed[i], perturbed[j] = perturbed[j], perturbed[i]
                        if not is_valid_tour(perturbed):
                            perturbed[i], perturbed[j] = perturbed[j], perturbed[i]
                core = perturbed
                total = tour_cost(core + ([core[0]] if closed else []))
            
            # Simulated annealing parameters (only for medium problems)
            if use_simulated_annealing:
                temperature = total * 0.05  # Reduced from 0.1
                cooling_rate = 0.99  # Faster cooling
                min_temperature = 0.01
            else:
                temperature = 0
                min_temperature = 0
            
            improved = True
            max_iters = iterations_per_restart
            iters = 0
            n = len(core)
            
            while (improved or temperature > min_temperature) and iters < max_iters:
                improved = False
                iters += 1
                
                # Operator 1: 2-opt (always enabled)
                for i in range(1, min(n - 2, n)):
                    if iters >= max_iters:
                        break
                    # Limit neighborhood size for large problems
                    max_j = min(n, i + 15) if strategy == "focused" else n
                    for j in range(i + 2, max_j):
                        # Reverse segment [i:j]
                        new_core = core[:i] + list(reversed(core[i:j])) + core[j:]
                        
                        if not is_valid_tour(new_core):
                            continue
                        
                        new_seq = new_core + ([new_core[0]] if closed else [])
                        new_cost = tour_cost(new_seq)
                        delta = new_cost - total
                        
                        # Accept if better OR with SA probability
                        accept = delta < -1e-9
                        if not accept and temperature > min_temperature:
                            accept = random.random() < math.exp(-delta / temperature)
                        
                        if accept:
                            core = new_core
                            total = new_cost
                            improved = True
                            
                            if delta < -1e-9:  # Real improvement
                                break
                    
                    if improved and temperature <= min_temperature:
                        break
                
                # Operator 2: Or-Opt (only for medium problems with balance strategy)
                if use_or_opt and (not improved or temperature > min_temperature):
                    for length in [1, 2]:
                        if length >= n - 1 or iters >= max_iters:
                            continue
                        for i in range(1, n - length):
                            if iters >= max_iters:
                                break
                            segment = core[i:i+length]
                            # Try only nearby positions for efficiency
                            positions = list(range(max(1, i - 4), min(n - length + 1, i + 5)))
                            for j in positions:
                                if j == i or (j > i and j < i + length):
                                    continue
                                
                                # Remove segment and insert at position j
                                new_core = core[:i] + core[i+length:]
                                insert_pos = j if j < i else j - length
                                new_core = new_core[:insert_pos] + segment + new_core[insert_pos:]
                                
                                if not is_valid_tour(new_core):
                                    continue
                                
                                new_seq = new_core + ([new_core[0]] if closed else [])
                                new_cost = tour_cost(new_seq)
                                delta = new_cost - total
                                
                                accept = delta < -1e-9
                                if not accept and temperature > min_temperature:
                                    accept = random.random() < math.exp(-delta / temperature)
                                
                                if accept:
                                    core = new_core
                                    total = new_cost
                                    improved = True
                                    
                                    if delta < -1e-9:
                                        break
                            
                            if improved and temperature <= min_temperature:
                                break
                        
                        if improved and temperature <= min_temperature:
                            break
                
                # Cool down temperature
                if use_simulated_annealing:
                    temperature *= cooling_rate
            
            # Update best if improved
            if total < best_cost - 1e-9:
                best_cost = total
                best_core = list(core)
        
        # Use best found tour
        core = best_core
        total = best_cost
        
        # Re-close tour
        if closed and core:
            core.append(core[0])
        
        return core, total

    # Note: multi-courier solver was intentionally removed. For multi-agent
    # routing, use a separate coordinator/service which can call `solve` per
    # agent (e.g. in `app.services.TSPService`) after dividing locations.

    def expand_tour_with_paths(self, tour, sp_graph):
        """Expand a compact tour (list of location nodes) into the full node-level route
        by concatenating the A* shortest-paths between consecutive tour nodes.

        Returns (full_route_list, total_cost). Raises ValueError if any leg is unreachable.
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


if __name__ == "__main__":
    # Example usage
    tsp = TSP()
    # create a minimal Tour-like object from available map nodes
    G_map, nodes = tsp._build_networkx_map_graph()
    if len(nodes) < 2:
        print("Map does not contain enough nodes for a sample tour")
    else:
        # build up to 3 sample pickup-delivery pairs from map nodes
        sample_pairs = []
        for i in range(0, min(6, len(nodes)), 2):
            a = nodes[i]
            b = nodes[i + 1] if i + 1 < len(nodes) else nodes[0]
            sample_pairs.append((a, b))

        sample_tour = cast(Tour, SimpleNamespace(deliveries=sample_pairs))

        path, cost = tsp.solve(sample_tour)
        print("Compact tour:", path)
        print("Compact cost:", cost)
    # If you want to expand the compact tour to the full node-level route,
    # recompute the pairwise sp_graph (as in solve_christofides) and call
    # expand_tour_with_paths(). Keeping example minimal here.
