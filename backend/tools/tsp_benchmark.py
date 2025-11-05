"""TSP Benchmarking: Classes and functions for benchmarking TSP algorithms."""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional, cast
from dataclasses import dataclass

import networkx as nx
import matplotlib
import matplotlib.pyplot as plt

# Ensure backend root is on sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.utils.TSP.TSP_networkx import TSP
from app.services.XMLParser import XMLParser
from app.models.schemas import Tour
from types import SimpleNamespace

# Import from canonical modules
from .path_utils import build_sp_graph_from_map as build_sp_graph, tour_cost
from .tsp_core import generate_all_valid_tours as generate_valid_tours

# Import compute_optimal_brute_force from its module
try:
    from . import compute_optimal_brute_force as optimal_module
    compute_optimal_brute_force = optimal_module.compute_optimal_brute_force
except ImportError:
    compute_optimal_brute_force = None

matplotlib.use('Agg')  # Non-interactive backend


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    map_file: str
    request_file: str
    num_deliveries: int
    num_nodes: int
    tsp_time_seconds: float
    tsp_cost: float
    tsp_expanded_nodes: int
    tsp_expanded_cost: float
    optimal_time_seconds: Optional[float] = None
    optimal_cost: Optional[float] = None
    optimal_expanded_cost: Optional[float] = None
    optimality_gap_percent: Optional[float] = None
    error: Optional[str] = None


