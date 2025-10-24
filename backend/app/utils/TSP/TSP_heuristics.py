"""
Initial tour construction heuristics for TSP solver.

This module provides various constructive heuristics for building initial TSP tours:
- Nearest Neighbor
- Clarke-Wright Savings
- Insertion Heuristic
"""

import networkx as nx
from typing import List, Tuple, Set, Dict, Callable, Optional


class TourHeuristics:
    """Collection of heuristics for constructing initial TSP tours."""

    @staticmethod
    def build_nearest_neighbor_tour(
        G: nx.Graph,
        pickups: List[str],
        deliveries: List[str],
        delivery_map: Dict[str, str],
        tour_cost_fn: Callable[[List[str]], float],
        is_valid_tour_fn: Callable[[List[str]], bool],
        start_node: Optional[str] = None
    ) -> Tuple[List[str], float]:
        """Build tour by nearest neighbor, considering all unvisited nodes.
        
        Args:
            G: Metric graph with nodes and edge weights
            pickups: List of pickup nodes
            deliveries: List of delivery nodes
            delivery_map: Maps delivery nodes to their required pickup nodes
            tour_cost_fn: Function to compute tour cost
            is_valid_tour_fn: Function to validate tour precedence constraints
            start_node: Optional starting node for the tour
            
        Returns:
            Tuple of (tour_sequence, tour_cost)
        """
        INF = float("inf")
        best_tour = None
        best_cost = INF
        
        for start_pickup in pickups[:3]:  # Try first 3 pickups as starts
            if start_pickup not in G.nodes():
                continue
                
            unvisited = set(pickups + deliveries)
            if start_node is not None and start_node in G.nodes():
                current = start_node
                route = [start_node]
                # Need to add the first pickup and remove from unvisited
                route.append(start_pickup)
                unvisited.discard(start_pickup)
                current = start_pickup
            else:
                # No start_node, so start directly from the pickup
                current = start_pickup
                route = [start_pickup]
                unvisited.discard(start_pickup)
            
            while unvisited:
                # Find nearest node that maintains precedence
                best_next = None
                best_dist = INF
                
                for node in unvisited:
                    # Check if we can visit this node (precedence)
                    can_visit = True
                    if node in deliveries:
                        # Check if pickup was already visited
                        req_pickup = delivery_map[node]
                        if req_pickup in unvisited:
                            can_visit = False
                    
                    if can_visit:
                        dist = G[current][node]["weight"]
                        if dist < best_dist:
                            best_dist = dist
                            best_next = node
                
                if best_next is None:
                    # Forced to add remaining (shouldn't happen with valid precedence)
                    best_next = list(unvisited)[0]
                
                route.append(best_next)
                unvisited.discard(best_next)
                current = best_next
            
            # Close tour
            if start_node is not None and start_node in G.nodes():
                if route[-1] != start_node:
                    route.append(start_node)
            else:
                if route[0] != route[-1]:
                    route.append(route[0])
            
            cost = tour_cost_fn(route)
            core_route = route[:-1] if route[0] == route[-1] else route
            if cost < best_cost and is_valid_tour_fn(core_route):
                best_cost = cost
                best_tour = route
        
        return best_tour or [], best_cost

    @staticmethod
    def build_savings_tour(
        G: nx.Graph,
        pd_pairs: List[Tuple[str, str]],
        tour_cost_fn: Callable[[List[str]], float],
        is_valid_tour_fn: Callable[[List[str]], bool],
        start_node: Optional[str] = None
    ) -> Tuple[List[str], float]:
        """Build tour using Clarke-Wright savings heuristic adapted for precedence.
        
        Args:
            G: Metric graph with nodes and edge weights
            pd_pairs: List of (pickup, delivery) tuples
            tour_cost_fn: Function to compute tour cost
            is_valid_tour_fn: Function to validate tour precedence constraints
            start_node: Optional depot/start node
            
        Returns:
            Tuple of (tour_sequence, tour_cost)
        """
        INF = float("inf")
        # Start with individual pickup->delivery routes
        routes = []
        pickups = [p for p, _ in pd_pairs]
        depot = start_node if start_node and start_node in G.nodes() else pickups[0]
        
        for p, d in pd_pairs:
            if p in G.nodes() and d in G.nodes():
                routes.append([p, d])
        
        # Calculate savings for merging routes
        savings = []
        for i in range(len(routes)):
            for j in range(i + 1, len(routes)):
                route_i, route_j = routes[i], routes[j]
                # Try merging: depot -> route_i -> route_j -> depot
                # Savings = dist(i_end, depot) + dist(depot, j_start) - dist(i_end, j_start)
                i_end = route_i[-1]
                j_start = route_j[0]
                s = (G[i_end][depot]["weight"] + G[depot][j_start]["weight"] - 
                     G[i_end][j_start]["weight"])
                savings.append((s, i, j))
        
        savings.sort(reverse=True)
        
        # Merge routes greedily with precedence checks
        merged = [False] * len(routes)
        final_route = []
        
        for s, i, j in savings[:len(routes)//2]:  # Limit merges
            if not merged[i] and not merged[j]:
                # Merge route_j into route_i
                merged_route = routes[i] + routes[j]
                # Check if the merged route respects precedence constraints
                if is_valid_tour_fn(merged_route):
                    routes[i] = merged_route
                    merged[j] = True
        
        # Combine remaining routes
        for i, route in enumerate(routes):
            if not merged[i]:
                final_route.extend(route)
        
        if not final_route:
            return [], INF
        
        # Add depot if needed
        if start_node and start_node in G.nodes():
            final_route = [start_node] + final_route + [start_node]
        else:
            final_route.append(final_route[0])
        
        cost = tour_cost_fn(final_route)
        return final_route, cost

    @staticmethod
    def build_insertion_tour(
        G: nx.Graph,
        pd_pairs: List[Tuple[str, str]],
        tour_cost_fn: Callable[[List[str]], float],
        is_valid_tour_fn: Callable[[List[str]], bool],
        start_node: Optional[str] = None
    ) -> Tuple[List[str], float]:
        """Build tour by inserting pickup-delivery pairs in best positions.
        
        Args:
            G: Metric graph with nodes and edge weights
            pd_pairs: List of (pickup, delivery) tuples
            tour_cost_fn: Function to compute tour cost
            is_valid_tour_fn: Function to validate tour precedence constraints
            start_node: Optional depot/start node
            
        Returns:
            Tuple of (tour_sequence, tour_cost)
        """
        INF = float("inf")
        pickups = [p for p, _ in pd_pairs]
        depot = start_node if start_node and start_node in G.nodes() else pickups[0]
        
        # Start with first pickup-delivery pair
        if not pd_pairs:
            return [], INF
        
        # Find pair closest to depot
        best_pair = None
        best_dist = INF
        for p, d in pd_pairs:
            if p in G.nodes() and d in G.nodes():
                dist = G[depot][p]["weight"] if depot != p else 0
                if dist < best_dist:
                    best_dist = dist
                    best_pair = (p, d)
        
        if not best_pair:
            return [], INF
        
        p0, d0 = best_pair
        if start_node and start_node in G.nodes():
            route = [start_node, p0, d0, start_node]
        else:
            route = [p0, d0, p0]
        
        remaining = [(p, d) for (p, d) in pd_pairs if (p, d) != best_pair 
                    and p in G.nodes() and d in G.nodes()]
        
        # Insert remaining pairs at best positions
        while remaining:
            best_insertion = None
            best_cost_increase = INF
            best_pair_idx = -1
            
            for pair_idx, (p, d) in enumerate(remaining):
                # Try inserting p and d at all valid positions
                for i in range(1, len(route)):
                    for j in range(i, len(route)):
                        # Insert p at position i, d at position j
                        new_route = route[:i] + [p] + route[i:j] + [d] + route[j:]
                        
                        test_route = new_route[:-1] if new_route[0] == new_route[-1] else new_route
                        if not is_valid_tour_fn(test_route):
                            continue
                        
                        new_cost = tour_cost_fn(new_route)
                        old_cost = tour_cost_fn(route)
                        cost_increase = new_cost - old_cost
                        
                        if cost_increase < best_cost_increase:
                            best_cost_increase = cost_increase
                            best_insertion = new_route
                            best_pair_idx = pair_idx
            
            if best_insertion is None:
                # No valid insertion found, try to append remaining pairs while checking precedence
                for p, d in remaining:
                    # Insert pickup and delivery before the last node (which closes the tour)
                    route.insert(-1, p)
                    route.insert(-1, d)
                    # Verify the tour still respects precedence
                    test_route = route[:-1] if route[0] == route[-1] else route
                    if not is_valid_tour_fn(test_route):
                        # If invalid, remove the inserted nodes and skip this pair
                        route.remove(p)
                        route.remove(d)
                break
            
            route = best_insertion
            remaining.pop(best_pair_idx)
        
        cost = tour_cost_fn(route)
        return route, cost
