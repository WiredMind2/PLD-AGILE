"""Compute optimal TSP tour using brute-force exhaustive search.

This script computes the truly optimal tour by trying all valid permutations
of pickup-delivery pairs while respecting precedence constraints (each pickup
must come before its delivery). 

⚠️  WARNING: Exponentially slow! Only practical for small instances (≤8 deliveries).

This is intended for comparison/validation purposes where we need a known
optimal solution to compare against heuristic results.

Usage:
  python tools/compute_optimal_brute_force.py --map PATH --req PATH
  python tools/compute_optimal_brute_force.py --map PATH --req PATH --nodes N

Examples:
  # Compute optimal for small instance
  python tools/compute_optimal_brute_force.py --map fichiersXMLPickupDelivery/petitPlan.xml --req fichiersXMLPickupDelivery/demandePetit1.xml
  
  # Limit to first 3 deliveries (6 nodes) for faster computation
  python tools/compute_optimal_brute_force.py --map petitPlan.xml --req demandePetit1.xml --nodes 6
"""
from __future__ import annotations

import os
import sys
import argparse
import time
from typing import List, Tuple, Dict, Optional, cast
from itertools import permutations

# Ensure backend root is on sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(HERE, '..'))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

import networkx as nx
from app.utils.TSP.TSP_networkx import TSP
from app.services.XMLParser import XMLParser


def compute_pairwise_shortest_paths(G_map: nx.DiGraph, nodes: List[str]) -> Dict[str, Dict[str, Dict]]:
    """Compute shortest paths between all pairs of nodes."""
    sp_graph = {}
    for src in nodes:
        try:
            lengths_raw, paths_raw = nx.single_source_dijkstra(G_map, src, weight='weight')
            lengths = cast(Dict[str, float], lengths_raw) if isinstance(lengths_raw, dict) else {}
            paths = cast(Dict[str, List[str]], paths_raw) if isinstance(paths_raw, dict) else {}
        except Exception:
            lengths = {}
            paths = {}
        
        sp_graph[src] = {}
        for tgt in nodes:
            sp_graph[src][tgt] = {
                'path': [src] if src == tgt else paths.get(tgt),
                'cost': 0.0 if src == tgt else lengths.get(tgt, float('inf'))
            }
    
    return sp_graph


def tour_cost(tour: List[str], sp_graph: Dict) -> float:
    """Calculate total cost of a tour using shortest paths."""
    if not tour or len(tour) < 2:
        return 0.0
    
    total = 0.0
    for i in range(len(tour) - 1):
        u, v = tour[i], tour[i + 1]
        cost = sp_graph.get(u, {}).get(v, {}).get('cost', float('inf'))
        total += cost
    
    return total


def is_valid_tour(tour: List[str], pd_pairs: List[Tuple[str, str]], start_node: Optional[str]) -> bool:
    """Check if a tour respects pickup-before-delivery constraints.
    
    Args:
        tour: List of nodes in visit order
        pd_pairs: List of (pickup, delivery) tuples
        start_node: Optional start node that should be first (and last for closed tours)
    """
    # If start_node is specified, check it's first in the tour
    if start_node is not None:
        if not tour or tour[0] != start_node:
            return False
    
    # Build position index
    pos = {node: idx for idx, node in enumerate(tour)}
    
    # Check each pickup comes before its delivery
    for pickup, delivery in pd_pairs:
        if pickup not in pos or delivery not in pos:
            return False
        if pos[pickup] >= pos[delivery]:
            return False
    
    return True


