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
        """Generate combined performance analysis graph."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Filter out failed results
        valid_results = [r for r in self.results if r.error is None]

        if not valid_results:
            print("⚠️  No valid results to plot")
            return

        # Sort by number of nodes
        valid_results.sort(key=lambda r: r.num_nodes)

        # Generate the combined graph
        self._generate_combined_graph(valid_results, output_dir)

    def _generate_combined_graph(self, valid_results: List[BenchmarkResult], output_dir: Path):
        """Generate combined graph with cost vs size and TSP vs optimal comparison."""
        
        # Create a figure with 2 subplots side by side
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
        
        # ==================== LEFT PLOT: Cost vs Problem Size ====================
        num_nodes = [r.num_nodes for r in valid_results]
        tsp_costs = [r.tsp_expanded_cost for r in valid_results]
        
        ax1.plot(num_nodes, tsp_costs, 'o-', linewidth=2.5, markersize=10, 
                color='#2E86AB', label='TSP Heuristic', markeredgecolor='black', markeredgewidth=0.5)
        
        if self.include_optimal:
            optimal_costs = [r.optimal_expanded_cost for r in valid_results if r.optimal_expanded_cost is not None]
            optimal_nodes = [r.num_nodes for r in valid_results if r.optimal_expanded_cost is not None]
            if optimal_costs:
                ax1.plot(optimal_nodes, optimal_costs, 's-', linewidth=2.5, markersize=10,
                        color='#A23B72', label='Optimal Solution', markeredgecolor='black', markeredgewidth=0.5)
        
        ax1.set_xlabel('Number of Nodes (Pickup + Delivery)', fontsize=13, fontweight='bold')
        ax1.set_ylabel('Path Length (meters)', fontsize=13, fontweight='bold')
        ax1.set_title('Cost vs Problem Size', fontsize=15, fontweight='bold', pad=15)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.legend(fontsize=11, loc='upper left', framealpha=0.9)
        
        # Add value labels on points
        for i, (x, y) in enumerate(zip(num_nodes, tsp_costs)):
            ax1.annotate(f'{y:.0f}m', (x, y), textcoords="offset points", 
                        xytext=(0,8), ha='center', fontsize=8, color='#2E86AB', fontweight='bold')
        
        # ==================== RIGHT PLOT: TSP vs Optimal Detailed ====================
        if self.include_optimal:
            # Filter to only include results with optimal values
            filtered_data = [(r, r.tsp_expanded_cost, r.optimal_expanded_cost) 
                            for r in valid_results 
                            if r.optimal_expanded_cost is not None]
            
            if filtered_data:
                test_labels = []
                tsp_vals = []
                opt_vals = []
                gaps = []
                
                for r, tsp_val, opt_val in filtered_data:
                    # Create compact label
                    map_name = r.map_file.replace('Plan.xml', '').replace('.xml', '')
                    req_name = r.request_file.replace('demande', '').replace('.xml', '')
                    test_labels.append(f"{map_name}\n{req_name}")
                    tsp_vals.append(tsp_val)
                    opt_vals.append(opt_val)
                    
                    # Calculate gap percentage
                    if opt_val > 0:
                        gap = ((tsp_val - opt_val) / opt_val) * 100
                        gaps.append(gap)
                    else:
                        gaps.append(0)
                
                x_pos = range(len(test_labels))
                width = 0.35
                
                # Create grouped bar chart
                bars1 = ax2.bar([x - width/2 for x in x_pos], tsp_vals, width, 
                              label='TSP Algorithm', color='#2E86AB', alpha=0.85, 
                              edgecolor='black', linewidth=1.2)
                bars2 = ax2.bar([x + width/2 for x in x_pos], opt_vals, width, 
                              label='Optimal Solution', color='#A23B72', alpha=0.85, 
                              edgecolor='black', linewidth=1.2)
                
                # Add percentage gap labels above bars
                for i, (x, gap) in enumerate(zip(x_pos, gaps)):
                    y_pos = max(tsp_vals[i], opt_vals[i]) * 1.05
                    if gap > 0.01:  # Only show if gap is meaningful
                        color = '#D32F2F' if gap > 5 else '#F57C00'
                        ax2.text(x, y_pos, f'+{gap:.1f}%',
                               ha='center', va='bottom', fontsize=10, 
                               color=color, fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                       edgecolor=color, alpha=0.8))
                    elif abs(gap) < 0.01:
                        ax2.text(x, y_pos, 'OPTIMAL',
                               ha='center', va='bottom', fontsize=9, 
                               color='#388E3C', fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                       edgecolor='#388E3C', alpha=0.8))
                
                # Add value labels on bars
                for bars in [bars1, bars2]:
                    for bar in bars:
                        height = bar.get_height()
                        if height > 0:
                            ax2.text(bar.get_x() + bar.get_width()/2., height * 0.5,
                                   f'{height:.0f}m',
                                   ha='center', va='center', fontsize=9, 
                                   color='white', fontweight='bold',
                                   bbox=dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.6))
                
                ax2.set_xlabel('Test Cases', fontsize=13, fontweight='bold')
                ax2.set_ylabel('Path Length (meters)', fontsize=13, fontweight='bold')
                ax2.set_title('TSP vs Optimal: Detailed Comparison', fontsize=15, fontweight='bold', pad=15)
                ax2.set_xticks(x_pos)
                ax2.set_xticklabels(test_labels, rotation=0, ha='center', fontsize=10)
                ax2.legend(fontsize=11, loc='upper left', framealpha=0.9)
                ax2.grid(True, alpha=0.3, axis='y', linestyle='--')
            else:
                ax2.text(0.5, 0.5, 'No optimal solutions available\nfor comparison',
                        ha='center', va='center', fontsize=14, transform=ax2.transAxes)
                ax2.set_xticks([])
                ax2.set_yticks([])
        else:
            ax2.text(0.5, 0.5, 'Optimal solver not included',
                    ha='center', va='center', fontsize=14, transform=ax2.transAxes)
            ax2.set_xticks([])
            ax2.set_yticks([])
        
        # Overall title
        fig.suptitle('TSP Heuristic Performance Analysis', fontsize=17, fontweight='bold', y=0.98)
        
        plt.tight_layout(rect=(0, 0, 1, 0.96))
        combined_plot = output_dir / "tsp_performance_analysis.png"
        plt.savefig(combined_plot, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {combined_plot}")
        plt.close()
