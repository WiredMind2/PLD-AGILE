import heapq
import os
import sys
from typing import Dict, List, Optional, Any, cast
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
            return self.graph, list(self._all_nodes) if self._all_nodes is not None else list(self.graph.nodes())

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
            for v in chosen_nodes[i+1:]:
                d = float(min(C[u][v], C[v][u]))
                # by construction via mutual reachability, d should be finite
                G.add_edge(u, v, weight=d)

        return G

    def solve(self, nodes=None, pickup_delivery_pairs: Optional[List[tuple]] = None):
        """Return a compact tour and cost using a Christofides-style approximation.

        This function builds a metric complete graph among the requested nodes
        (using shortest-path distances on the map), computes an approximate
        TSP tour with Christofides steps (MST + minimum-weight matching +
        Eulerian circuit shortcutting), and returns a compact tour (sequence
        of location node ids) and the tour cost.

        Args:
            nodes: Optional iterable of node ids to consider for the TSP. If
                omitted, all map nodes are used.
            must_visit: Optional iterable of node ids that must be included in
                the tour. When provided, the solver will take the union of
                `nodes` and `must_visit`.
            pickup_delivery_pairs: Optional iterable of (pickup, delivery)
                node id pairs. When supplied the returned compact tour will
                be post-processed to ensure each pickup appears before its
                paired delivery. This is a lightweight precedence handling
                step (keeps solver backward-compatible but enforces local
                ordering by reordering the compact tour when necessary).

        Returns:
            (tour, total_cost) where `tour` is a list of node ids (closed
            — first node equals last) and `total_cost` is the sum of metric
            edge weights along the compact tour.
        """
        # Compute pairwise shortest-paths among the TSP nodes using networkx
        G_map, all_nodes = self._build_networkx_map_graph()
        # Support `must_visit` similar to the removed solve(): if provided,
        # take the union of `nodes` and `must_visit` so the solver computes
        # pairwise distances among required locations and any extra nodes
        # provided for connectivity.
        # `nodes` should be the list of node ids to include in the TSP.
        # For backward compatibility callers should pass nodes explicitly.
        nodes_list = list(nodes) if nodes is not None else list(all_nodes)

        pdp = pickup_delivery_pairs

        # Validate and filter out missing nodes in the map graph
        missing = [n for n in nodes_list if n not in G_map.nodes()]
        if missing:
            print(f"Warning: {len(missing)} requested TSP nodes not present in map (examples: {missing[:5]})")
            nodes_list = [n for n in nodes_list if n in G_map.nodes()]

        # If explicit pickup_delivery_pairs provided, add their nodes to nodes_list
        if pdp:
            extra = []
            for p, d in pdp:
                if p in G_map.nodes() and p not in nodes_list:
                    extra.append(p)
                if d in G_map.nodes() and d not in nodes_list:
                    extra.append(d)
            if extra:
                nodes_list = list(dict.fromkeys(nodes_list + extra))

        # Build sp_graph similar to solve()
        sp_graph = {}
        for src in nodes_list:
            try:
                # NetworkX returns (distances: dict[node, float], paths: dict[node, list[node]])
                lengths_raw, paths_raw = nx.single_source_dijkstra(G_map, src, weight='weight')
                # help static type checkers and guard against unexpected return types
                if isinstance(lengths_raw, dict):
                    lengths: Dict[str, float] = cast(Dict[str, float], lengths_raw)
                else:
                    lengths = {}
                if isinstance(paths_raw, dict):
                    paths: Dict[str, List[str]] = cast(Dict[str, List[str]], paths_raw)
                else:
                    paths = {}
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

        # Post-process compact tour to enforce pickup-before-delivery ordering
        # for any provided pickup-delivery pairs. The previous behavior moved
        # deliveries to immediately follow their pickup (forcing immediate
        # drop-off). Here we adopt a deferred-stable reorder: when a delivery
        # appears before its pickup we defer it until its pickup has been
        # visited in the tour. This allows accumulating multiple pickups
        # before making deliveries and typically produces shorter, more
        # realistic routes while still ensuring precedence.
        if pdp:
            # work on the compact tour without the duplicated closing node
            closed = (len(tour) >= 2 and tour[0] == tour[-1])
            core = tour[:-1] if closed else list(tour)

            # build quick-lookup maps for pickups and deliveries
            pickup_of = {p: d for p, d in pdp}
            delivery_of = {d: p for p, d in pdp}

            result = []
            seen_pickups = set()
            deferred_deliveries = []  # deliveries whose pickup hasn't been seen yet (preserve order)

            for node in core:
                # if node is a pickup, append it and mark seen;
                # then flush any deferred deliveries whose pickup is now seen
                if node in pickup_of:
                    result.append(node)
                    seen_pickups.add(node)
                    i = 0
                    while i < len(deferred_deliveries):
                        d = deferred_deliveries[i]
                        p = delivery_of.get(d)
                        if p in seen_pickups:
                            result.append(d)
                            deferred_deliveries.pop(i)
                        else:
                            i += 1
                # if node is a delivery and its pickup was already seen, append;
                # otherwise defer it until later
                elif node in delivery_of:
                    p = delivery_of[node]
                    if p in seen_pickups:
                        result.append(node)
                    else:
                        deferred_deliveries.append(node)
                else:
                    # normal node, keep original order
                    result.append(node)

            # append any remaining deferred deliveries (their pickups were
            # not present in the core order); preserve their original relative order
            for d in deferred_deliveries:
                result.append(d)

            # re-close tour
            if closed and result:
                result.append(result[0])
            tour = result

            # recompute total after modifications
            total = 0.0
            for i in range(len(tour)-1):
                u, v = tour[i], tour[i+1]
                total += G[u][v]['weight']

        return tour, total

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