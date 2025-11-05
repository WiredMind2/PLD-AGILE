"""Core benchmarking logic for TSP algorithms."""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Tuple, cast

import networkx as nx

# Ensure backend root is on sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.utils.TSP.TSP_networkx import TSP
from app.services.XMLParser import XMLParser

from .benchmark_types import BenchmarkResult
# Import canonical implementation from path_utils
from .path_utils import build_sp_graph_from_map


class TSPBenchmark:
    """Orchestrates TSP benchmarking across multiple test files."""

    def __init__(self, xml_dir: Path, include_optimal: bool = False):
        self.xml_dir = xml_dir
        self.include_optimal = include_optimal
        self.results: List[BenchmarkResult] = []

    def find_test_combinations(self) -> List[Tuple[str, str]]:
        """Find all valid map + request file combinations."""
        map_files = sorted(self.xml_dir.glob("*Plan.xml"))
        request_files = sorted(self.xml_dir.glob("demande*.xml"))

        combinations = []
        for map_file in map_files:
            map_size = map_file.stem  # petitPlan, moyenPlan, grandPlan

            # Find matching request files
            for req_file in request_files:
                req_name = req_file.stem.lower()

                # Match based on size prefix
                if "petit" in map_size.lower() and "petit" in req_name:
                    combinations.append((str(map_file), str(req_file)))
                elif "moyen" in map_size.lower() and "moyen" in req_name:
                    combinations.append((str(map_file), str(req_file)))
                elif "grand" in map_size.lower() and "grand" in req_name:
                    combinations.append((str(map_file), str(req_file)))

        return combinations

    def load_map_and_requests(self, map_path: str, req_path: str) -> Tuple[nx.DiGraph, List[Tuple[str, str]]]:
        """Load map graph and delivery requests from XML files."""
        print(f"  Loading {Path(map_path).name} + {Path(req_path).name}...")

        parser = XMLParser()

        # Load map
        with open(map_path, "r", encoding="utf-8") as f:
            map_data = parser.parse_map(f.read())

        # Build NetworkX graph (use string IDs to match TSP solver)
        G = nx.DiGraph()
        for intersection in map_data.intersections:
            G.add_node(str(intersection.id), latitude=intersection.latitude, longitude=intersection.longitude)
        for segment in map_data.road_segments:
            start_id = getattr(segment.start, 'id', segment.start)
            end_id = getattr(segment.end, 'id', segment.end)
            G.add_edge(str(start_id), str(end_id), weight=segment.length_m)

        # Load requests
        with open(req_path, "r", encoding="utf-8") as f:
            deliveries = parser.parse_deliveries(f.read())

        delivery_pairs = [(delivery.pickup_addr, delivery.delivery_addr) for delivery in deliveries]

        print(f"    Map: {len(G.nodes)} nodes, {len(G.edges)} edges")
        print(f"    Deliveries: {len(delivery_pairs)} ({len(delivery_pairs) * 2} nodes)")

        return G, delivery_pairs

    def run_tsp_heuristic(self, G: nx.DiGraph, delivery_pairs: List[Tuple[str, str]],
                          depot: str) -> Tuple[float, float, int, float]:
        """Run Christofides TSP and return timing + results."""
        from types import SimpleNamespace
        from app.models.schemas import Tour
        from typing import cast

        # Pairs are already strings, no conversion needed
        sample_tour = cast(Tour, SimpleNamespace(deliveries=delivery_pairs))

        # Create TSP instance and inject the graph
        tsp = TSP()
        # Set the cached graph so TSP doesn't rebuild from XML
        tsp.graph = G
        tsp._all_nodes = list(G.nodes())

        # Time the solving phase
        start_time = time.time()
        tour, compact_cost = tsp.solve(sample_tour)

        # Build shortest-path graph for TSP nodes
        nodes_list = [depot]
        for p, d in delivery_pairs:
            nodes_list.extend([p, d])
        sp_graph = build_sp_graph_from_map(G, nodes_list)

        # Expand tour
        tsp_full_route, tsp_expanded_cost = tsp.expand_tour_with_paths(tour, sp_graph)
        elapsed = time.time() - start_time

        return elapsed, compact_cost, len(tsp_full_route), tsp_expanded_cost

    def run_optimal_solver(self, G: nx.DiGraph, delivery_pairs: List[Tuple[str, str]], 
                          depot: str) -> Tuple[float | None, float | None, float | None]:
        """Run brute-force optimal solver (WARNING: Exponential complexity!)."""
        try:
            from compute_optimal_brute_force import (
                generate_all_valid_tours,
                tour_cost as brute_force_tour_cost,
            )
        except ImportError:
            return None, None, None

        nodes = [depot]
        for pickup, delivery in delivery_pairs:
            nodes.extend([pickup, delivery])

        # Build shortest path graph
        sp_graph = {}
        for u in nodes:
            sp_graph[u] = {}
            for v in nodes:
                if u != v:
                    try:
                        path_length = nx.shortest_path_length(G, u, v, weight="weight")
                        sp_graph[u][v] = path_length
                    except nx.NetworkXNoPath:
                        sp_graph[u][v] = float("inf")

        # Time the brute-force search
        start_time = time.time()

        best_cost = float("inf")
        best_tour = None

        for tour in generate_all_valid_tours(delivery_pairs, depot):
            cost = brute_force_tour_cost(tour, sp_graph)
            if cost < best_cost:
                best_cost = cost
                best_tour = tour

        elapsed = time.time() - start_time

        if best_tour is None:
            return None, None, None

        # Expand optimal tour to full path
        expanded_cost = 0.0
        for i in range(len(best_tour) - 1):
            u, v = best_tour[i], best_tour[i + 1]
            try:
                path_length = nx.shortest_path_length(G, u, v, weight="weight")
                expanded_cost += path_length
            except nx.NetworkXNoPath:
                expanded_cost += float("inf")

        return elapsed, best_cost, expanded_cost

    def benchmark_single_instance(self, map_path: str, req_path: str) -> BenchmarkResult:
        """Run benchmark on a single map + request combination."""
        try:
            # Load data
            G, delivery_pairs = self.load_map_and_requests(map_path, req_path)

            # Use first pickup as depot (common convention) - already a string
            depot = delivery_pairs[0][0] if delivery_pairs else str(list(G.nodes())[0])

            num_deliveries = len(delivery_pairs)
            num_nodes = num_deliveries * 2

            # Run TSP heuristic
            print("  Running Christofides TSP...")
            tsp_time, tsp_cost, tsp_expanded_nodes, tsp_expanded_cost = self.run_tsp_heuristic(
                G, delivery_pairs, depot
            )
            print(f"    ✓ Completed in {tsp_time:.3f}s, cost: {tsp_cost:.2f}")

            # Optionally run optimal solver
            optimal_time = None
            optimal_cost = None
            optimal_expanded_cost = None
            optimality_gap = None

            if self.include_optimal and num_nodes <= 10:
                print(f"  Running brute-force optimal solver...")
                optimal_time, optimal_cost, optimal_expanded_cost = self.run_optimal_solver(
                    G, delivery_pairs, depot
                )
                if optimal_cost:
                    optimality_gap = ((tsp_cost - optimal_cost) / optimal_cost) * 100
                    print(f"    ✓ Completed in {optimal_time:.3f}s, cost: {optimal_cost:.2f}")
                    print(f"    Gap: {optimality_gap:.2f}%")
            elif self.include_optimal:
                print(f"  ⚠️  Skipping optimal solver (too large: {num_nodes} nodes)")

            return BenchmarkResult(
                map_file=Path(map_path).name,
                request_file=Path(req_path).name,
                num_deliveries=num_deliveries,
                num_nodes=num_nodes,
                tsp_time_seconds=tsp_time,
                tsp_cost=tsp_cost,
                tsp_expanded_nodes=tsp_expanded_nodes,
                tsp_expanded_cost=tsp_expanded_cost,
                optimal_time_seconds=optimal_time,
                optimal_cost=optimal_cost,
                optimal_expanded_cost=optimal_expanded_cost,
                optimality_gap_percent=optimality_gap,
            )

        except Exception as e:
            print(f"    ✗ Error: {e}")
            return BenchmarkResult(
                map_file=Path(map_path).name,
                request_file=Path(req_path).name,
                num_deliveries=0,
                num_nodes=0,
                tsp_time_seconds=0.0,
                tsp_cost=0.0,
                tsp_expanded_nodes=0,
                tsp_expanded_cost=0.0,
                error=str(e),
            )

    def _print_header(self, title: str):
        """Print a section header."""
        print("=" * 70)
        print(title)
        print("=" * 70)

    def run_all_benchmarks(self):
        """Execute benchmarks on all test combinations."""
        combinations = self.find_test_combinations()

        self._print_header("TSP ALGORITHM BENCHMARK SUITE")
        print(f"Found {len(combinations)} test combinations")
        print(f"Include optimal solver: {self.include_optimal}")
        print("=" * 70)
        print()

        for i, (map_path, req_path) in enumerate(combinations, 1):
            print(f"[{i}/{len(combinations)}] Testing combination:")
            result = self.benchmark_single_instance(map_path, req_path)
            self.results.append(result)
            print()

        print("=" * 70)
        print("BENCHMARK COMPLETE")
        print("=" * 70)

    def print_summary(self):
        """Print summary statistics."""
        valid_results = [r for r in self.results if r.error is None]

        if not valid_results:
            print("No valid results to summarize")
            return

        print("\n" + "=" * 70)
        self._print_header("BENCHMARK SUMMARY")

        print(f"\nTotal tests: {len(self.results)}")
        print(f"Successful: {len(valid_results)}")
        print(f"Failed: {len(self.results) - len(valid_results)}")

        print(f"\nProblem size range:")
        print(f"  Min nodes: {min(r.num_nodes for r in valid_results)}")
        print(f"  Max nodes: {max(r.num_nodes for r in valid_results)}")

        print(f"\nChristofides TSP performance:")
        print(f"  Min time: {min(r.tsp_time_seconds for r in valid_results):.3f}s")
        print(f"  Max time: {max(r.tsp_time_seconds for r in valid_results):.3f}s")
        print(f"  Avg time: {sum(r.tsp_time_seconds for r in valid_results) / len(valid_results):.3f}s")

        if self.include_optimal:
            if (optimal_results := [r for r in valid_results if r.optimal_time_seconds is not None]):
                print(f"\nBrute-force optimal performance:")
                print(f"  Tests completed: {len(optimal_results)}")
                times = [cast(float, r.optimal_time_seconds) for r in optimal_results]
                print(f"  Min time: {min(times):.3f}s")
                print(f"  Max time: {max(times):.3f}s")
                print(f"  Avg time: {sum(times) / len(optimal_results):.3f}s")

                if (gap_results := [r for r in optimal_results if r.optimality_gap_percent is not None]):
                    print(f"\nOptimality gaps:")
                    gaps = [cast(float, r.optimality_gap_percent) for r in gap_results]
                    print(f"  Min gap: {min(gaps):.2f}%")
                    print(f"  Max gap: {max(gaps):.2f}%")
                    print(f"  Avg gap: {sum(gaps) / len(gap_results):.2f}%")

        print("=" * 70)