"""TSP Core Utilities: Core functions for TSP operations."""

import os
import sys
import time
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from itertools import permutations
from dataclasses import dataclass

import networkx as nx

# Ensure backend root is on sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.utils.TSP.TSP_networkx import TSP
from app.services.XMLParser import XMLParser


def build_sp_graph(G_map: nx.DiGraph, nodes_list: List[str]) -> Dict:
    """Build shortest path graph for given nodes."""
    sp_graph = {}
    for src in nodes_list:
        try:
            lengths, paths = nx.single_source_dijkstra(G_map, src, weight="weight")
        except:
            lengths = {}
            paths = {}
        sp_graph[src] = {}
        for tgt in nodes_list:
            if tgt == src:
                sp_graph[src][tgt] = {"path": [src], "cost": 0.0}
            else:
                sp_graph[src][tgt] = {"path": paths.get(tgt) if isinstance(paths, dict) else None, "cost": lengths.get(tgt, float("inf")) if isinstance(lengths, dict) else float("inf")}
    return sp_graph


def tour_cost(tour: List[str], sp_graph: Dict) -> float:
    """Calculate total cost of a tour."""
    total = 0.0
    for i in range(len(tour) - 1):
        u, v = tour[i], tour[i + 1]
        cost = sp_graph.get(u, {}).get(v, float("inf"))
        total += cost
    return total


def generate_valid_tours(pd_pairs: List[Tuple[str, str]], start_node: Optional[str] = None):
    """Generate valid tours respecting pickup-delivery constraints."""
    all_nodes = []
    delivery_to_pickup = {d: p for p, d in pd_pairs}
    for p, d in pd_pairs:
        all_nodes.extend([p, d])
    for perm in permutations(all_nodes):
        node_positions = {node: idx for idx, node in enumerate(perm)}
        if all(node_positions[pickup] < node_positions[delivery] for delivery, pickup in delivery_to_pickup.items()):
            tour = list(perm)
            if start_node:
                tour = [start_node] + tour + [start_node]
            else:
                tour += [tour[0]]
            yield tour


def is_valid_tour(tour: List[str], pd_pairs: List[Tuple[str, str]], start_node: Optional[str]) -> bool:
    """Check if a tour is valid."""
    if start_node and tour[0] != start_node:
        return False
    pos = {node: idx for idx, node in enumerate(tour)}
    for pickup, delivery in pd_pairs:
        if pickup not in pos or delivery not in pos or pos[pickup] >= pos[delivery]:
            return False
    return True


def generate_all_valid_tours(pd_pairs: List[Tuple[str, str]], start_node: Optional[str] = None):
    """Generate all valid tours (alternative implementation)."""
    all_nodes = []
    delivery_to_pickup = {d: p for p, d in pd_pairs}
    for p, d in pd_pairs:
        all_nodes.extend([p, d])
    for perm in permutations(all_nodes):
        node_positions = {node: idx for idx, node in enumerate(perm)}
        if all(node_positions[pickup] < node_positions[delivery] for delivery, pickup in delivery_to_pickup.items()):
            tour = list(perm)
            if start_node:
                tour = [start_node] + tour + [start_node]
            else:
                tour += [tour[0]]
            yield tour