class TSPBenchmark:
    """Handles TSP benchmarking operations."""

    def __init__(self, xml_dir: Path, include_optimal: bool = False):
        self.xml_dir = xml_dir
        self.include_optimal = include_optimal
        self.results: List[BenchmarkResult] = []

    def find_test_combinations(self) -> List[Tuple[str, str]]:
        """Find valid map-request file combinations."""
        map_files = sorted(self.xml_dir.glob("*Plan.xml"))
        req_files = sorted(self.xml_dir.glob("demande*.xml"))
        combinations = []
        for map_file in map_files:
            map_size = map_file.stem
            for req_file in req_files:
                req_name = req_file.stem.lower()
                if "petit" in map_size.lower() and "petit" in req_name:
                    combinations.append((str(map_file), str(req_file)))
                elif "moyen" in map_size.lower() and "moyen" in req_name:
                    combinations.append((str(map_file), str(req_file)))
                elif "grand" in map_size.lower() and "grand" in req_name:
                    combinations.append((str(map_file), str(req_file)))
        return combinations

    def load_map_and_requests(self, map_path: str, req_path: str) -> Tuple[nx.DiGraph, List[Tuple[str, str]]]:
        """Load map and request data."""
        parser = XMLParser()
        with open(map_path, "r", encoding="utf-8") as f:
            map_data = parser.parse_map(f.read())
        G = nx.DiGraph()
        for inter in map_data.intersections:
            G.add_node(str(inter.id))
        for seg in map_data.road_segments:
            G.add_edge(str(seg.start.id), str(seg.end.id), weight=seg.length_m)
        with open(req_path, "r", encoding="utf-8") as f:
            deliveries = parser.parse_deliveries(f.read())
        delivery_pairs = [(d.pickup_addr, d.delivery_addr) for d in deliveries]
        return G, delivery_pairs

    def run_tsp_heuristic(self, G: nx.DiGraph, delivery_pairs: List[Tuple[str, str]], depot: str) -> Tuple[float, float, int, float]:
        """Run TSP heuristic."""
        tsp = TSP()
        tsp.graph = G
        tsp._all_nodes = list(G.nodes())
        sample_tour = cast(Tour, SimpleNamespace(deliveries=delivery_pairs))
        start_time = time.time()
        tour, compact_cost = tsp.solve(sample_tour)
        nodes_list = [depot] + [n for pair in delivery_pairs for n in pair]
        sp_graph = build_sp_graph(G, nodes_list)
        full_route, expanded_cost = tsp.expand_tour_with_paths(tour, sp_graph)
        elapsed = time.time() - start_time
        return elapsed, compact_cost, len(full_route), expanded_cost

    def run_optimal_solver(self, G: nx.DiGraph, delivery_pairs: List[Tuple[str, str]], depot: str) -> Tuple[float | None, float | None, float | None]:
        """Run optimal solver."""
        # Build a deduplicated ordered list of nodes (depot + pickups/deliveries).
        # Deduplication avoids repeated entries when depot equals a pickup node
        # which otherwise produces self-transitions in generated tours.
        nodes = list(dict.fromkeys([depot] + [n for pair in delivery_pairs for n in pair]))
        sp_graph = {}
        for u in nodes:
            sp_graph[u] = {}
            for v in nodes:
                # Ensure self-costs are zero so tours containing repeated start/end
                # nodes (e.g. start_node == pickup) are evaluated correctly.
                if u == v:
                    sp_graph[u][v] = 0.0
                else:
                    try:
                        cost = nx.shortest_path_length(G, u, v, weight="weight")
                        sp_graph[u][v] = cost
                    except:
                        sp_graph[u][v] = float("inf")
        start_time = time.time()
        best_cost = float("inf")
        best_tour = None
        for tour in generate_valid_tours(delivery_pairs, depot):
            cost = tour_cost(tour, sp_graph)
            if cost < best_cost:
                best_cost = cost
                best_tour = tour
        elapsed = time.time() - start_time
        expanded_cost = 0.0
        if best_tour:
            for i in range(len(best_tour) - 1):
                u, v = best_tour[i], best_tour[i + 1]
                try:
                    expanded_cost += nx.shortest_path_length(G, u, v, weight="weight")
                except:
                    expanded_cost += float("inf")
        return elapsed, best_cost if best_tour else None, expanded_cost if best_tour else None

    def benchmark_single_instance(self, map_path: str, req_path: str) -> BenchmarkResult:
        """Benchmark a single instance."""
        try:
            G, delivery_pairs = self.load_map_and_requests(map_path, req_path)
            depot = delivery_pairs[0][0] if delivery_pairs else list(G.nodes())[0]
            num_deliveries = len(delivery_pairs)
            num_nodes = num_deliveries * 2
            tsp_time, tsp_cost, tsp_expanded_nodes, tsp_expanded_cost = self.run_tsp_heuristic(G, delivery_pairs, depot)
            optimal_time = optimal_cost = optimal_expanded_cost = optimality_gap = None
            if self.include_optimal and num_nodes <= 10:
                optimal_time, optimal_cost, optimal_expanded_cost = self.run_optimal_solver(G, delivery_pairs, depot)
                if optimal_cost:
                    optimality_gap = ((tsp_cost - optimal_cost) / optimal_cost) * 100
            return BenchmarkResult(map_file=Path(map_path).name, request_file=Path(req_path).name,
                                   num_deliveries=num_deliveries, num_nodes=num_nodes,
                                   tsp_time_seconds=tsp_time, tsp_cost=tsp_cost,
                                   tsp_expanded_nodes=tsp_expanded_nodes, tsp_expanded_cost=tsp_expanded_cost,
                                   optimal_time_seconds=optimal_time, optimal_cost=optimal_cost,
                                   optimal_expanded_cost=optimal_expanded_cost, optimality_gap_percent=optimality_gap)
        except Exception as e:
            return BenchmarkResult(map_file=Path(map_path).name, request_file=Path(req_path).name,
                                   num_deliveries=0, num_nodes=0, tsp_time_seconds=0.0, tsp_cost=0.0,
                                   tsp_expanded_nodes=0, tsp_expanded_cost=0.0, error=str(e))

    def run_all_benchmarks(self):
        """Run all benchmarks."""
        combinations = self.find_test_combinations()
        print(f"Found {len(combinations)} test combinations")
        for i, (map_path, req_path) in enumerate(combinations, 1):
            print(f"[{i}/{len(combinations)}] Testing {Path(map_path).name} + {Path(req_path).name}")
            result = self.benchmark_single_instance(map_path, req_path)
            self.results.append(result)

    def print_summary(self):
        """Print benchmark summary."""
        valid_results = [r for r in self.results if r.error is None]
        if not valid_results:
            print("No valid results")
            return
        print(f"Total: {len(self.results)}, Successful: {len(valid_results)}")
        print(f"Time range: {min(r.tsp_time_seconds for r in valid_results):.3f}s - {max(r.tsp_time_seconds for r in valid_results):.3f}s")


