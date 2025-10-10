import heapq
import math
from typing import Dict, Tuple, List, Optional
import xml.etree.ElementTree as ET
import os
from app.services.XMLParser import XMLParser


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

    def load_data(self, xml_file_path: str = None):
        """
        Charge les données d'un fichier XML en utilisant XMLParser.
        Si aucun fichier n'est spécifié, utilise un fichier par défaut.
        """
        if xml_file_path is None:
            # Utilise un fichier XML par défaut depuis le répertoire du projet
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(current_dir, "..", "..", "..", "..")
            xml_file_path = os.path.join(project_root, "fichiersXMLPickupDelivery", "petitPlan.xml")
        
        try:
            # Lire le contenu du fichier XML
            with open(xml_file_path, 'r', encoding='utf-8') as file:
                xml_content = file.read()
            
            # Parser les données avec XMLParser
            map_data = XMLParser.parse_map(xml_content)
            
            # Construire self.nodes à partir des intersections
            self.nodes = {}
            for intersection in map_data.intersections:
                # Utiliser (longitude, latitude) comme coordonnées (x, y)
                self.nodes[intersection.id] = (intersection.longitude, intersection.latitude)
            
            # Construire self.adj à partir des segments de route
            self.adj = {}
            for segment in map_data.road_segments:
                # XMLParser retourne start/end comme des strings (IDs), pas des objets Intersection
                start_id = segment.start  # C'est déjà un string ID
                end_id = segment.end      # C'est déjà un string ID
                
                # Vérifier que les nœuds source et destination existent
                if start_id in self.nodes and end_id in self.nodes:
                    if start_id not in self.adj:
                        self.adj[start_id] = {}
                    
                    # Utiliser la longueur du segment comme coût
                    cost = float(segment.length_m)
                    
                    # Si il y a déjà un arc entre ces nœuds, garder le plus court
                    existing_cost = self.adj[start_id].get(end_id)
                    if existing_cost is None or cost < existing_cost:
                        self.adj[start_id][end_id] = cost
            
            print(f"Données chargées: {len(self.nodes)} nœuds, {sum(len(adj) for adj in self.adj.values())} arcs")
            
        except FileNotFoundError:
            print(f"Fichier XML non trouvé: {xml_file_path}")
        except Exception as e:
            print(f"Erreur lors du chargement du fichier XML: {e}")

  

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
        Pour les tests seulement (temporaire).

        Charge les données depuis un fichier XML via XMLParser, calcule tous les plus courts 
        chemins via multipleTarget_astar, affiche les résultats et retourne le dictionnaire obtenu.
        """
        if not self.nodes:
            self.load_data()

        result = self.compute_shortest_paths_graph()

        def _sort_key(k: str):
            try:
                return int(k)
            except Exception:
                return k

        # Afficher seulement un échantillon pour éviter une sortie trop longue
        sorted_sources = sorted(result.keys(), key=_sort_key)
        max_display = min(5, len(sorted_sources))  # Limiter à 5 sources max
        
        print(f"=== Résultats A* (affichage des {max_display} premiers nœuds sur {len(sorted_sources)}) ===")
        for i, src in enumerate(sorted_sources[:max_display]):
            print(f"\nDepuis {src}:")
            tgt_map = result[src]
            sorted_targets = sorted(tgt_map.items(), key=lambda it: _sort_key(it[0]))
            max_targets = min(5, len(sorted_targets))  # Limiter à 5 destinations max
            
            for j, (tgt, info) in enumerate(sorted_targets[:max_targets]):
                path = info.get("path")
                cost = info.get("cost", float("inf"))
                if path is None:
                    print(f"  vers {tgt}: inaccessible (cost=inf)")
                else:
                    print(f"  vers {tgt}: cost={cost:.2f}m, path={' -> '.join(path)}")
            
            if len(sorted_targets) > max_targets:
                print(f"  ... et {len(sorted_targets) - max_targets} autres destinations")
        
        if len(sorted_sources) > max_display:
            print(f"\n... et {len(sorted_sources) - max_display} autres sources")
            
        return result
        
    