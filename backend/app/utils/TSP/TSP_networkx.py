import heapq
import os
import sys
from typing import Dict, List, Optional
try:
    import networkx as nx
except Exception:
    raise

try:
    from app.services.XMLParser import XMLParser
except Exception:
    # fallback for direct script execution / tests
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from services.XMLParser import XMLParser


class TSP():
    def __init__(self):
        # No A* dependency here. We'll build a NetworkX graph from XML map
        # data and use NetworkX shortest-path routines which are C-optimized
        # and much faster than the Python A* implementation for this workload.
        self.graph = None

    def _build_networkx_map_graph(self, xml_file_path: str | None = None):
        """Parse the XML map and return a directed NetworkX graph and the node list.

        The returned graph uses edge attribute 'weight' with the segment length (meters).
        """
        if xml_file_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(current_dir, "..", "..", "..", "..")
            xml_file_path = os.path.join(project_root, "fichiersXMLPickupDelivery", "petitPlan.xml")

        with open(xml_file_path, 'r', encoding='utf-8') as f:
            xml_text = f.read()

        map_data = XMLParser.parse_map(xml_text)

        G = nx.DiGraph()
        # Add nodes (use intersection ids as strings)
        for inter in map_data.intersections:
            G.add_node(str(inter.id))

        # Add directed edges with weight = length_m
        for seg in map_data.road_segments:
            start_id = str(getattr(seg.start, 'id', seg.start))
            end_id = str(getattr(seg.end, 'id', seg.end))
            try:
                weight = float(seg.length_m)
            except Exception:
                weight = float('inf')
            # If node ids are present, add the edge
            if start_id in G.nodes and end_id in G.nodes:
                # If multiple edges exist, keep the smallest weight
                prev = G.get_edge_data(start_id, end_id, default=None)
                if prev is None or weight < prev.get('weight', float('inf')):
                    G.add_edge(start_id, end_id, weight=weight, street_name=seg.street_name)

        return G, list(G.nodes())

    # The previous brute-force `solve` was removed in favour of the
    # Christofides-based polynomial-time solver (renamed to `solve`).

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
        INF = float('inf')
        nodes = list(graph.keys())
        if not nodes:
            return nx.Graph()

        # Initialize cost matrix C[u][v]
        C = {u: {v: (0.0 if u == v else INF) for v in nodes} for u in nodes}
        for u in nodes:
            for v, info in graph.get(u, {}).items():
                try:
                    c = float(info.get('cost', INF))
                except Exception:
                    c = INF
                if c < C[u].get(v, INF):
                    C[u][v] = c

        # Floyd–Warshall: closure to get shortest directed costs
        for k in nodes:
            row_k = C[k]
            for i in nodes:
                ik = C[i][k]
                if ik == INF:
                    continue
                row_i = C[i]
                base = ik
                for j in nodes:
                    kj = row_k[j]
                    if kj == INF:
                        continue
                    nd = base + kj
                    if nd < row_i[j]:
                        row_i[j] = nd

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
            for v in chosen_nodes[i+1:]:
                d = float(min(C[u][v], C[v][u]))
                # by construction via mutual reachability, d should be finite
                G.add_edge(u, v, weight=d)

        return G

    def solve(self, nodes=None, must_visit=None):
        """Return a tour and cost using Christofides algorithm (approx 1.5-approx for metric TSP).

        Steps:
        1. Build metric complete graph from computed shortest-paths.
        2. Compute MST.
        3. Find odd-degree vertices of MST.
        4. Compute minimum-weight perfect matching on the induced subgraph of odd-degree vertices.
        5. Combine MST and matching to make Eulerian multigraph, find Eulerian circuit.
        6. Shortcut repeated vertices to obtain Hamiltonian tour.
        """
        # Compute pairwise shortest-paths among the TSP nodes using networkx
        G_map, all_nodes = self._build_networkx_map_graph()
        # Support `must_visit` similar to the removed solve(): if provided,
        # take the union of `nodes` and `must_visit` so the solver computes
        # pairwise distances among required locations and any extra nodes
        # provided for connectivity.
        if must_visit is not None:
            if nodes is not None:
                nodes_list = list(dict.fromkeys(list(nodes) + list(must_visit)))
            else:
                nodes_list = list(dict.fromkeys(list(must_visit)))
        else:
            nodes_list = list(nodes) if nodes is not None else list(all_nodes)

        # Validate and filter out missing nodes in the map graph
        missing = [n for n in nodes_list if n not in G_map.nodes()]
        if missing:
            print(f"Warning: {len(missing)} requested TSP nodes not present in map (examples: {missing[:5]})")
            nodes_list = [n for n in nodes_list if n in G_map.nodes()]

        # Build sp_graph similar to solve()
        sp_graph = {}
        for src in nodes_list:
            try:
                # NetworkX returns (distances: dict[node, float], paths: dict[node, list[node]])
                lengths, paths = nx.single_source_dijkstra(G_map, src, weight='weight')
                # help static type checkers
                lengths = dict(lengths)  # type: Dict[str, float]
                paths = dict(paths)      # type: Dict[str, List[str]]
            except Exception:
                lengths = {}  # type: Dict[str, float]
                paths = {}    # type: Dict[str, List[str]]
            sp_graph[src] = {}
            for tgt in nodes_list:
                if tgt == src:
                    sp_graph[src][tgt] = {'path': [src], 'cost': 0.0}
                else:
                    sp_graph[src][tgt] = {'path': paths.get(tgt), 'cost': lengths.get(tgt, float('inf'))}

        G = self._build_metric_complete_graph(sp_graph)

        # 1. MST
        T = nx.minimum_spanning_tree(G, weight='weight')

        # 2. Odd degree vertices
        odd_nodes = [v for v, d in T.degree() if d % 2 == 1]

        # 3. Induced subgraph on odd degree vertices (complete within these nodes via G)
        M = nx.Graph()
        for i, u in enumerate(odd_nodes):
            for v in odd_nodes[i+1:]:
                w = G[u][v]['weight']
                M.add_edge(u, v, weight=w)

        # 4. Minimum weight perfect matching on M (returns set of edges)
        # use explicit import to satisfy static analyzers
        from networkx.algorithms import matching as nx_matching
        matching = nx_matching.min_weight_matching(M, weight='weight')

        # 5. Combine edges of T and matching to form a multigraph
        multigraph = nx.MultiGraph()
        multigraph.add_nodes_from(T.nodes())
        multigraph.add_edges_from(T.edges(data=True))
        # add matching edges (as single edges)
        for u, v in matching:
            multigraph.add_edge(u, v, weight=G[u][v]['weight'])

        # 6. Find Eulerian circuit
        if not nx.is_eulerian(multigraph):
            # should be Eulerian by construction, but ensure it
            # connect components if necessary (shouldn't happen for connected G)
            multigraph = nx.eulerize(multigraph)

        euler_circuit = list(nx.eulerian_circuit(multigraph))

        # 7. Shortcut repeated vertices to get Hamiltonian tour
        tour = []
        seen = set()
        for u, v in euler_circuit:
            if u not in seen:
                tour.append(u)
                seen.add(u)
            # last edge's v possibly added on next iteration
        # ensure all nodes included
        for n in G.nodes():
            if n not in seen:
                tour.append(n)

        # close tour
        if tour and tour[0] != tour[-1]:
            tour.append(tour[0])

        # compute total cost
        total = 0.0
        for i in range(len(tour)-1):
            u, v = tour[i], tour[i+1]
            total += G[u][v]['weight']

        return tour, total

    def solve_multi_couriers(self, num_couriers, nodes=None, must_visit=None, depot_node=None):
        """Multi-agent TSP solver using cluster-first, route-second approach.
        
        Args:
            num_couriers: Number of delivery agents
            nodes: Optional list of all nodes to consider
            must_visit: List of nodes that must be visited
            depot_node: Starting/ending point for all couriers (first node if None)
            
        Returns:
            Dictionary with courier assignments:
            {
                'courier_1': {'tour': [...], 'cost': float},
                'courier_2': {'tour': [...], 'cost': float},
                ...
                'total_cost': float
            }
        """
        # Build map graph
        G_map, all_nodes = self._build_networkx_map_graph()
        
        # Determine nodes to visit
        if must_visit is not None:
            if nodes is not None:
                nodes_list = list(dict.fromkeys(list(nodes) + list(must_visit)))
            else:
                nodes_list = list(dict.fromkeys(list(must_visit)))
        else:
            nodes_list = list(nodes) if nodes is not None else list(all_nodes)
        
        # Filter valid nodes
        nodes_list = [n for n in nodes_list if n in G_map.nodes()]
        
        if not nodes_list:
            return {'total_cost': 0.0}
        
        # Set depot
        if depot_node is None:
            depot_node = nodes_list[0]
        elif depot_node not in G_map.nodes():
            depot_node = nodes_list[0]
        
        # Remove depot from visit list if present
        visit_nodes = [n for n in nodes_list if n != depot_node]
        
        if not visit_nodes:
            # Only depot, return empty tours
            result = {'total_cost': 0.0}
            for i in range(num_couriers):
                result[f'courier_{i+1}'] = {'tour': [depot_node], 'cost': 0.0}
            return result
        
        # Compute shortest paths from depot to all visit nodes for clustering
        try:
            depot_lengths = nx.single_source_dijkstra_path_length(G_map, depot_node, weight='weight')
        except Exception:
            depot_lengths = {}
        
        # Simple clustering: assign nodes to couriers using nearest-neighbor from depot
        # Sort nodes by distance from depot
        sorted_nodes = sorted(visit_nodes, key=lambda n: depot_lengths.get(n, float('inf')))
        
        # Distribute nodes round-robin to balance load
        courier_clusters = [[] for _ in range(num_couriers)]
        for idx, node in enumerate(sorted_nodes):
            courier_clusters[idx % num_couriers].append(node)
        
        # Build complete sp_graph for all relevant nodes
        all_tsp_nodes = [depot_node] + visit_nodes
        sp_graph = {}
        for src in all_tsp_nodes:
            try:
                lengths, paths = nx.single_source_dijkstra(G_map, src, weight='weight')
                lengths = dict(lengths)
                paths = dict(paths)
            except Exception:
                lengths = {}
                paths = {}
            sp_graph[src] = {}
            for tgt in all_tsp_nodes:
                if tgt == src:
                    sp_graph[src][tgt] = {'path': [src], 'cost': 0.0}
                else:
                    sp_graph[src][tgt] = {'path': paths.get(tgt), 'cost': lengths.get(tgt, float('inf'))}
        
        # Solve TSP for each courier
        result = {}
        total_cost = 0.0
        
        for i, cluster in enumerate(courier_clusters):
            courier_name = f'courier_{i+1}'
            
            if not cluster:
                # Empty cluster
                result[courier_name] = {'tour': [depot_node, depot_node], 'cost': 0.0}
                continue
            
            # TSP nodes for this courier: depot + assigned nodes
            courier_nodes = [depot_node] + cluster
            
            # Build metric graph for this subset
            courier_sp_graph = {u: {v: sp_graph[u][v] for v in courier_nodes} for u in courier_nodes}
            G_courier = self._build_metric_complete_graph(courier_sp_graph)
            
            if len(G_courier.nodes()) < 2:
                result[courier_name] = {'tour': [depot_node, depot_node], 'cost': 0.0}
                continue
            
            # Apply Christofides on this subset
            T = nx.minimum_spanning_tree(G_courier, weight='weight')
            odd_nodes = [v for v, d in T.degree() if d % 2 == 1]
            
            if odd_nodes:
                M = nx.Graph()
                for i_idx, u in enumerate(odd_nodes):
                    for v in odd_nodes[i_idx+1:]:
                        w = G_courier[u][v]['weight']
                        M.add_edge(u, v, weight=w)
                
                matching = nx_matching.min_weight_matching(M, weight='weight')
            else:
                matching = set()
            
            multigraph = nx.MultiGraph()
            multigraph.add_nodes_from(T.nodes())
            multigraph.add_edges_from(T.edges(data=True))
            for u, v in matching:
                multigraph.add_edge(u, v, weight=G_courier[u][v]['weight'])
            
            if not nx.is_eulerian(multigraph):
                multigraph = nx.eulerize(multigraph)
            
            euler_circuit = list(nx.eulerian_circuit(multigraph))
            
            # Build tour starting from depot
            tour = []
            seen = set()
            for u, v in euler_circuit:
                if u not in seen:
                    tour.append(u)
                    seen.add(u)
            
            for n in G_courier.nodes():
                if n not in seen:
                    tour.append(n)
            
            # Ensure tour starts and ends at depot
            if tour and tour[0] != depot_node:
                if depot_node in tour:
                    depot_idx = tour.index(depot_node)
                    tour = tour[depot_idx:] + tour[:depot_idx]
            
            if tour and tour[-1] != depot_node:
                tour.append(depot_node)
            
            # Calculate cost
            cost = 0.0
            for j in range(len(tour)-1):
                u, v = tour[j], tour[j+1]
                cost += G_courier[u][v]['weight']
            
            result[courier_name] = {'tour': tour, 'cost': cost}
            total_cost += cost
        
        result['total_cost'] = total_cost
        return result

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
            u, v = tour[i], tour[i+1]
            info = sp_graph.get(u, {}).get(v)
            if info is None or info.get('path') is None:
                raise ValueError(f"No shortest-path from {u} to {v}")
            path = info['path']
            cost = info.get('cost', float('inf'))
            if full_route and full_route[-1] == path[0]:
                full_route.extend(path[1:])
            else:
                full_route.extend(path)
            total += cost
        return full_route, total
    
if __name__ == "__main__":
    # Example usage

    tsp = TSP()
    path, cost = tsp.solve()
    print("Compact tour:", path)
    print("Compact cost:", cost)
    # If you want to expand the compact tour to the full node-level route,
    # recompute the pairwise sp_graph (as in solve_christofides) and call
    # expand_tour_with_paths(). Keeping example minimal here.