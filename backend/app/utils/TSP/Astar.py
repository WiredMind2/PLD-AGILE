import heapq
import math
from typing import Dict, Tuple, List, Optional
import xml.etree.ElementTree as ET
import os
from app.services.XMLParser import XMLParser


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

    def load_data(self, xml_file_path: str = None):
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
                # XMLParser returns start/end as strings (IDs), not Intersection objects
                start_id = segment.start  # already a string ID
                end_id = segment.end      # already a string ID
                
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

    def multipleTarget_astar(self, idNode):
        """
        Find shortest paths from idNode to all other nodes.
        Returns a dict:
          target -> {'path': [idNode, ..., target] or None, 'cost': float('inf') if unreachable}
        """
        if idNode not in self.nodes:
            raise ValueError(f"start node {idNode!r} not in graph")

        # set of goals (all nodes except the start)
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

        # Multi-target A*: admissible heuristic = min heuristic to any remaining goal
        remaining_goals = set(goals)
        g_score: Dict[str, float] = {idNode: 0.0}
        came_from: Dict[str, str] = {}
        found: Dict[str, Dict] = {}

        heap = []
        # f, g, node
        h0 = min(self.heuristic(idNode, g) for g in remaining_goals)
        heapq.heappush(heap, (h0, 0.0, idNode))

        while heap and len(found) < len(goals):
            f, g, node = heapq.heappop(heap)
            # outdated entry?
            if g > g_score.get(node, float("inf")):
                continue

            # if we are on a goal not yet found, record it
            if node in remaining_goals:
                path = reconstruct_path(came_from, node)
                found[node] = {"path": path, "cost": g}
                remaining_goals.remove(node)
                # if all found, we can stop
                if len(found) == len(goals):
                    break

            # explore neighbors
            for nbr, cost in self.adj.get(node, {}).items():
                tentative_g = g + float(cost)
                if tentative_g < g_score.get(nbr, float("inf")):
                    g_score[nbr] = tentative_g
                    came_from[nbr] = node
                    # heuristic = min distance to any remaining goal (admissible)
                    if remaining_goals:
                        h = min(self.heuristic(nbr, gg) for gg in remaining_goals)
                    else:
                        h = 0.0
                    heapq.heappush(heap, (tentative_g + h, tentative_g, nbr))

        # build result: for unreachable targets, put None / inf
        result: Dict[str, Dict] = {}
        for tgt in goals:
            if tgt in found:
                result[tgt] = found[tgt]
            else:
                result[tgt] = {"path": None, "cost": float("inf")}
        return result
        

    def compute_shortest_paths_graph(self) -> Dict[str, Dict[str, Dict]]:
        """
        Compute the shortest paths graph for every node in self.nodes using multipleTarget_astar.
        Returns a dict mapping source -> (dict returned by multipleTarget_astar for that source)
        """
        if not self.nodes:
            return {}
        result: Dict[str, Dict[str, Dict]] = {}
        for src in list(self.nodes.keys()):
            result[src] = self.multipleTarget_astar(src)
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
