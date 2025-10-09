import heapq
import math
from typing import Dict, Tuple, List, Optional
import xml.etree.ElementTree as ET


class Astar:
    def __init__(self, alpha: float = 0.5):
        """
        alpha: mélange entre euclidienne et manhattan pour l'heuristique
               h = alpha * euclidienne + (1 - alpha) * manhattan
               (0 <= alpha <= 1)

        L'initialisation ne charge pas automatiquement les données.
        Utiliser load_data() pour remplir self.nodes et self.adj.
        """
        self.alpha = float(alpha)
        self.nodes: Dict[str, Tuple[float, float]] = {}
        self.adj: Dict[str, Dict[str, float]] = {}

        # structures optionnelles utilisées par load_data()
        self.edges = []

    def load_data(self):
        """
        Initialise des données factices (exemples) dans self.nodes et self.edges,
        puis construit self.adj (matrice d'adjacence avec coûts).
        """
        self.nodes = {
            "1": (0.0, 0.0),
            "2": (1.0, 2.0),
            "3": (4.0, 2.0),
            "4": (3.5, -1.0),
            "5": (-1.0, 1.0),
            "6": (2.0, 0.5),
            "7": (0.5, -2.0),
            "8": (5.5, 0.0),
            "9": (6.0, 2.5),
            "10": (-2.0, 0.5),
            "11": (1.0, 4.0),
        }

        self.edges = [
            ("1", "2", "euclid", 1.0, 0.0),
            ("2", "3", "euclid", 1.0, 0.0),
            ("3", "8", "euclid", 1.0, 0.0),
            ("8", "9", "euclid", 1.0, 0.0),
            ("9", "3", "euclid", 1.2, 0.3),
            ("2", "11", "euclid", 1.0, 0.0),
            ("11", "2", "euclid", 1.0, 0.0),
            ("1", "7", "euclid", 1.1, 0.0),
            ("7", "4", "euclid", 1.3, 0.5),
            ("4", "3", "euclid", 1.0, 0.0),
            ("5", "1", "euclid", 1.2, 0.2),
            ("10", "5", "euclid", 1.0, 0.0),
            ("5", "10", "euclid", 1.0, 0.0),
            ("6", "2", "manhattan", 1.0, 0.0),
            ("2", "6", "euclid", 0.9, 0.0),
            ("6", "4", "euclid", 1.0, 0.0),
            ("4", "8", "euclid", 1.1, 0.2),
            ("8", "4", "euclid", 1.0, 0.0),
            ("3", "6", "mixed", 0.8, 0.0),
            ("6", "11", "manhattan", 1.0, 0.0),
            ("11", "6", "euclid", 1.1, 0.0),
            ("7", "1", "euclid", 1.5, 0.7),
            ("9", "8", "euclid", 1.0, 0.0),
            ("10", "1", "euclid", 1.3, 0.2),
            ("5", "2", "mixed", 0.9, 0.1),
        ]

        self.adj = {}
        for src, dst, metric, factor, penalty in self.edges:
            # compute cost for this directed edge
            a = self.nodes[src]
            b = self.nodes[dst]

            if metric == "euclid":
                base = self._euclid(a, b)
            elif metric == "manhattan":
                base = self._manhattan(a, b)
            elif metric == "mixed":
                base = self.alpha * self._euclid(a, b) + (1.0 - self.alpha) * self._manhattan(a, b)
            else:
                base = self._euclid(a, b)

            cost = round(base * float(factor) + float(penalty), 3)

            # add src -> dst
            self.adj.setdefault(src, {})
            prev = self.adj[src].get(dst)
            if prev is None or cost < prev:
                self.adj[src][dst] = cost

            # also add a reverse edge dst -> src with the same metric parameters
            # compute cost for reverse (using swapped points and same factor/penalty)
            a_rev = self.nodes[dst]
            b_rev = self.nodes[src]
            if metric == "euclid":
                base_rev = self._euclid(a_rev, b_rev)
            elif metric == "manhattan":
                base_rev = self._manhattan(a_rev, b_rev)
            elif metric == "mixed":
                base_rev = self.alpha * self._euclid(a_rev, b_rev) + (1.0 - self.alpha) * self._manhattan(a_rev, b_rev)
            else:
                base_rev = self._euclid(a_rev, b_rev)

            cost_rev = round(base_rev * float(factor) + float(penalty), 3)
            self.adj.setdefault(dst, {})
            prev_rev = self.adj[dst].get(src)
            if prev_rev is None or cost_rev < prev_rev:
                self.adj[dst][src] = cost_rev

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
        Trouve les plus courts chemins depuis idNode vers tous les autres noeuds.
        Retourne un dict:
          target -> {'path': [idNode, ..., target] or None, 'cost': float('inf') if inaccessible}
        """
        if idNode not in self.nodes:
            raise ValueError(f"start node {idNode!r} not in graph")

        # ensemble des objectifs (tous les noeuds sauf le départ)
        goals = set(self.nodes.keys()) - {idNode}
        if not goals:
            return {}

        # utilitaires
        def reconstruct_path(came_from: Dict[str, str], current: str) -> List[str]:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        # A* multi-cible: heuristique admissible = min heuristique vers les objectifs restants
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

            # si on est sur un objectif non encore trouvé, le mémoriser
            if node in remaining_goals:
                path = reconstruct_path(came_from, node)
                found[node] = {"path": path, "cost": g}
                remaining_goals.remove(node)
                # si tous trouvés, on peut sortir
                if len(found) == len(goals):
                    break

            # parcourir voisins
            for nbr, cost in self.adj.get(node, {}).items():
                tentative_g = g + float(cost)
                if tentative_g < g_score.get(nbr, float("inf")):
                    g_score[nbr] = tentative_g
                    came_from[nbr] = node
                    # heuristique = min distance to any remaining goal (admissible)
                    if remaining_goals:
                        h = min(self.heuristic(nbr, gg) for gg in remaining_goals)
                    else:
                        h = 0.0
                    heapq.heappush(heap, (tentative_g + h, tentative_g, nbr))

        # construire résultat: pour cibles non atteintes, mettre None / inf
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
        For testing only (temporary).

        Loads dummy data, computes all shortest paths via multipleTarget_astar,
        prints the results and returns the obtained dictionary.
        """
        if not self.nodes:
            self.load_data()

        result = self.compute_shortest_paths_graph()

        def _sort_key(k: str):
            try:
                return int(k)
            except Exception:
                return k

        for src in sorted(result.keys(), key=_sort_key):
            print(f"From {src}:")
            tgt_map = result[src]
            for tgt, info in sorted(tgt_map.items(), key=lambda it: _sort_key(it[0])):
                path = info.get("path")
                cost = info.get("cost", float("inf"))
                if path is None:
                    print(f"  to {tgt}: unreachable (cost=inf)")
                else:
                    print(f"  to {tgt}: cost={cost}, path={' -> '.join(path)}")
        return result
        
       
        
        
        
    