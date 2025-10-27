"""Data loading utilities for TSP path comparison tool."""

from typing import List, Tuple, Optional
import networkx as nx
from app.utils.TSP.TSP_networkx import TSP


def load_map_graph(tsp_solver: "TSP") -> Tuple[nx.DiGraph, List[str]]:
    """Load the map graph and return nodes."""
    G_map, all_nodes = tsp_solver._build_networkx_map_graph(None)
    print(f"Map loaded: {len(all_nodes)} nodes")
    return G_map, all_nodes


def load_delivery_requests(args, all_nodes: List[str]) -> Tuple[List, List[str]]:
    """Load delivery requests and extract relevant nodes."""
    deliveries = []
    nodes_list = []

    if args.req:
        print(f"\nLoading delivery requests from: {args.req}")
        try:
            from app.services.XMLParser import XMLParser

            with open(args.req, "r", encoding="utf-8") as rf:
                req_text = rf.read()
            deliveries = XMLParser.parse_deliveries(req_text)
            print(f"Loaded {len(deliveries)} delivery requests")

            # Show first few deliveries
            print("\nDelivery details:")
            for i, d in enumerate(deliveries[:5], 1):
                pickup = d.pickup_addr
                delivery = d.delivery_addr
                print(
                    f"  {i}. Pickup: {pickup} -> Delivery: {delivery} "
                    f"(service: {d.pickup_service_s}s + {d.delivery_service_s}s)"
                )
            if len(deliveries) > 5:
                print(f"  ... and {len(deliveries) - 5} more deliveries")

            # Extract nodes from deliveries
            nodes_from_reqs = []
            for d in deliveries:
                nodes_from_reqs.extend([d.pickup_addr, d.delivery_addr])

            # Keep order and uniqueness
            seen = set()
            nodes_list = [n for n in nodes_from_reqs if not (n in seen or seen.add(n))]

            # Filter to nodes present in map
            map_nodes = set(all_nodes)
            nodes_list = [n for n in nodes_list if n in map_nodes]

            if args.nodes and args.nodes > 0:
                nodes_list = nodes_list[: args.nodes]

        except Exception as e:
            print(f"Error loading requests: {e}")
            nodes_list = (
                list(all_nodes)[: args.nodes] if args.nodes > 0 else list(all_nodes)
            )
    else:
        print("\nNo delivery requests provided, using map nodes")
        nodes_list = (
            list(all_nodes)[: args.nodes] if args.nodes > 0 else list(all_nodes)
        )

    return deliveries, nodes_list


def build_tour_pairs(deliveries: List, nodes_list: List[str]) -> List[Tuple[str, str]]:
    """Build tour pairs from deliveries or create default pairs."""
    if deliveries:
        tour_pairs = [
            (
                d.pickup_addr,
                d.delivery_addr,
            )
            for d in deliveries
        ]
    else:
        # Pair adjacent nodes
        tour_pairs = []
        for k in range(0, len(nodes_list), 2):
            a = nodes_list[k]
            b = nodes_list[k + 1] if k + 1 < len(nodes_list) else nodes_list[0]
            tour_pairs.append((a, b))

    return tour_pairs


def validate_nodes(nodes_list: List[str]) -> bool:
    """Validate that we have enough nodes to create a path."""
    if len(nodes_list) < 2:
        print("Error: Need at least 2 nodes to create a path")
        return False

    print(f"\nWorking with {len(nodes_list)} nodes:")
    print(
        f"  {', '.join(nodes_list[:20])}"
        + (f" ... and {len(nodes_list) - 20} more" if len(nodes_list) > 20 else "")
    )
    return True