def generate_all_valid_tours(pd_pairs: List[Tuple[str, str]], start_node: Optional[str] = None):
    """Generate all valid tours respecting pickup-delivery precedence.
    
    This uses a simpler approach: generate all permutations of the nodes,
    then filter for those that respect the precedence constraints.
    
    For small instances this is practical and much simpler to implement correctly.
    """
    # Collect all nodes
    all_nodes = []
    for p, d in pd_pairs:
        all_nodes.append(p)
        all_nodes.append(d)
    
    # Create precedence map: delivery -> pickup
    delivery_to_pickup = {d: p for p, d in pd_pairs}
    
    # Generate all permutations of nodes
    for perm in permutations(all_nodes):
        # Check if this permutation respects all precedences
        valid = True
        node_positions = {node: idx for idx, node in enumerate(perm)}
        
        for delivery, pickup in delivery_to_pickup.items():
            if node_positions[pickup] >= node_positions[delivery]:
                valid = False
                break
        
        if valid:
            # Build tour with start/end nodes
            tour = list(perm)
            if start_node is not None:
                # Insert start node at beginning and end
                tour = [start_node] + tour + [start_node]
            else:
                # Close tour to first node
                tour = tour + [tour[0]]
            
            yield tour


def compute_optimal_brute_force(map_path: str, 
                                req_path: str, 
                                max_nodes: int = 0,
                                start_node: Optional[str] = None) -> Tuple[List[str], float]:
    """Compute optimal TSP tour using brute-force search.
    
    Args:
        map_path: Path to map XML file
        req_path: Path to delivery requests XML file
        max_nodes: Maximum number of nodes to use (0 = all). Limits to first N/2 deliveries.
        start_node: Optional depot/start node ID
    
    Returns:
        Tuple of (optimal_tour, optimal_cost)
    """
    print(f"\n{'='*70}")
    print("BRUTE-FORCE OPTIMAL TSP SOLVER")
    print(f"{'='*70}")
    
    # Load map
    print(f"\nLoading map from: {map_path}")
    tsp = TSP()
    G_map, all_map_nodes = tsp._build_networkx_map_graph(map_path)
    print(f"Map loaded: {G_map.number_of_nodes()} nodes, {G_map.number_of_edges()} edges")
    
    # Load delivery requests
    print(f"\nLoading delivery requests from: {req_path}")
    with open(req_path, 'r', encoding='utf-8') as f:
        req_text = f.read()
    deliveries = XMLParser.parse_deliveries(req_text)
    print(f"Loaded {len(deliveries)} delivery requests")
    
    # Extract pickup-delivery pairs (use correct attribute names)
    pd_pairs = []
    for d in deliveries:
        # Handle both Intersection objects and string IDs
        if hasattr(d.pickup_addr, 'id'):
            pickup = str(d.pickup_addr.id)  # type: ignore
        else:
            pickup = str(d.pickup_addr)
        
        if hasattr(d.delivery_addr, 'id'):
            delivery = str(d.delivery_addr.id)  # type: ignore
        else:
            delivery = str(d.delivery_addr)
        
        pd_pairs.append((pickup, delivery))
    
    # Limit number of deliveries if requested
    if max_nodes > 0:
        max_deliveries = max_nodes // 2
        if max_deliveries < len(pd_pairs):
            print(f"\nLimiting to first {max_deliveries} deliveries ({max_nodes} nodes)")
            pd_pairs = pd_pairs[:max_deliveries]
    
    print(f"\nWorking with {len(pd_pairs)} delivery pairs ({len(pd_pairs)*2} nodes)")
    
    if len(pd_pairs) > 8:
        print(f"\n⚠️  WARNING: {len(pd_pairs)} deliveries will take a VERY long time!")
        print(f"   Estimated permutations: ~{len(pd_pairs)}! = ~{factorial_approx(len(pd_pairs))}")
        response = input("\nContinue anyway? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Aborted.")
            return [], float('inf')
    
    # Collect all nodes
    all_nodes = []
    for p, d in pd_pairs:
        if p not in all_nodes:
            all_nodes.append(p)
        if d not in all_nodes:
            all_nodes.append(d)
    
    if start_node is not None:
        start_node = str(start_node)
        if start_node not in G_map.nodes():
            print(f"Warning: start_node {start_node} not in map")
            start_node = None
        elif start_node not in all_nodes:
            all_nodes.append(start_node)
    
    # Compute shortest paths
    print("\nComputing pairwise shortest paths...")
    sp_graph = compute_pairwise_shortest_paths(G_map, all_nodes)
    
    # Brute force: try all valid permutations
    print(f"\nSearching for optimal tour...")
    print(f"  Generating valid permutations (this may take a while)...")
    
    best_tour = None
    best_cost = float('inf')
    count = 0
    start_time = time.time()
    
    # Use the simpler permutation generator
    for tour in generate_all_valid_tours(pd_pairs, start_node):
        count += 1
        
        if count % 10000 == 0:
            elapsed = time.time() - start_time
            print(f"  Checked {count:,} permutations in {elapsed:.1f}s (rate: {count/elapsed:.0f}/s)...")
        
        # Calculate cost
        cost = tour_cost(tour, sp_graph)
        
        if cost < best_cost:
            best_cost = cost
            best_tour = tour
            print(f"  New best: cost={cost:.2f}, tour={' -> '.join(tour[:5])}{'...' if len(tour) > 5 else ''}")
    
    elapsed = time.time() - start_time
    
    if best_tour is None:
        print(f"\n{'='*70}")
        print("NO SOLUTION FOUND")
        print(f"{'='*70}")
        return [], float('inf')
    
    print(f"\n{'='*70}")
    print("OPTIMAL SOLUTION FOUND")
    print(f"{'='*70}")
    print(f"Checked {count:,} valid permutations in {elapsed:.1f}s")
    print(f"Optimal cost: {best_cost:.2f}")
    print(f"Optimal tour ({len(best_tour)} nodes):")
    print(f"  {' -> '.join(best_tour)}")
    
    return best_tour, best_cost


