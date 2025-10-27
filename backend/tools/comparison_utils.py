"""Comparison and display utilities for TSP path comparison tool."""

from typing import List, Optional
from .path_utils import format_path


def display_path_info(
    label: str,
    compact_path: Optional[List[str]],
    compact_cost: Optional[float],
    expanded_path: Optional[List[str]] = None,
    expanded_cost: Optional[float] = None,
):
    """Helper to display path information consistently."""
    if compact_path and compact_cost is not None:
        print(f"\n{label} (compact: {len(compact_path)} waypoints):")
        print(f"  {format_path(compact_path, max_display=40)}")
        print(f"  Direct cost: {compact_cost:.2f}")

        if expanded_path and expanded_cost is not None:
            print(f"\n{label} (expanded: {len(expanded_path)} nodes):")
            print(f"  {format_path(expanded_path)}")
            print(f"  Full cost: {expanded_cost:.2f}")
    elif expanded_path and expanded_cost is not None:
        print(f"\n{label} ({len(expanded_path)} nodes):")
        print(f"  {format_path(expanded_path)}")
        print(f"  Cost: {expanded_cost:.2f}")


def compare_paths(
    tsp_path: List[str],
    tsp_cost: float,
    manual_path: List[str],
    manual_cost: float,
    manual_compact: Optional[List[str]] = None,
    manual_compact_cost: Optional[float] = None,
    tsp_compact: Optional[List[str]] = None,
    tsp_compact_cost: Optional[float] = None,
    optimal_path: Optional[List[str]] = None,
    optimal_cost: Optional[float] = None,
    optimal_compact: Optional[List[str]] = None,
    optimal_compact_cost: Optional[float] = None,
):
    """Display comparison between TSP and manual paths."""
    print("\n" + "=" * 70)
    print("COMPARISON RESULTS")
    print("=" * 70)

    # Display TSP paths
    display_path_info(
        "TSP Heuristic", tsp_compact, tsp_compact_cost, tsp_path, tsp_cost
    )

    # Display optimal solution if available
    display_path_info(
        "Brute-Force Optimal",
        optimal_compact,
        optimal_compact_cost,
        optimal_path,
        optimal_cost,
    )

    # Display manual paths
    display_path_info(
        "Manual Path", manual_compact, manual_compact_cost, manual_path, manual_cost
    )

    print("\n" + "-" * 70)

    # Compare manual vs heuristic
    diff_heuristic = manual_cost - tsp_cost
    print("Manual vs TSP Heuristic:")
    if diff_heuristic == 0:
        print("  ✓ IDENTICAL: Your path has the same cost as TSP!")
    elif diff_heuristic < 0:
        print(
            f"  ★ BETTER: Your path is {abs(diff_heuristic):.2f} units shorter! ({abs(diff_heuristic/tsp_cost*100):.1f}% improvement)"
        )
    else:
        print(
            f"  ✗ LONGER: Your path is {diff_heuristic:.2f} units longer ({diff_heuristic/tsp_cost*100:.1f}% more)"
        )

    # Compare manual vs optimal if available
    if optimal_cost is not None:
        diff_optimal = manual_cost - optimal_cost
        print("\nManual vs Brute-Force Optimal:")
        if diff_optimal == 0:
            print("  ✓ OPTIMAL: Your path matches the brute-force optimal solution!")
        elif diff_optimal < 0:
            print(
                f"  ★★ BETTER: Your path is {abs(diff_optimal):.2f} units shorter than optimal! (check for errors)"
            )
        else:
            print(
                f"  Gap to optimal: {diff_optimal:.2f} units ({diff_optimal/optimal_cost*100:.1f}% suboptimal)"
            )

    # Check if paths are identical
    if tsp_path == manual_path:
        print("\n✓ Expanded paths are identical to heuristic!")
    else:
        # Find common segments
        common_count = len(
            [
                i
                for i in range(min(len(tsp_path), len(manual_path)))
                if tsp_path[i] == manual_path[i]
            ]
        )
        print(f"\n  First {common_count} nodes match with heuristic in expanded paths")

    print("=" * 70)


def display_heuristic_vs_optimal_comparison(
    tour,
    compact_cost,
    optimal_tour,
    optimal_compact_cost,
    tsp_time=None,
    optimal_time=None,
):
    """Display comparison between heuristic and optimal solutions."""
    separator = "=" * 70
    print(f"\n{separator}")
    print("HEURISTIC VS OPTIMAL COMPARISON")
    print(separator)

    print(f"\nTSP Heuristic (compact: {len(tour)} waypoints):")
    print(f"  Cost: {compact_cost:.2f}")
    if tsp_time is not None:
        print(f"  Computation time: {tsp_time:.3f}s")

    print(f"\nBrute-Force Optimal (compact: {len(optimal_tour)} waypoints):")
    print(f"  Cost: {optimal_compact_cost:.2f}")
    if optimal_time is not None:
        print(f"  Computation time: {optimal_time:.3f}s")

    improvement = compact_cost - optimal_compact_cost
    if improvement > 0.01:
        print(
            f"\nOptimality Gap: {improvement:.2f} units ({improvement/optimal_compact_cost*100:.1f}% suboptimal)"
        )
    else:
        print("\n✓ Heuristic found the optimal solution!")

    # Display timing comparison if both times are available
    if tsp_time is not None and optimal_time is not None:
        speedup = optimal_time / tsp_time if tsp_time > 0 else float("inf")
        print(f"\nTiming Comparison:")
        print(f"  Heuristic is {speedup:.1f}× faster than brute-force")
        print(f"  Time saved: {optimal_time - tsp_time:.3f}s")

    print(separator)