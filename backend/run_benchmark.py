"""Run TSP benchmark directly"""
from tools.benchmark_core import TSPBenchmark
from pathlib import Path

xml_dir = Path(r'C:\Users\willi\Documents\INSA\AGILE\PLD-AGILE\fichiersXMLPickupDelivery')
output_dir = Path(r'C:\Users\willi\Documents\INSA\AGILE\PLD-AGILE\backend\tools\benchmark_results')

print("="*70)
print("TSP HEURISTIC QUALITY BENCHMARK")
print("="*70)
print(f"XML Directory: {xml_dir}")
print(f"Output Directory: {output_dir}")
print(f"Include optimal: True")
print("="*70)
print()

benchmark = TSPBenchmark(xml_dir, include_optimal=True)
benchmark.run_all_benchmarks()

if benchmark.results:
    # Save results to CSV
    import csv
    from tools.benchmark_visualization import BenchmarkVisualizer
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    csv_file = output_dir / "benchmark_results.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Map', 'Request', 'Deliveries', 'Nodes', 'TSP Time (s)', 'TSP Cost', 
                        'TSP Expanded', 'Optimal Time (s)', 'Optimal Cost', 'Optimal Expanded', 
                        'Gap (%)', 'Error'])
        for r in benchmark.results:
            writer.writerow([
                r.map_file, r.request_file, r.num_deliveries, r.num_nodes,
                f"{r.tsp_time_seconds:.4f}", f"{r.tsp_cost:.2f}", f"{r.tsp_expanded_cost:.2f}",
                f"{r.optimal_time_seconds:.4f}" if r.optimal_time_seconds else '',
                f"{r.optimal_cost:.2f}" if r.optimal_cost else '',
                f"{r.optimal_expanded_cost:.2f}" if r.optimal_expanded_cost else '',
                f"{r.optimality_gap_percent:.2f}" if r.optimality_gap_percent is not None else '',
                r.error or ''
            ])
    
    # Generate visualization graphs
    visualizer = BenchmarkVisualizer(benchmark.results, include_optimal=True)
    visualizer.generate_graphs(output_dir)
    
    print()
    print("="*70)
    print("RESULTS SAVED")
    print("="*70)
    print(f"CSV: {csv_file}")
    print(f"Graphs: {output_dir}")
else:
    print("⚠️  No valid results")
