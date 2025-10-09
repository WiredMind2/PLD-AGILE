import heapq
try:
    from .Astar import Astar
except ImportError:
    from Astar import Astar

import networkx as nx


class TSP():
    def __init__(self):
        self.astar = Astar()

    def solve(self, nodes=None):
        if nodes is not None:
            self.astar.nodes = nodes
        else:
            self.astar.load_data()
        graph = self.astar.compute_shortest_paths_graph()

        # Use the first node in the graph as the start
        try:
            start = next(iter(graph))
        except StopIteration:
            return None, float('inf')

        # We'll push entries containing the full ordered path so we can return a valid tour.
        # Heap entries: (cost, tie, current_node, visited_frozenset, path_list)
        import itertools
        counter = itertools.count()

        n_nodes = len(graph)
        start_entry = (0.0, next(counter), start, frozenset([start]), [start])
        heap = [start_entry]

        while heap:
            cost, _, node, visited, path = heapq.heappop(heap)

            # If we've visited all nodes, try to close the tour back to start
            if len(visited) == n_nodes:
                back_cost = graph[node].get(start, {}).get('cost', float('inf'))
                if back_cost != float('inf'):
                    return path + [start], cost + back_cost
                # no edge back to start from this node, continue searching

            for neighbor, data in graph[node].items():
                edge_cost = data.get('cost', float('inf'))
                if edge_cost == float('inf'):
                    continue
                # Allow revisiting nodes (to go back along a segment), but track which
                # distinct nodes have been seen in `visited`. If neighbor was already
                # seen, `new_visited` remains the same; otherwise we add it.
                if neighbor in visited:
                    new_visited = visited
                else:
                    new_visited = visited | {neighbor}

                new_path = path + [neighbor]
                new_cost = cost + edge_cost

                # Prune states we've already reached cheaper or equal before. Keyed by
                # (node, visited_set) so revisiting is allowed but we avoid endless loops.
                if not hasattr(self, '_tsp_best_cost'):
                    self._tsp_best_cost = {}

                state_key = (neighbor, new_visited)
                prev_best = self._tsp_best_cost.get(state_key, float('inf'))
                if new_cost >= prev_best:
                    continue

                self._tsp_best_cost[state_key] = new_cost
                heapq.heappush(heap, (new_cost, next(counter), neighbor, new_visited, new_path))

        return None, float('inf')

    def _build_metric_complete_graph(self, graph):
        """Convert the provided shortest-paths dict-of-dicts into a complete metric networkx Graph.

        `graph` is expected to be mapping u -> {v: {'cost': w, ...}, ...}
        Missing or infinite edges will be treated as absent and raise ValueError if graph is not metric/complete.
        """
        G = nx.Graph()
        nodes = list(graph.keys())
        for u in nodes:
            G.add_node(u)

        for i, u in enumerate(nodes):
            for v in nodes[i+1:]:
                cost = graph[u].get(v, {}).get('cost', float('inf'))
                if cost == float('inf'):
                    # If missing, try the reverse direction
                    cost = graph[v].get(u, {}).get('cost', float('inf'))
                if cost == float('inf'):
                    raise ValueError(f"Graph is not complete/metric between {u} and {v}")
                G.add_edge(u, v, weight=cost)
        return G

    def solve_christofides(self, nodes=None):
        """Return a tour and cost using Christofides algorithm (approx 1.5-approx for metric TSP).

        Steps:
        1. Build metric complete graph from computed shortest-paths.
        2. Compute MST.
        3. Find odd-degree vertices of MST.
        4. Compute minimum-weight perfect matching on the induced subgraph of odd-degree vertices.
        5. Combine MST and matching to make Eulerian multigraph, find Eulerian circuit.
        6. Shortcut repeated vertices to obtain Hamiltonian tour.
        """
        if nodes is not None:
            self.astar.nodes = nodes
        else:
            self.astar.load_data()

        sp_graph = self.astar.compute_shortest_paths_graph()
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
        matching = nx.algorithms.matching.min_weight_matching(M, weight='weight')

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
    tsp.astar.load_data()
    sp_graph = tsp.astar.compute_shortest_paths_graph()
    path, cost = tsp.solve_christofides()
    print("Compact tour:", path)
    print("Compact cost:", cost)

    try:
        full_route, full_cost = tsp.expand_tour_with_paths(path, sp_graph)
        print("Expanded route:", full_route)
        print("Expanded cost:", full_cost)
        if abs(full_cost - cost) > 1e-6:
            print("Warning: expanded cost differs from compact cost!")
        else:
            print("Expanded cost matches compact cost.")
    except ValueError as e:
        print("Could not expand tour:", e)