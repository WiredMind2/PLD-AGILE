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

import argparse
import sys
from pathlib import Path

# Ensure backend root is on sys.path
import os
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from .benchmark_core import TSPBenchmark
from .benchmark_visualization import BenchmarkVisualizer


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
    visualizer = BenchmarkVisualizer(benchmark.results, include_optimal=args.include_optimal)
    visualizer.generate_graphs(args.output_dir)
    benchmark.print_summary()
    
    print(f"\n✓ All results saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
