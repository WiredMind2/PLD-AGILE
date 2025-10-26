"""Benchmark TSP algorithm performance across all available XML test files.

This script:
1. Scans all XML map and request files in fichiersXMLPickupDelivery/
2. Runs the Christofides TSP algorithm on each combination
3. Measures computation time and solution quality
4. Generates performance graphs showing scaling behavior

Usage:
  python tools/benchmark_tsp.py
  python tools/benchmark_tsp.py --output-dir results/
  python tools/benchmark_tsp.py --include-optimal  # WARNING: Very slow for large instances!
"""

from __future__ import annotations

import os
import sys
import time
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import argparse

# Ensure backend root is on sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for saving figures

from app.utils.TSP.TSP_networkx import TSP
from app.services.XMLParser import XMLParser


@dataclass
class BenchmarkResult:
    """Store results from a single TSP benchmark run."""
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
    
    def load_map_and_requests(self, map_path: str, req_path: str) -> Tuple[nx.DiGraph, List[Tuple[int, int]]]:
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
            G.add_edge(str(segment.start.id), str(segment.end.id), weight=segment.length_m)
        
        # Load requests
        with open(req_path, "r", encoding="utf-8") as f:
            deliveries = parser.parse_deliveries(f.read())
        
        delivery_pairs = []
        for delivery in deliveries:
            # Use string IDs to match TSP solver
            pickup = delivery.pickup_addr
            delivery_addr = delivery.delivery_addr
            delivery_pairs.append((pickup, delivery_addr))
        
        print(f"    Map: {len(G.nodes)} nodes, {len(G.edges)} edges")
        print(f"    Deliveries: {len(delivery_pairs)} ({len(delivery_pairs) * 2} nodes)")
        
        return G, delivery_pairs
    
    def build_sp_graph_from_map(self, G_map: nx.DiGraph, nodes_list: List[str]) -> Dict:
        """Build shortest-path graph between nodes."""
        sp_graph = {}
        for src in nodes_list:
            sp_graph[src] = {}
            for tgt in nodes_list:
                if src != tgt:
                    try:
                        # Use string node IDs directly (no conversion to int)
                        path = nx.shortest_path(G_map, src, tgt, weight="weight")
                        cost = nx.shortest_path_length(G_map, src, tgt, weight="weight")
                        sp_graph[src][tgt] = {"path": path, "cost": cost}
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        sp_graph[src][tgt] = {"path": [], "cost": float("inf")}
        return sp_graph
    
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
        sp_graph = self.build_sp_graph_from_map(G, nodes_list)
        
        # Expand tour
        tsp_full_route, tsp_expanded_cost = tsp.expand_tour_with_paths(tour, sp_graph)
        elapsed = time.time() - start_time
        
        return elapsed, compact_cost, len(tsp_full_route), tsp_expanded_cost
    
    def run_optimal_solver(self, G: nx.DiGraph, delivery_pairs: List[Tuple[int, int]], 
                          depot: int) -> Tuple[float, float, float]:
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
    
    def run_all_benchmarks(self):
        """Execute benchmarks on all test combinations."""
        combinations = self.find_test_combinations()
        
        print("=" * 70)
        print("TSP ALGORITHM BENCHMARK SUITE")
        print("=" * 70)
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
    
    def save_results(self, output_dir: Path):
        """Save benchmark results to JSON file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / "benchmark_results.json"
        
        results_dict = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "include_optimal": self.include_optimal,
            "num_tests": len(self.results),
            "results": [asdict(r) for r in self.results],
        }
        
        with open(output_file, "w") as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"✓ Results saved to: {output_file}")
    
    def generate_graphs(self, output_dir: Path):
        """Generate performance analysis graphs."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Filter out failed results
        valid_results = [r for r in self.results if r.error is None]
        
        if not valid_results:
            print("⚠️  No valid results to plot")
            return
        
        # Sort by number of nodes
        valid_results.sort(key=lambda r: r.num_nodes)
        
        # Extract data
        num_nodes = [r.num_nodes for r in valid_results]
        tsp_times = [r.tsp_time_seconds for r in valid_results]
        tsp_costs = [r.tsp_cost for r in valid_results]
        
        # Graph 1: Computation Time vs Problem Size
        plt.figure(figsize=(10, 6))
        plt.plot(num_nodes, tsp_times, 'o-', linewidth=2, markersize=8, label='Christofides TSP')
        
        if self.include_optimal:
            optimal_times = [r.optimal_time_seconds for r in valid_results if r.optimal_time_seconds]
            optimal_nodes = [r.num_nodes for r in valid_results if r.optimal_time_seconds]
            if optimal_times:
                plt.plot(optimal_nodes, optimal_times, 's-', linewidth=2, markersize=8, label='Brute-Force Optimal')
        
        plt.xlabel('Number of Nodes (Pickup + Delivery)', fontsize=12)
        plt.ylabel('Computation Time (seconds)', fontsize=12)
        plt.title('TSP Algorithm Performance: Time vs Problem Size', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10)
        plt.tight_layout()
        
        time_plot_path = output_dir / "tsp_time_vs_size.png"
        plt.savefig(time_plot_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {time_plot_path}")
        plt.close()
        
        # Graph 2: Solution Cost vs Problem Size
        plt.figure(figsize=(10, 6))
        plt.plot(num_nodes, tsp_costs, 'o-', linewidth=2, markersize=8, color='green', label='TSP Heuristic Cost')
        
        if self.include_optimal:
            optimal_costs = [r.optimal_cost for r in valid_results if r.optimal_cost]
            optimal_nodes = [r.num_nodes for r in valid_results if r.optimal_cost]
            if optimal_costs:
                plt.plot(optimal_nodes, optimal_costs, 's-', linewidth=2, markersize=8, 
                        color='red', label='Optimal Cost')
        
        plt.xlabel('Number of Nodes (Pickup + Delivery)', fontsize=12)
        plt.ylabel('Tour Cost (meters)', fontsize=12)
        plt.title('TSP Solution Quality: Cost vs Problem Size', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10)
        plt.tight_layout()
        
        cost_plot_path = output_dir / "tsp_cost_vs_size.png"
        plt.savefig(cost_plot_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {cost_plot_path}")
        plt.close()
        
        # Graph 3: Optimality Gap (if optimal solutions computed)
        if self.include_optimal:
            gap_data = [(r.num_nodes, r.optimality_gap_percent) 
                       for r in valid_results if r.optimality_gap_percent is not None]
            
            if gap_data:
                gap_nodes, gaps = zip(*gap_data)
                
                plt.figure(figsize=(10, 6))
                plt.bar(gap_nodes, gaps, width=0.6, color='orange', alpha=0.7, edgecolor='black')
                plt.axhline(y=0, color='green', linestyle='--', linewidth=2, label='Optimal (0% gap)')
                plt.axhline(y=50, color='red', linestyle='--', linewidth=1, alpha=0.5, 
                           label='Theoretical worst-case (50%)')
                
                plt.xlabel('Number of Nodes (Pickup + Delivery)', fontsize=12)
                plt.ylabel('Optimality Gap (%)', fontsize=12)
                plt.title('TSP Heuristic Quality: Gap from Optimal Solution', fontsize=14, fontweight='bold')
                plt.grid(True, alpha=0.3, axis='y')
                plt.legend(fontsize=10)
                plt.tight_layout()
                
                gap_plot_path = output_dir / "tsp_optimality_gap.png"
                plt.savefig(gap_plot_path, dpi=300, bbox_inches='tight')
                print(f"✓ Saved: {gap_plot_path}")
                plt.close()
        
        # Graph 4: Log-scale time comparison (if optimal included)
        if self.include_optimal:
            optimal_data = [(r.num_nodes, r.tsp_time_seconds, r.optimal_time_seconds) 
                           for r in valid_results if r.optimal_time_seconds]
            
            if optimal_data:
                nodes, tsp_t, opt_t = zip(*optimal_data)
                
                plt.figure(figsize=(10, 6))
                plt.semilogy(nodes, tsp_t, 'o-', linewidth=2, markersize=8, label='Christofides (Polynomial)')
                plt.semilogy(nodes, opt_t, 's-', linewidth=2, markersize=8, label='Brute-Force (Exponential)')
                
                plt.xlabel('Number of Nodes (Pickup + Delivery)', fontsize=12)
                plt.ylabel('Computation Time (seconds, log scale)', fontsize=12)
                plt.title('Algorithmic Complexity Comparison (Log Scale)', fontsize=14, fontweight='bold')
                plt.grid(True, alpha=0.3, which='both')
                plt.legend(fontsize=10)
                plt.tight_layout()
                
                logscale_plot_path = output_dir / "tsp_time_logscale.png"
                plt.savefig(logscale_plot_path, dpi=300, bbox_inches='tight')
                print(f"✓ Saved: {logscale_plot_path}")
                plt.close()
    
    def print_summary(self):
        """Print summary statistics."""
        valid_results = [r for r in self.results if r.error is None]
        
        if not valid_results:
            print("No valid results to summarize")
            return
        
        print("\n" + "=" * 70)
        print("BENCHMARK SUMMARY")
        print("=" * 70)
        
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
            optimal_results = [r for r in valid_results if r.optimal_time_seconds]
            if optimal_results:
                print(f"\nBrute-force optimal performance:")
                print(f"  Tests completed: {len(optimal_results)}")
                print(f"  Min time: {min(r.optimal_time_seconds for r in optimal_results):.3f}s")
                print(f"  Max time: {max(r.optimal_time_seconds for r in optimal_results):.3f}s")
                print(f"  Avg time: {sum(r.optimal_time_seconds for r in optimal_results) / len(optimal_results):.3f}s")
                
                gap_results = [r for r in optimal_results if r.optimality_gap_percent is not None]
                if gap_results:
                    print(f"\nOptimality gaps:")
                    print(f"  Min gap: {min(r.optimality_gap_percent for r in gap_results):.2f}%")
                    print(f"  Max gap: {max(r.optimality_gap_percent for r in gap_results):.2f}%")
                    print(f"  Avg gap: {sum(r.optimality_gap_percent for r in gap_results) / len(gap_results):.2f}%")
        
        print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark TSP algorithm across all XML test files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--xml-dir",
        type=Path,
        default=Path(BACKEND_ROOT).parent / "fichiersXMLPickupDelivery",
        help="Directory containing XML test files (default: ../fichiersXMLPickupDelivery)",
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(BACKEND_ROOT) / "tools" / "benchmark_results",
        help="Directory to save results and graphs (default: tools/benchmark_results)",
    )
    
    parser.add_argument(
        "--include-optimal",
        action="store_true",
        help="Also run brute-force optimal solver (WARNING: Very slow for >10 nodes!)",
    )
    
    args = parser.parse_args()
    
    # Validate XML directory exists
    if not args.xml_dir.exists():
        print(f"Error: XML directory not found: {args.xml_dir}")
        sys.exit(1)
    
    # Run benchmark
    benchmark = TSPBenchmark(args.xml_dir, include_optimal=args.include_optimal)
    benchmark.run_all_benchmarks()
    
    # Save and visualize results
    benchmark.save_results(args.output_dir)
    benchmark.generate_graphs(args.output_dir)
    benchmark.print_summary()
    
    print(f"\n✓ All results saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
