"""Setup utilities for TSP path comparison tool."""

import argparse
from app.utils.TSP.TSP_networkx import TSP


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare manual path with TSP solution"
    )
    parser.add_argument("--map", type=str, default=None, help="Map XML file to use")
    parser.add_argument(
        "--req",
        "--delivery",
        type=str,
        default=None,
        dest="req",
        help="Delivery requests XML file (contains <livraison> elements)",
    )
    parser.add_argument(
        "--nodes",
        type=int,
        default=0,
        help="Limit number of nodes (0 = use all from requests)",
    )
    parser.add_argument(
        "--optimal",
        action="store_true",
        help="Compute optimal solution using brute-force (slow, only for small instances ≤10 nodes)",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Prompt for manual path input (otherwise skip manual path)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recomputation of optimal solution (ignore cache)",
    )
    return parser.parse_args()


def initialize_tsp_solver(args):
    """Initialize and configure the TSP solver."""
    tsp = TSP()

    # Load map
    if args.map:
        print(f"\nLoading map from: {args.map}")
        orig_builder = tsp._build_networkx_map_graph
        tsp._build_networkx_map_graph = (
            lambda xml_file_path=None, p=args.map: orig_builder(p)
        )
    else:
        print("\nUsing embedded default map")

    return tsp


def print_header():
    """Print the tool header."""
    print("=" * 70)
    print("TSP PATH COMPARISON TOOL")
    print("=" * 70)