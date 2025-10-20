import heapq
import os
import sys
from typing import Dict, List, Optional, Any, cast
from types import SimpleNamespace

from app.models.schemas import Tour

try:
    import networkx as nx
    from networkx.algorithms import matching as nx_matching
except Exception:
    raise




class TSP:
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

    def solve(self, tour: Tour):
        """Construct a paired tour (pickup->delivery) then improve it while
        preserving pickup-before-delivery precedence. This approach builds an
        initial route by visiting each pickup followed immediately by its
        delivery, selecting the next pickup greedily by metric distance from
        the current location. After the greedy construction we run a
        constrained 2-opt local search that only accepts changes which keep
        every pickup before its corresponding delivery.

        The function uses NetworkX shortest-paths for pairwise distances and
        the existing metric builder `_build_metric_complete_graph` to obtain
        symmetric metric distances between the involved nodes.
        """
        # Extract pickup-delivery pairs from the provided Tour object
        pd_pairs = list(tour.deliveries)
        if not pd_pairs:
            return [], 0.0

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

        # Helper: compute compact tour cost on the metric graph G
        def tour_cost(seq: List[str]) -> float:
            if not seq or len(seq) < 2:
                return 0.0
            s = 0.0
            for i in range(len(seq) - 1):
                u, v = seq[i], seq[i + 1]
                s += G[u][v]["weight"]
            return s

        # Build initial greedy paired tour: start from first pickup
        start_p, start_d = pd_pairs[0]
        if start_p not in nodes_list or start_d not in nodes_list:
            # choose any available pickup/delivery pair present in nodes_list
            found = False
            for p, d in pd_pairs:
                if p in nodes_list and d in nodes_list:
                    start_p, start_d = p, d
                    found = True
                    break
            if not found:
                return [], 0.0

        # restrict to pickups/deliveries present in G
        pickups = [p for p, _ in pd_pairs]
        deliveries = [d for _, d in pd_pairs]
        remaining_pickups = [p for p in pickups if p in G.nodes()]
        pair_of = {p: d for p, d in pd_pairs}

        current = start_p
        tour_seq: List[str] = []
        # visit start pickup and its delivery
        tour_seq.append(start_p)
        tour_seq.append(start_d)
        if start_p in remaining_pickups:
            remaining_pickups.remove(start_p)
        current = start_d

        # greedily choose next pickup as the nearest (in metric G) to current
        INF = float("inf")
        while remaining_pickups:
            best = None
            best_cost = INF
            for p in remaining_pickups:
                try:
                    c = G[current][p]["weight"] if current in G and p in G[current] else INF
                except Exception:
                    c = INF
                if c < best_cost:
                    best_cost = c
                    best = p
            if best is None:
                # no reachable remaining pickup; append them in arbitrary order
                for p in remaining_pickups:
                    tour_seq.append(p)
                    tour_seq.append(pair_of.get(p, p))
                break
            # append pickup and its delivery
            tour_seq.append(best)
            tour_seq.append(pair_of[best])
            remaining_pickups.remove(best)
            current = pair_of[best]

        # close tour
        if tour_seq and tour_seq[0] != tour_seq[-1]:
            tour_seq.append(tour_seq[0])

        total = tour_cost(tour_seq)

        # Constrained 2-opt local search: try reversing segments while ensuring
        # every pickup remains before its delivery.
        # Work on the core (without final duplicated node) to make index checks easier.
        closed = len(tour_seq) >= 2 and tour_seq[0] == tour_seq[-1]
        core = tour_seq[:-1] if closed else list(tour_seq)

        # Build quick lookup for precedence
        pickup_set = set(p for p, _ in pd_pairs if p in nodes_list)
        delivery_map = {d: p for p, d in pd_pairs if p in nodes_list and d in nodes_list}

        improved = True
        max_iters = 500
        iters = 0
        n = len(core)
        while improved and iters < max_iters:
            improved = False
            iters += 1
            # try all i<j pairs for 2-opt (skip index 0 to keep start fixed)
            for i in range(1, n - 2):
                for j in range(i + 1, n - 1):
                    # propose reversing core[i:j+1]
                    new_core = core[:i] + list(reversed(core[i : j + 1])) + core[j + 1 :]

                    # check precedence: for every delivery, pickup must come before delivery
                    ok = True
                    for d, p in delivery_map.items():
                        try:
                            idx_p = new_core.index(p)
                            idx_d = new_core.index(d)
                        except ValueError:
                            ok = False
                            break
                        if idx_p >= idx_d:
                            ok = False
                            break
                    if not ok:
                        continue

                    new_seq = new_core + ([new_core[0]] if closed else [])
                    new_cost = tour_cost(new_seq)
                    if new_cost + 1e-9 < total:
                        core = new_core
                        total = new_cost
                        improved = True
                        # restart scanning
                        break
                if improved:
                    break

        # re-close tour
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
