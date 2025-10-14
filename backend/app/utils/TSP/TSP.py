import heapq
import time
import logging
try:
    from .Astar import Astar
except ImportError:
    from Astar import Astar



class TSP():
    def __init__(self):
        self.astar = Astar()
        self._sp_graph_cache = None

    def solve(self, nodes=None, must_visit=None):
        # `must_visit` is an optional iterable of node ids that the returned
        # tour must pass through. If provided, we ensure these nodes are part
        # of the TSP instance (filtering missing ones) and prefer to compute
        # pairwise shortest paths among them (possibly unioned with `nodes`).
        if nodes is not None:
            self.astar.nodes = nodes
        else:
            self.astar.load_data()

        # If caller provided a set of required nodes, delegate to the
        # multi-start NN + 2-opt solver which supports `must_visit` and
        # targeted pairwise shortest-path computation.
        if must_visit is not None:
            return self.solve_multi_start_nn_2opt(nodes=nodes, must_visit=must_visit)

        start = time.time()
        graph = self.astar.compute_shortest_paths_graph()
        end = time.time()
        print(f"Computed shortest-paths graph in {end - start:.3f} seconds")

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
        """Build a symmetric metric distance matrix from the directed shortest-paths graph.

        This function:
        - initializes a directed cost matrix from `graph` entries,
        - runs Floyd-Warshall to compute shortest directed path costs between any two nodes,
        - selects the largest mutually-reachable undirected component (pairs with finite costs both ways),
        - symmetrizes distances by taking the min(cost(u,v), cost(v,u)).

        Returns: D (dict u -> v -> float)
        Raises ValueError when there are insufficient mutually-reachable nodes to build a TSP instance.
        """
        INF = float('inf')
        nodes = list(graph.keys())
        if not nodes:
            raise ValueError('Empty graph')

        # Initialize cost matrix C[u][v] with direct shortest-path costs where available.
        C = {u: {v: (0.0 if u == v else INF) for v in nodes} for u in nodes}
        for u in nodes:
            for v, info in graph.get(u, {}).items():
                try:
                    c = float(info.get('cost', INF))
                except Exception:
                    c = INF
                if c < C[u].get(v, INF):
                    C[u][v] = c

        # Floyd-Warshall closure
        for k in nodes:
            row_k = C[k]
            for i in nodes:
                ik = C[i][k]
                if ik == INF:
                    continue
                row_i = C[i]
                nd_base = ik
                for j in nodes:
                    kj = row_k[j]
                    if kj == INF:
                        continue
                    nd = nd_base + kj
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
            raise ValueError('No mutually-reachable components found')

        # choose the largest component
        components.sort(key=len, reverse=True)
        largest = components[0]
        if len(largest) < 2:
            raise ValueError('Insufficient mutually-reachable nodes to build a metric TSP instance')

        if len(largest) < len(nodes):
            print("Graph contains unreachable pairs; restricting TSP to %d nodes out of %d", len(largest), len(nodes))

        chosen_nodes = list(largest)

        # Symmetrize to metric: D[u][v] = min(C[u][v], C[v][u]) for chosen nodes
        D = {u: {} for u in chosen_nodes}
        for u in chosen_nodes:
            for v in chosen_nodes:
                if u == v:
                    D[u][v] = 0.0
                else:
                    D[u][v] = float(min(C[u][v], C[v][u]))

        return D

    def solve_multi_start_nn_2opt(self, nodes=None, must_visit=None):
        """Return a tour and cost using Multi-start Nearest-Neighbor + 2-opt heuristic.

        This is fast, deterministic for a given set of starts, and gives good-quality tours for metric TSPs.
        """
        if nodes is not None:
            self.astar.nodes = nodes
        else:
            self.astar.load_data()

        # Load full map data (nodes positions and adjacency). The `nodes` argument
        # is interpreted as the list of location IDs we want to build a TSP for
        # (typically a much smaller subset than the full map). We always call
        # load_data() so adjacency and coordinates are available to A*.
        self.astar.load_data()

        # Support a `must_visit` list of required nodes. If provided, take the
        # union with `nodes` (if any) so the solver can use extra nodes for
        # connectivity between required locations.
        if must_visit is not None:
            if nodes is not None:
                nodes_list = list(dict.fromkeys(list(nodes) + list(must_visit)))
            else:
                nodes_list = list(dict.fromkeys(list(must_visit)))
        else:
            # `nodes` should be an iterable of node ids (strings). Use these as
            # the TSP-relevant nodes.
            if nodes is not None:
                nodes_list = list(nodes)
            else:
                # Default: use all loaded nodes (backwards-compatible)
                nodes_list = list(self.astar.nodes.keys())

        # Build pairwise shortest-paths only among `nodes_list` by invoking
        # the multi-target A* from each node and restricting targets to the
        # nodes_list. This avoids computing all-pairs on the full map.
        D = {u: {v: float('inf') for v in nodes_list} for u in nodes_list}
        compact_sp_graph = {u: {} for u in nodes_list}

        total = len(nodes_list)
        for i, u in enumerate(nodes_list):
            if u not in self.astar.nodes:
                raise ValueError(f"TSP node {u!r} not present in loaded map")
            t0 = time.time()
            res = self.astar.multipleTarget_astar(u, targets=nodes_list)
            t1 = time.time()
            if i < 5 or (i + 1) % 50 == 0 or i == total - 1:
                print(f"computed pairwise from {i+1}/{total} nodes (src={u}) in {t1 - t0:.3f}s")

            for v in nodes_list:
                info = res.get(v)
                if info is None:
                    cost = float('inf')
                else:
                    cost = float(info.get('cost', float('inf')))
                D[u][v] = cost
                # keep full info for path expansion later
                compact_sp_graph[u][v] = info if info is not None else {"path": None, "cost": float('inf')}

        # Symmetrize to metric: D[u][v] = min(D[u][v], D[v][u])
        for u in nodes_list:
            for v in nodes_list:
                if u == v:
                    D[u][v] = 0.0
                else:
                    D[u][v] = float(min(D[u][v], D[v][u]))

        # Find mutually-reachable undirected adjacency among chosen nodes
        INF = float('inf')
        adj_mutual = {u: set() for u in nodes_list}
        for u in nodes_list:
            for v in nodes_list:
                if u == v:
                    continue
                if D[u][v] != INF and D[v][u] != INF:
                    adj_mutual[u].add(v)

        # Connected components on the undirected mutual graph
        seen = set()
        components = []
        for u in nodes_list:
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
            raise ValueError('No mutually-reachable components found among TSP nodes')

        components.sort(key=len, reverse=True)
        largest = components[0]
        if len(largest) < 2:
            raise ValueError('Insufficient mutually-reachable TSP nodes (need at least 2)')

        if len(largest) < len(nodes_list):
            print(f"Graph contains unreachable pairs; restricting TSP to {len(largest)} nodes out of {len(nodes_list)}")

        chosen_nodes = list(largest)

        # Restrict D and compact_sp_graph to chosen_nodes
        D = {u: {v: D[u][v] for v in chosen_nodes} for u in chosen_nodes}
        sp_graph = {u: {v: compact_sp_graph[u][v] for v in chosen_nodes} for u in chosen_nodes}

        # For the remainder of the method, operate on the largest mutually-
        # reachable component (chosen_nodes). This yields a compact metric that
        # A* returned for most pairs and avoids attempting NN/2-opt on nodes
        # that are mutually unreachable.
        nodes_list = list(chosen_nodes)
        print(f"Using {len(nodes_list)} mutually-reachable nodes for TSP")

        # If caller specified `must_visit`, ensure all required nodes are in the
        # chosen_nodes component; otherwise the requirement cannot be satisfied.
        if must_visit is not None:
            missing_required = [n for n in must_visit if n not in nodes_list]
            if missing_required:
                raise ValueError(f"Cannot satisfy required nodes: {missing_required[:5]} (not in mutually-reachable component)")

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
            print("starting NN from %s", s)
            t = nearest_neighbor(s)
            t = two_opt(t)
            c = tour_cost(t)
            print("start %s produced tour cost %.3f", s, c)
            if c < best_cost:
                best_cost = c
                best_tour = t

        print("best compact tour cost=%.3f, nodes=%d", best_cost, len(D))

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
    # tsp.astar.load_data()
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