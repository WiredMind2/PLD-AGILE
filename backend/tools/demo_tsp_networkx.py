"""Demo runner for the NetworkX-based TSP solver.

Usage:
  python tools/demo_tsp_networkx.py [--xml PATH] [--nodes N]

This script measures the time to compute a compact TSP tour using the
existing `TSP` class and optionally expands the compact tour to a full
node-level route using shortest-paths between tour nodes.
"""

from __future__ import annotations

import os
import sys

# Ensure backend root is on sys.path for direct script execution
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

import time
import argparse
from typing import List, cast, Dict

from app.utils.TSP.TSP_networkx import TSP
from types import SimpleNamespace
from typing import cast
from app.models.schemas import Tour

# Import canonical implementation from path_utils
try:
    from .path_utils import build_sp_graph_from_map
except ImportError:
    # Fallback for direct script execution
    import sys
    sys.path.insert(0, os.path.join(HERE, '..'))
    from tools.path_utils import build_sp_graph_from_map


def pretty_format_path(
    path: List[str], max_items: int = 100, per_line: int = 20
) -> str:
    """Return a readable, line-wrapped representation of a node path.

    - If path length <= max_items, join all nodes with ' -> ' and wrap every `per_line` items.
    - If longer, show first `max_items//2` and last `max_items//2` with a "... (N nodes) ..." marker.
    """
    if not path:
        return "<empty>"

    n = len(path)

    def join_chunk(chunk):
        return " -> ".join(chunk)

    if n <= max_items:
        chunks = [join_chunk(path[i : i + per_line]) for i in range(0, n, per_line)]
        return "\n".join(chunks)

    head = path[: max_items // 2]
    tail = path[-(max_items // 2) :]
    middle = f"... ({n - len(head) - len(tail)} nodes omitted) ..."
    chunks = [join_chunk(head[i : i + per_line]) for i in range(0, len(head), per_line)]
    chunks.append(middle)
    chunks.extend(
        [join_chunk(tail[i : i + per_line]) for i in range(0, len(tail), per_line)]
    )
    return "\n".join(chunks)


def main():
    parser = argparse.ArgumentParser(
        description="Demo NetworkX TSP solver with timings"
    )
    parser.add_argument(
        "--map", type=str, default=None, help="Optional map XML file to use (preferred)"
    )
    # legacy alias for older scripts
    parser.add_argument(
        "--xml",
        type=str,
        default=None,
        help="Legacy: optional map XML file (alias for --map)",
    )
    parser.add_argument(
        "--req",
        type=str,
        default=None,
        help="Optional delivery-requests XML file to use (contains <livraison> entries)",
    )
    parser.add_argument(
        "--nodes", type=int, default=0, help="Limit number of TSP nodes (0 = use all)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run benchmark across all provided XML maps in repository",
    )
    parser.add_argument(
        "--repeat", type=int, default=1, help="Number of repeats per map"
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Optional CSV output file to store benchmark results",
    )
    args = parser.parse_args()

    tsp = TSP()

    # If --all is set, run across all XML maps in the repository folder
    maps_dir = os.path.abspath(
        os.path.join(BACKEND_ROOT, "..", "fichiersXMLPickupDelivery")
    )
    maps_to_run = []
    if args.all:
        if os.path.isdir(maps_dir):
            maps_to_run.extend(
                os.path.join(maps_dir, fname)
                for fname in os.listdir(maps_dir)
                if fname.lower().endswith(".xml")
            )
        else:
            print(f"No maps directory found at {maps_dir}")
            return
    elif args.map or args.xml:
        # prefer --map but support legacy --xml
        chosen = args.map or args.xml
        maps_to_run = [chosen]
    else:
        maps_to_run = [None]

    # Prepare results collection
    results = []

    # keep original builder to allow temporary monkeypatching
    orig_builder = tsp._build_networkx_map_graph
    for map_path in maps_to_run:
        # set map builder to use the provided xml if any
        if map_path:
            print(f"\n=== Running on map: {map_path}")
            orig_builder = tsp._build_networkx_map_graph
            tsp._build_networkx_map_graph = (
                lambda xml_file_path=None, p=map_path: orig_builder(p)
            )
        else:
            print("\n=== Running on default embedded map")

        # build map
        G_map, all_nodes = tsp._build_networkx_map_graph(None)
        nodes_seq = list(G_map.nodes())
        print(f"Map nodes: {len(nodes_seq)}")

        if len(nodes_seq) < 2:
            reason = "map has fewer than 2 nodes; skipping"
            print(f"Skipping map: {reason}")
            results.append(
                {
                    "map": os.path.basename(map_path) if map_path else "embedded",
                    "nodes": len(nodes_seq),
                    "solve_time_s": None,
                    "expand_time_s": None,
                    "compact_cost": None,
                    "expanded_cost": None,
                    "repeat": 0,
                    "skipped": True,
                    "reason": reason,
                }
            )
            # restore if monkeypatched and continue
            if map_path:
                tsp._build_networkx_map_graph = orig_builder
            continue

        for repeat_i in range(max(1, args.repeat)):
            # If a requests XML was provided for this run, parse deliveries and build nodes_list from them
            deliveries = []
            if args.req:
                try:
                    # lazy import XMLParser to avoid circular imports
                    from app.services.XMLParser import XMLParser

                    with open(args.req, "r", encoding="utf-8") as rf:
                        req_text = rf.read()
                    deliveries = XMLParser.parse_deliveries(req_text)
                    # collect node ids from deliveries
                    nodes_from_reqs = []
                    for d in deliveries:
                        for addr in (d.pickup_addr, d.delivery_addr):
                            nodes_from_reqs.append(addr)
                    # keep order and uniqueness
                    seen = set()
                    nodes_list = [
                        n for n in nodes_from_reqs if not (n in seen or seen.add(n))
                    ]
                    # filter to nodes present in map
                    map_nodes = set(all_nodes)
                    nodes_list = [n for n in nodes_list if n in map_nodes]
                    if args.nodes and args.nodes > 0:
                        nodes_list = nodes_list[: args.nodes]
                except Exception as e:
                    print(f"Failed to parse requests file {args.req}: {e}")
                    # fallback to using all nodes
                    nodes_list = (
                        list(all_nodes)[: args.nodes]
                        if args.nodes and args.nodes > 0
                        else list(all_nodes)
                    )
            else:
                if args.nodes and args.nodes > 0:
                    nodes_list = list(all_nodes)[: args.nodes]
                else:
                    nodes_list = list(all_nodes)

            print(
                f"Run {repeat_i+1}/{max(1,args.repeat)}: solving TSP for {len(nodes_list)} nodes"
            )

            # build a Tour-like object (list of (pickup,delivery) pairs)
            if args.req:
                # deliveries variable exists when --req parsing succeeded above
                try:
                    # ensure 'deliveries' exists in this scope (set by earlier parsing)
                    if "deliveries" not in locals():
                        deliveries = []
                    tour_pairs = [(d.pickup_addr, d.delivery_addr) for d in deliveries]
                except Exception:
                    # fallback: pair adjacent nodes
                    tour_pairs = []
                    for k in range(0, len(nodes_list), 2):
                        a = nodes_list[k]
                        b = (
                            nodes_list[k + 1]
                            if k + 1 < len(nodes_list)
                            else nodes_list[0]
                        )
                        tour_pairs.append((a, b))
            else:
                # pair adjacent nodes from the map to form pickup->delivery pairs
                tour_pairs = []
                for k in range(0, len(nodes_list), 2):
                    a = nodes_list[k]
                    b = nodes_list[k + 1] if k + 1 < len(nodes_list) else nodes_list[0]
                    tour_pairs.append((a, b))

            sample_tour = cast(Tour, SimpleNamespace(deliveries=tour_pairs))

            # solve using new interface
            t0 = time.perf_counter()
            tour, compact_cost = tsp.solve(sample_tour)
            t1 = time.perf_counter()
            solve_time = t1 - t0

            # build sp_graph and expand
            t2 = time.perf_counter()
            sp_graph = build_sp_graph_from_map(G_map, nodes_list)
            try:
                full_route, expanded_cost = tsp.expand_tour_with_paths(tour, sp_graph)
                t3 = time.perf_counter()
                expand_time = t3 - t2
            except Exception as e:
                full_route, expanded_cost = [], float("inf")
                t3 = time.perf_counter()
                expand_time = t3 - t2
                print(f"Expand failed: {e}")

            # pretty-print the full route for readability
            if full_route:
                print("\nFull route (readable):")
                print(pretty_format_path(full_route, max_items=200, per_line=30))

            print(
                f"  solve_time={solve_time:.6f}s expand_time={expand_time:.6f}s compact_cost={compact_cost} expanded_cost={expanded_cost}"
            )

            results.append(
                {
                    "map": os.path.basename(map_path) if map_path else "embedded",
                    "nodes": len(nodes_list),
                    "solve_time_s": solve_time,
                    "expand_time_s": expand_time,
                    "compact_cost": compact_cost,
                    "expanded_cost": expanded_cost,
                    "repeat": repeat_i + 1,
                    "skipped": False,
                    "reason": "",
                }
            )

        # restore original builder if it was monkeypatched
        if map_path:
            tsp._build_networkx_map_graph = orig_builder

    # Optionally write CSV
    if args.out:
        import csv

        out_path = os.path.abspath(args.out)
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "map",
                "nodes",
                "repeat",
                "solve_time_s",
                "expand_time_s",
                "compact_cost",
                "expanded_cost",
                "skipped",
                "reason",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow({k: r.get(k, "") for k in writer.fieldnames})
        print(f"Benchmark results written to {out_path}")
    else:
        print("\nBenchmark results:")
        for r in results:
            print(r)


if __name__ == "__main__":
    main()
