import heapq
try:
    from .Astar import Astar
except ImportError:
    from Astar import Astar



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
        """Return a lightweight dict-of-dicts distance matrix from the shortest-paths graph.

        The returned object is a mapping u -> v -> float cost. Raises ValueError if any pair is unreachable.
        """
        nodes = list(graph.keys())
        D = {u: {} for u in nodes}
        for u in nodes:
            for v in nodes:
                if u == v:
                    D[u][v] = 0.0
                    continue
                cost = graph[u].get(v, {}).get('cost', float('inf'))
                if cost == float('inf'):
                    cost = graph[v].get(u, {}).get('cost', float('inf'))
                if cost == float('inf'):
                    raise ValueError(f"Graph is not complete/metric between {u} and {v}")
                D[u][v] = float(cost)
        return D

    def solve_multi_start_nn_2opt(self, nodes=None):
        """Return a tour and cost using Multi-start Nearest-Neighbor + 2-opt heuristic.

        This is fast, deterministic for a given set of starts, and gives good-quality tours for metric TSPs.
        """
        if nodes is not None:
            self.astar.nodes = nodes
        else:
            self.astar.load_data()

        sp_graph = self.astar.compute_shortest_paths_graph()
        D = self._build_metric_complete_graph(sp_graph)

        nodes_list = list(D.keys())

        def tour_cost(tour):
            c = 0.0
            for i in range(len(tour)-1):
                c += D[tour[i]][tour[i+1]]
            return c

        def nearest_neighbor(start):
            unvisited = set(nodes_list)
            tour = [start]
            unvisited.remove(start)
            cur = start
            while unvisited:
                nxt = min(unvisited, key=lambda x: D[cur][x])
                tour.append(nxt)
                unvisited.remove(nxt)
                cur = nxt
            tour.append(start)
            return tour

        def two_opt(tour):
            improved = True
            n = len(tour)
            while improved:
                improved = False
                for i in range(1, n - 2):
                    for j in range(i+1, n - 1):
                        # compute delta for swapping (i..j)
                        a, b = tour[i-1], tour[i]
                        c, d = tour[j], tour[(j+1) % n]
                        delta = D[a][c] + D[b][d] - D[a][b] - D[c][d]
                        if delta < -1e-12:
                            # perform 2-opt: reverse segment i..j
                            tour[i:j+1] = reversed(tour[i:j+1])
                            improved = True
                # loop until no improvement
            return tour

        best_tour = None
        best_cost = float('inf')

        # multi-start: try each node as start up to a limit
        max_starts = min(len(nodes_list), 10)
        starts = nodes_list if len(nodes_list) <= max_starts else nodes_list[:max_starts]

        for s in starts:
            t = nearest_neighbor(s)
            t = two_opt(t)
            c = tour_cost(t)
            if c < best_cost:
                best_cost = c
                best_tour = t

        return best_tour, best_cost

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
    path, cost = tsp.solve_multi_start_nn_2opt()
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