def compute_optimal(map_path: str, req_path: str, max_nodes: int = 0, start_node: Optional[str] = None) -> Tuple[List[str], float]:
    """Compute optimal tour using brute force."""
    tsp = TSP()
    G_map, _ = tsp._build_networkx_map_graph(map_path)
    with open(req_path, 'r', encoding='utf-8') as f:
        deliveries = XMLParser.parse_deliveries(f.read())
    pd_pairs = [(d.pickup_addr, d.delivery_addr) for d in deliveries]
    if max_nodes > 0:
        pd_pairs = pd_pairs[:max_nodes // 2]
    all_nodes = []
    for p, d in pd_pairs:
        if p not in all_nodes:
            all_nodes.append(p)
        if d not in all_nodes:
            all_nodes.append(d)
    if start_node and start_node not in all_nodes:
        all_nodes.append(start_node)
    sp_graph = {}
    for u in all_nodes:
        sp_graph[u] = {}
        for v in all_nodes:
            if u != v:
                try:
                    cost = nx.shortest_path_length(G_map, u, v, weight="weight")
                    sp_graph[u][v] = cost
                except:
                    sp_graph[u][v] = float("inf")
    best_tour = None
    best_cost = float("inf")
    for tour in generate_valid_tours(pd_pairs, start_node):
        cost = tour_cost(tour, sp_graph)
        if cost < best_cost:
            best_cost = cost
            best_tour = tour
    return best_tour or [], best_cost if best_tour else float("inf")


def compute_optimal_brute_force(map_path: str, req_path: str, max_nodes: int = 0, start_node: Optional[str] = None) -> Tuple[List[str], float]:
    """Compute optimal tour using brute force (alternative implementation)."""
    tsp = TSP()
    G_map, _ = tsp._build_networkx_map_graph(map_path)
    with open(req_path, 'r', encoding='utf-8') as f:
        deliveries = XMLParser.parse_deliveries(f.read())
    pd_pairs = [(d.pickup_addr, d.delivery_addr) for d in deliveries]
    if max_nodes > 0:
        max_deliveries = max_nodes // 2
        pd_pairs = pd_pairs[:max_deliveries]
    all_nodes = []
    for p, d in pd_pairs:
        if p not in all_nodes:
            all_nodes.append(p)
        if d not in all_nodes:
            all_nodes.append(d)
    if start_node and start_node not in all_nodes:
        all_nodes.append(start_node)
    sp_graph = {}
    for u in all_nodes:
        sp_graph[u] = {}
        for v in all_nodes:
            if u != v:
                try:
                    cost = nx.shortest_path_length(G_map, u, v, weight="weight")
                    sp_graph[u][v] = cost
                except:
                    sp_graph[u][v] = float("inf")
    best_tour = None
    best_cost = float("inf")
    count = 0
    start_time = time.time()
    for tour in generate_all_valid_tours(pd_pairs, start_node):
        count += 1
        cost = tour_cost(tour, sp_graph)
        if cost < best_cost:
            best_cost = cost
            best_tour = tour
    elapsed = time.time() - start_time
    if best_tour:
        save_cached_optimal_tour(map_path, req_path, best_tour, best_cost, count, elapsed)
        return best_tour, best_cost
    return [], float("inf")


def expand_path(path: List[str], G_map: nx.DiGraph) -> Tuple[List[str], float]:
    """Expand compact path to full path with intermediate nodes."""
    if not path or len(path) < 2:
        return path, 0.0
    expanded = []
    total_cost = 0.0
    for i in range(len(path) - 1):
        src, tgt = path[i], path[i + 1]
        try:
            segment = nx.shortest_path(G_map, src, tgt, weight="weight")
            segment_cost = nx.shortest_path_length(G_map, src, tgt, weight="weight")
            if i == 0:
                expanded.extend(segment)
            else:
                expanded.extend(segment[1:])
            total_cost += segment_cost
        except:
            return [], float("inf")
    return expanded, total_cost


def expand_manual_path(path: List[str], G_map: nx.DiGraph) -> Tuple[List[str], float]:
    """Expand manual path (alias for expand_path)."""
    return expand_path(path, G_map)


def calculate_path_cost(path: List[str], sp_graph: Optional[Dict] = None, G_map: Optional[nx.DiGraph] = None) -> float:
    """Calculate cost of a path."""
    if not path or len(path) < 2:
        return 0.0
    total = 0.0
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        if sp_graph and u in sp_graph and v in sp_graph[u]:
            cost = sp_graph[u][v].get("cost", float("inf"))
        elif G_map:
            try:
                cost = nx.shortest_path_length(G_map, u, v, weight="weight")
            except:
                cost = float("inf")
        else:
            cost = float("inf")
        total += cost
    return total


def format_path(path: List[str], max_display: int = 20) -> str:
    """Format path for display."""
    if not path:
        return "<empty>"
    if len(path) <= max_display:
        return " -> ".join(path)
    head = " -> ".join(path[:max_display // 2])
    tail = " -> ".join(path[-(max_display // 2):])
    return f"{head} -> ... ({len(path) - max_display} nodes) ... -> {tail}"


def validate_path(path: List[str], valid_nodes: set) -> Tuple[bool, str]:
    """Validate that all nodes in path are valid."""
    invalid = [n for n in path if n not in valid_nodes]
    if invalid:
        return False, f"Invalid nodes: {', '.join(invalid[:5])}"
    return True, ""


def input_manual_path(valid_nodes: set) -> List[str]:
    """Get manual path input from user."""
    print("\nEnter path as space/comma/-> separated node IDs. Press Enter to skip.")
    while True:
        inp = input("Path: ").strip()
        if not inp:
            return []
        path = inp.replace(",", " ").replace("->", " ").split()
        path = [p.strip() for p in path if p.strip()]
        is_valid, err = validate_path(path, valid_nodes)
        if is_valid:
            return path
        print(f"Error: {err}")


# Caching functions
def compute_file_hash(filepath: str) -> str:
    """Compute hash of file for caching."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()[:16]


def get_cache_key(map_path: str, req_path: str) -> str:
    """Generate cache key for optimal tour."""
    map_hash = compute_file_hash(map_path)
    req_hash = compute_file_hash(req_path)
    map_name = Path(map_path).stem
    req_name = Path(req_path).stem
    return f"{map_name}_{req_name}_{map_hash}_{req_hash}"


def load_cached_optimal_tour(map_path: str, req_path: str) -> Optional[Dict]:
    """Load cached optimal tour."""
    try:
        cache_key = get_cache_key(map_path, req_path)
        cache_path = Path(__file__).parent / "data" / "optimal_tours" / f"{cache_key}_optimal.json"
        if cache_path.exists():
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def save_cached_optimal_tour(map_path: str, req_path: str, tour: list, cost: float, num_permutations: int, computation_time: float) -> None:
    """Save optimal tour to cache."""
    try:
        cache_key = get_cache_key(map_path, req_path)
        cache_dir = Path(__file__).parent / "data" / "optimal_tours"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"{cache_key}_optimal.json"
        cache_data = {
            "tour": tour, "cost": cost, "num_nodes": len(tour), "num_permutations_checked": num_permutations,
            "computation_time_s": computation_time, "computed_at": time.time(),
            "map_file": os.path.basename(map_path), "req_file": os.path.basename(req_path), "solver": "brute_force"
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
    except Exception:
        pass