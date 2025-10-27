"""Visualization and graphing utilities for TSP benchmarks."""

from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for saving figures

from .benchmark_types import BenchmarkResult


class BenchmarkVisualizer:
    """Handles generation of performance analysis graphs."""

    def __init__(self, results: List[BenchmarkResult], include_optimal: bool = False):
        self.results = results
        self.include_optimal = include_optimal

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