class BenchmarkVisualizer:
    """Handles visualization of benchmark results."""

    def __init__(self, results: List[BenchmarkResult], include_optimal: bool = False):
        self.results = results
        self.include_optimal = include_optimal

    def generate_graphs(self, output_dir: Path):
        """Generate visualization graphs."""
        output_dir.mkdir(parents=True, exist_ok=True)
        valid_results = [r for r in self.results if r.error is None]
        if not valid_results:
            print("No valid results to plot")
            return
        valid_results.sort(key=lambda r: r.num_nodes)
        num_nodes = [r.num_nodes for r in valid_results]
        tsp_times = [r.tsp_time_seconds for r in valid_results]
        tsp_costs = [r.tsp_cost for r in valid_results]

        # Time vs size
        plt.figure(figsize=(10, 6))
        plt.plot(num_nodes, tsp_times, 'o-', linewidth=2, markersize=8, label='Christofides TSP')
        if self.include_optimal:
            opt_times = [r.optimal_time_seconds for r in valid_results if r.optimal_time_seconds]
            opt_nodes = [r.num_nodes for r in valid_results if r.optimal_time_seconds]
            if opt_times:
                plt.plot(opt_nodes, opt_times, 's-', linewidth=2, markersize=8, label='Brute-Force Optimal')
        plt.xlabel('Number of Nodes')
        plt.ylabel('Time (seconds)')
        plt.title('TSP Performance: Time vs Problem Size')
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / "tsp_time_vs_size.png", dpi=300, bbox_inches='tight')
        plt.close()

        # Cost vs size
        plt.figure(figsize=(10, 6))
        plt.plot(num_nodes, tsp_costs, 'o-', linewidth=2, markersize=8, color='green', label='TSP Cost')
        if self.include_optimal:
            opt_costs = [r.optimal_cost for r in valid_results if r.optimal_cost]
            opt_nodes = [r.num_nodes for r in valid_results if r.optimal_cost]
            if opt_costs:
                plt.plot(opt_nodes, opt_costs, 's-', linewidth=2, markersize=8, color='red', label='Optimal Cost')
        plt.xlabel('Number of Nodes')
        plt.ylabel('Cost (meters)')
        plt.title('TSP Quality: Cost vs Problem Size')
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / "tsp_cost_vs_size.png", dpi=300, bbox_inches='tight')
        plt.close()

        # Optimality gap
        if self.include_optimal:
            gap_data = [(r.num_nodes, r.optimality_gap_percent) for r in valid_results if r.optimality_gap_percent is not None]
            if gap_data:
                nodes, gaps = zip(*gap_data)
                plt.figure(figsize=(10, 6))
                plt.bar(nodes, gaps, width=0.6, color='orange', alpha=0.7)
                plt.xlabel('Number of Nodes')
                plt.ylabel('Gap (%)')
                plt.title('TSP Quality: Gap from Optimal')
                plt.grid(True, alpha=0.3, axis='y')
                plt.tight_layout()
                plt.savefig(output_dir / "tsp_optimality_gap.png", dpi=300, bbox_inches='tight')
                plt.close()


def run_benchmark(args):
    """Run benchmark (legacy function for compatibility)."""
    xml_dir = Path(args.xml_dir) if args.xml_dir else Path(BACKEND_ROOT).parent / "fichiersXMLPickupDelivery"
    if not xml_dir.exists():
        print(f"XML directory not found: {xml_dir}")
        return
    output_dir = Path(args.output_dir) if args.output_dir else Path(BACKEND_ROOT) / "tools" / "benchmark_results"
    benchmark = TSPBenchmark(xml_dir, args.include_optimal)
    benchmark.run_all_benchmarks()
    visualizer = BenchmarkVisualizer(benchmark.results, args.include_optimal)
    visualizer.generate_graphs(output_dir)
    benchmark.print_summary()
    print(f"Results saved to {output_dir}")