def factorial_approx(n):
    """Approximate factorial for display purposes."""
    if n <= 20:
        result = 1
        for i in range(2, n+1):
            result *= i
        return f"{result:,}"
    else:
        # Use Stirling's approximation
        import math
        log_fact = n * math.log(n) - n + 0.5 * math.log(2 * math.pi * n)
        return f"10^{int(log_fact / math.log(10))}"


def main():
    parser = argparse.ArgumentParser(
        description='Compute optimal TSP tour using brute-force search',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compute optimal for small instance
  python tools/compute_optimal_brute_force.py --map fichiersXMLPickupDelivery/petitPlan.xml --req fichiersXMLPickupDelivery/demandePetit1.xml
  
  # Limit to first 3 deliveries (6 nodes)
  python tools/compute_optimal_brute_force.py --map petitPlan.xml --req demandePetit1.xml --nodes 6
  
  # With start node
  python tools/compute_optimal_brute_force.py --map petitPlan.xml --req demandePetit1.xml --start 123456789

Performance notes:
  2 deliveries (4 nodes):  ~10 permutations      < 1 second
  3 deliveries (6 nodes):  ~90 permutations      < 1 second
  4 deliveries (8 nodes):  ~2,500 permutations   < 1 second
  5 deliveries (10 nodes): ~113,000 permutations ~few seconds
  6 deliveries (12 nodes): ~7 million perms      ~minutes
  7 deliveries (14 nodes): ~600 million perms    ~hours
  8 deliveries (16 nodes): ~63 billion perms     ~days
        """
    )
    
    parser.add_argument('--map', type=str, required=True, help='Map XML file path')
    parser.add_argument('--req', '--delivery', type=str, required=True, dest='req',
                        help='Delivery requests XML file path')
    parser.add_argument('--nodes', type=int, default=0,
                        help='Limit to first N nodes (0 = use all)')
    parser.add_argument('--start', type=str, default=None,
                        help='Start/depot node ID (optional)')
    
    args = parser.parse_args()
    
    # Resolve paths
    map_path = os.path.abspath(args.map)
    req_path = os.path.abspath(args.req)
    
    if not os.path.exists(map_path):
        print(f"❌ Map file not found: {map_path}")
        return
    
    if not os.path.exists(req_path):
        print(f"❌ Requests file not found: {req_path}")
        return
    
    # Compute optimal tour
    optimal_tour, optimal_cost = compute_optimal_brute_force(
        map_path, req_path, args.nodes, args.start
    )
    
    if optimal_tour:
        print("\n✓ Optimal solution computed successfully!")
    else:
        print("\n❌ Failed to compute optimal solution")


if __name__ == '__main__':
    main()
