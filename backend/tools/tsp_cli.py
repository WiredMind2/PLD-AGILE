"""TSP Interactive CLI: Interactive command-line interface for TSP operations."""

import os
import sys
from pathlib import Path
from typing import Optional, cast
from types import SimpleNamespace

# Ensure backend root is on sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.utils.TSP.TSP_networkx import TSP
from app.services.XMLParser import XMLParser
from app.models.schemas import Tour

from tsp_core import build_sp_graph, expand_manual_path, input_manual_path, format_path, compute_optimal_brute_force
from tsp_benchmark import TSPBenchmark, BenchmarkVisualizer


def get_user_choice(options: list, prompt: str) -> int:
    """Get user choice from menu."""
    while True:
        print(f"\n{prompt}")
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        try:
            choice = int(input("Enter choice (number): ").strip())
            if 1 <= choice <= len(options):
                return choice
            print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a valid number.")


def get_file_path(prompt: str, file_type: str, default_dir: Optional[Path] = None) -> Optional[str]:
    """Get file path from user."""
    while True:
        path = input(f"{prompt} (or 'skip' to skip): ").strip()
        if path.lower() == 'skip':
            return None
        if path:
            full_path = Path(path)
            if not full_path.is_absolute() and default_dir:
                full_path = default_dir / full_path
            if full_path.exists():
                return str(full_path)
            print(f"{file_type} file not found: {full_path}")
        else:
            print("Please enter a valid path or 'skip'.")


def get_yes_no(prompt: str, default: bool = False) -> bool:
    """Get yes/no answer from user."""
    while True:
        response = input(f"{prompt} (y/n) [{'Y' if default else 'y'}/{'n' if not default else 'N'}]: ").strip().lower()
        if not response:
            return default
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("Please enter 'y' or 'n'.")


def run_interactive_benchmark():
    """Run interactive benchmark."""
    print("\n=== TSP Benchmark ===")

    xml_dir = Path(BACKEND_ROOT).parent / "fichiersXMLPickupDelivery"
    if not xml_dir.exists():
        print(f"Default XML directory not found: {xml_dir}")
        xml_dir_str = input("Enter XML directory path: ").strip()
        if xml_dir_str:
            xml_dir = Path(xml_dir_str)
            if not xml_dir.exists():
                print("Directory not found.")
                return

    output_dir = Path(BACKEND_ROOT) / "tools" / "benchmark_results"
    output_dir_str = input(f"Enter output directory (default: {output_dir}): ").strip()
    if output_dir_str:
        output_dir = Path(output_dir_str)

    include_optimal = get_yes_no("Include optimal solver comparison? (slow for large instances)")

    print(f"\nRunning benchmarks with XML dir: {xml_dir}")
    print(f"Output dir: {output_dir}")
    print(f"Include optimal: {include_optimal}")

    if get_yes_no("Proceed with benchmark?"):
        benchmark = TSPBenchmark(xml_dir, include_optimal)
        benchmark.run_all_benchmarks()
        visualizer = BenchmarkVisualizer(benchmark.results, include_optimal)
        visualizer.generate_graphs(output_dir)
        benchmark.print_summary()
        print(f"\nResults saved to {output_dir}")
    else:
        print("Benchmark cancelled.")


def run_interactive_compare():
    """Run interactive comparison."""
    print("\n=== TSP Path Comparison ===")

    xml_dir = Path(BACKEND_ROOT).parent / "fichiersXMLPickupDelivery"

    map_path = get_file_path("Enter map file path", "Map", xml_dir)
    if not map_path:
        print("Map file required.")
        return

    req_path = get_file_path("Enter request file path", "Request", xml_dir)
    if not req_path:
        print("Request file required.")
        return

    tsp = TSP()
    if map_path:
        orig_builder = tsp._build_networkx_map_graph
        tsp._build_networkx_map_graph = lambda xml_file_path=None, p=map_path: orig_builder(p)

    G_map, all_nodes = tsp._build_networkx_map_graph(None)
    deliveries = []
    nodes_list = list(all_nodes)

    if req_path:
        with open(req_path, "r", encoding="utf-8") as f:
            deliveries = XMLParser.parse_deliveries(f.read())
        nodes_from_reqs = []
        for d in deliveries:
            nodes_from_reqs.extend([d.pickup_addr, d.delivery_addr])
        nodes_list = [n for n in nodes_from_reqs if n in all_nodes]

    tour_pairs = [(d.pickup_addr, d.delivery_addr) for d in deliveries] if deliveries else []
    if tour_pairs:
        tour, compact_cost = tsp.solve(Tour(courier="test", deliveries=tour_pairs))
    else:
        # For nodes-only, create a tour with empty deliveries but somehow pass nodes
        # This might not work, let's skip for now
        print("No deliveries found, skipping TSP solve.")
        return
    sp_graph = build_sp_graph(G_map, nodes_list)
    full_route, expanded_cost = tsp.expand_tour_with_paths(tour, sp_graph)

    print(f"\nTSP Result:")
    print(f"Compact tour: {format_path(tour)} Cost: {compact_cost:.2f}")
    print(f"Expanded route: {format_path(full_route)} Cost: {expanded_cost:.2f}")

    # Manual path
    if get_yes_no("Compare with manual path?"):
        manual_compact = input_manual_path(set(all_nodes))
        if manual_compact:
            manual_expanded, manual_cost = expand_manual_path(manual_compact, G_map)
            print(f"\nManual path: {format_path(manual_expanded)} Cost: {manual_cost:.2f}")
            diff = manual_cost - expanded_cost
            print(f"Manual vs TSP: {'Better' if diff < 0 else 'Worse'} by {abs(diff):.2f}")

    # Optimal
    if len(nodes_list) <= 10 and get_yes_no("Compare with optimal? (may be slow)"):
        optimal_tour, optimal_cost = compute_optimal_brute_force(map_path, req_path, len(nodes_list))
        if optimal_tour:
            print(f"\nOptimal: {format_path(optimal_tour)} Cost: {optimal_cost:.2f}")
            diff_opt = expanded_cost - optimal_cost
            print(f"TSP vs Optimal: {'Better' if diff_opt < 0 else 'Worse'} by {abs(diff_opt):.2f}")


