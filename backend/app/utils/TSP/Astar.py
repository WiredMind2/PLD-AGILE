import heapq
import math
from typing import Dict, Tuple, List, Optional
import xml.etree.ElementTree as ET
import os
import time
import logging
try:
    from tqdm import tqdm
except Exception:
    # fallback: identity wrapper if tqdm is not installed
    def tqdm(x, **kwargs):
        return x
try:
    from app.services.XMLParser import XMLParser
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from services.XMLParser import XMLParser


class Astar:
    def __init__(self, alpha: float = 0.5):
        """
        alpha: blend between Euclidean and Manhattan for the heuristic
               h = alpha * euclidean + (1 - alpha) * manhattan
               (0 <= alpha <= 1)

        Initialization does not automatically load data.
        Use load_data() to populate self.nodes and self.adj.
        """
        self.alpha = float(alpha)
        self.nodes: Dict[str, Tuple[float, float]] = {}
        self.adj: Dict[str, Dict[str, float]] = {}

        # optional structures used by load_data()
        self.edges = []

    def load_data(self, xml_file_path: Optional[str] = None):
        """
        Load data from an XML file using XMLParser.
        If no file is specified, use a default file.
        """
        if xml_file_path is None:
            # Use a default XML file from the project directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(current_dir, "..", "..", "..", "..")
            xml_file_path = os.path.join(project_root, "fichiersXMLPickupDelivery", "petitPlan.xml")
        
        try:
            # Read the XML file content
            with open(xml_file_path, 'r', encoding='utf-8') as file:
                xml_content = file.read()
            
            # Parse data with XMLParser
            map_data = XMLParser.parse_map(xml_content)
            
            # Build self.nodes from intersections
            self.nodes = {}
            for intersection in map_data.intersections:
                # Use (longitude, latitude) as coordinates (x, y)
                self.nodes[intersection.id] = (intersection.longitude, intersection.latitude)
            
            # Build self.adj from road segments
            self.adj = {}
            for segment in map_data.road_segments:
                # start/end may be either a string ID or an Intersection object.
                start_id = getattr(segment.start, 'id', segment.start)
                end_id = getattr(segment.end, 'id', segment.end)

                # Normalize to strings
                try:
                    start_id = str(start_id)
                    end_id = str(end_id)
                except Exception:
                    # Skip malformed segment
                    continue

                # Verify that source and destination nodes exist
                if start_id in self.nodes and end_id in self.nodes:
                    if start_id not in self.adj:
                        self.adj[start_id] = {}

                    # Use the segment length as the cost
                    cost = float(segment.length_m)

                    # If there's already an edge between these nodes, keep the shortest
                    existing_cost = self.adj[start_id].get(end_id)
                    if existing_cost is None or cost < existing_cost:
                        self.adj[start_id][end_id] = cost
            
            print(f"Data loaded: {len(self.nodes)} nodes, {sum(len(adj) for adj in self.adj.values())} edges")
            print("Data loaded: %d nodes, %d edges", len(self.nodes), sum(len(adj) for adj in self.adj.values()))
            
        except FileNotFoundError:
            print(f"XML file not found: {xml_file_path}")
        except Exception as e:
            print(f"Error while loading XML file: {e}")

    def _euclid(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def _manhattan(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def heuristic(self, n1: str, n2: str) -> float:
        p1 = self.nodes[n1]
        p2 = self.nodes[n2]
        return self.alpha * self._euclid(p1, p2) + (1.0 - self.alpha) * self._manhattan(p1, p2)

    def multipleTarget_astar(self, idNode, targets: Optional[List[str]] = None):
        """
        Find shortest paths from idNode to all other nodes.
        Returns a dict:
          target -> {'path': [idNode, ..., target] or None, 'cost': float('inf') if unreachable}
        """
        if idNode not in self.nodes:
            raise ValueError(f"start node {idNode!r} not in graph")

        # set of goals (either provided targets or all nodes except the start)
        if targets is not None:
            goals = set(targets) - {idNode}
        else:
            goals = set(self.nodes.keys()) - {idNode}
        if not goals:
            return {}

        # helpers
        def reconstruct_path(came_from: Dict[str, str], current: str) -> List[str]:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        # Local references for speed
        nodes_local = self.nodes
        adj_local = self.adj
        heuristic_fn = self.heuristic

        # Multi-target A*: precompute a min-heuristic to any goal for each node.
        # Using the min over all goals (static) is admissible and avoids repeated
        # computation while remaining_goals shrinks.
        goals_list = list(goals)
        h_min: Dict[str, float] = {}
        # Use tqdm for a visible progress bar when available (safe fallback otherwise)
        for n in tqdm(nodes_local, desc="precompute h_min", leave=False):
            # compute min heuristic to any goal
            best = float('inf')
            p1 = nodes_local.get(n)
            if p1 is None:
                h_min[n] = best
                continue
            for g in goals_list:
                # skip computing heuristic to itself (not a goal)
                try:
                    val = heuristic_fn(n, g)
                except Exception:
                    val = float('inf')
                if val < best:
                    best = val
            h_min[n] = best

        remaining_goals = set(goals_list)
        g_score: Dict[str, float] = {idNode: 0.0}
        came_from: Dict[str, str] = {}
        found: Dict[str, Dict] = {}

        heap = []
        # f, g, node
        h0 = h_min.get(idNode, 0.0)
        heapq.heappush(heap, (h0, 0.0, idNode))

        t_start_search = time.perf_counter()
        # Main search loop
        while heap and len(found) < len(goals_list):
            f, g, node = heapq.heappop(heap)
            prev_best = g_score.get(node)
            if prev_best is None or g != prev_best and g > prev_best:
                # outdated entry
                continue

            # if we are on a goal not yet found, record it
            if node in remaining_goals:
                path = reconstruct_path(came_from, node)
                found[node] = {"path": path, "cost": g}
                remaining_goals.remove(node)
                # if all found, we can stop
                if len(found) == len(goals_list):
                    break

            # explore neighbors
            nbrs = adj_local.get(node)
            if not nbrs:
                continue
            for nbr, cost in nbrs.items():
                tentative_g = g + float(cost)
                prev = g_score.get(nbr, float('inf'))
                if tentative_g < prev:
                    g_score[nbr] = tentative_g
                    came_from[nbr] = node
                    # heuristic = precomputed min heuristic (admissible)
                    h = h_min.get(nbr, 0.0)
                    heapq.heappush(heap, (tentative_g + h, tentative_g, nbr))

        # build result: for unreachable targets, put None / inf
        result: Dict[str, Dict] = {}
        for tgt in goals_list:
            if tgt in found:
                result[tgt] = found[tgt]
            else:
                result[tgt] = {"path": None, "cost": float("inf")}
        t_end_search = time.perf_counter()
        print(f"multipleTarget_astar: start={idNode} found={sum(1 for v in result.values() if v['path'] is not None)}/{len(result)} time={t_end_search - t_start_search:.3f}s")
        return result
        

    def compute_shortest_paths_graph(self) -> Dict[str, Dict[str, Dict]]:
        """
        Compute the shortest paths graph for every node in self.nodes using multipleTarget_astar.
        Returns a dict mapping source -> (dict returned by multipleTarget_astar for that source)
        """
        if not self.nodes:
            return {}
        result: Dict[str, Dict[str, Dict]] = {}
        sources = list(self.nodes.keys())
        total = len(sources)
        for i, src in enumerate(sources):
            t0 = time.perf_counter()
            result[src] = self.multipleTarget_astar(src)
            t1 = time.perf_counter()
            # Log progress every 50 sources or for the first/last
            if i < 5 or (i + 1) % 50 == 0 or i == total - 1:
                print(f"compute_shortest_paths_graph: computed {i + 1}/{total} sources (last src={src}) in {t1 - t0:.3f}s")
        return result

    def print_for_test(self) -> Dict[str, Dict[str, Dict]]:
        """
        For tests only (temporary).

        Loads data from an XML file via XMLParser if needed, computes all shortest
        paths with multipleTarget_astar, prints results and returns the dictionary.
        """
        if not self.nodes:
            self.load_data()

        result = self.compute_shortest_paths_graph()

        def _sort_key(k: str):
            try:
                return int(k)
            except Exception:
                return k

        # Print only a sample to avoid excessively long output
        sorted_sources = sorted(result.keys(), key=_sort_key)
        max_display = min(5, len(sorted_sources))  # limit to 5 sources max
        
        print(f"=== A* Results (showing first {max_display} nodes out of {len(sorted_sources)}) ===")
        for i, src in enumerate(sorted_sources[:max_display]):
            print(f"\nFrom {src}:")
            tgt_map = result[src]
            sorted_targets = sorted(tgt_map.items(), key=lambda it: _sort_key(it[0]))
            max_targets = min(5, len(sorted_targets))  # limit to 5 destinations max
            
            for j, (tgt, info) in enumerate(sorted_targets[:max_targets]):
                path = info.get("path")
                cost = info.get("cost", float("inf"))
                if path is None:
                    print(f"  to {tgt}: unreachable (cost=inf)")
                else:
                    print(f"  to {tgt}: cost={cost:.2f}m, path={' -> '.join(path)}")
            
            if len(sorted_targets) > max_targets:
                print(f"  ... and {len(sorted_targets) - max_targets} other destinations")
        
        if len(sorted_sources) > max_display:
            print(f"\n... and {len(sorted_sources) - max_display} other sources")
            
        return result