def run_interactive_optimal():
    """Run interactive optimal computation."""
    print("\n=== Compute Optimal Tour ===")

    xml_dir = Path(BACKEND_ROOT).parent / "fichiersXMLPickupDelivery"

    map_path = get_file_path("Enter map file path", "Map", xml_dir)
    if not map_path:
        print("Map file required.")
        return

    req_path = get_file_path("Enter request file path", "Request", xml_dir)
    if not req_path:
        print("Request file required.")
        return

    nodes_limit = input("Limit nodes (press Enter for no limit): ").strip()
    nodes_limit = int(nodes_limit) if nodes_limit.isdigit() else None

    start_node = input("Start node (press Enter for auto): ").strip() or None

    print("Computing optimal tour...")
    tour, cost = compute_optimal_brute_force(map_path, req_path, nodes_limit or 0, start_node)

    if tour:
        print(f"\nOptimal tour: {format_path(tour)} Cost: {cost:.2f}")
    else:
        print("No solution found.")


def run_interactive_demo():
    """Run interactive demo."""
    print("\n=== TSP Demo ===")

    xml_dir = Path(BACKEND_ROOT).parent / "fichiersXMLPickupDelivery"

    map_path = get_file_path("Enter map file path", "Map", xml_dir)
    req_path = get_file_path("Enter request file path (optional)", "Request", xml_dir)

    nodes_limit = input("Limit nodes (press Enter for no limit): ").strip()
    nodes_limit = int(nodes_limit) if nodes_limit.isdigit() else None

    tsp = TSP()
    if map_path:
        orig_builder = tsp._build_networkx_map_graph
        tsp._build_networkx_map_graph = lambda xml_file_path=None, p=map_path: orig_builder(p)

    G_map, all_nodes = tsp._build_networkx_map_graph(None)
    nodes_list = list(all_nodes)[:nodes_limit] if nodes_limit else list(all_nodes)

    if req_path:
        with open(req_path, "r", encoding="utf-8") as f:
            deliveries = XMLParser.parse_deliveries(f.read())
        tour_pairs = [(d.pickup_addr, d.delivery_addr) for d in deliveries]
        sample_tour = cast(Tour, SimpleNamespace(deliveries=tour_pairs))
        tour, compact_cost = tsp.solve(sample_tour)
    else:
        # For nodes-only demo
        print("No request file provided, using node list.")
        sample_tour = cast(Tour, SimpleNamespace(deliveries=[]))
        tour, compact_cost = tsp.solve(sample_tour)

    sp_graph = build_sp_graph(G_map, nodes_list)
    full_route, expanded_cost = tsp.expand_tour_with_paths(tour, sp_graph)

    print(f"\nDemo Result:")
    print(f"Tour: {format_path(tour)} Cost: {compact_cost:.2f}")
    print(f"Expanded: {len(full_route)} nodes, Cost: {expanded_cost:.2f}")


def main():
    """Main interactive CLI."""
    print("=== TSP Toolkit Interactive CLI ===")
    print("Welcome to the TSP Toolkit!")

    while True:
        choice = get_user_choice([
            "Run TSP Benchmarks",
            "Compare TSP with Manual/Optimal paths",
            "Compute Optimal Tour",
            "Run TSP Demo",
            "Exit"
        ], "Select an option:")

        if choice == 1:
            run_interactive_benchmark()
        elif choice == 2:
            run_interactive_compare()
        elif choice == 3:
            run_interactive_optimal()
        elif choice == 4:
            run_interactive_demo()
        elif choice == 5:
            print("Goodbye!")
            break

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()