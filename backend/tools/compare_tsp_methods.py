"""Compare NetworkX-based TSP and OR-Tools TSP on a sample node set.


Run this from the `backend` folder (it expects the package `app` to be importable).

Usage (from workspace root):
    cd backend
    .venv\\Scripts\\python.exe tools\\compare_tsp_methods.py

The script:
- builds a small nodes_list from the map (first N nodes)
- optionally creates simple pickup-delivery pairs from that list
- runs NetworkX solver and OR-Tools solver (if installed)
- times each and computes expanded (node-level) cost using NetworkX shortest paths
"""

import os
import sys
from time import perf_counter
from typing import List, Tuple

# Ensure backend directory is on sys.path so imports like `app.*` work when run from backend
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(HERE)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

import networkx as nx
import logging

# configure logging: write to console and to a file in tools/
LOG_PATH = os.path.join(HERE, 'compare_tsp_methods.log')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH, encoding='utf-8')])
logger = logging.getLogger(__name__)

try:
    from app.utils.TSP.TSP_networkx import TSP as NX_TSP
except Exception as e:
    print('Failed to import NetworkX TSP implementation:', e)
    raise

try:
    from app.utils.TSP.TSP_ortools import TSP as ORToolsTSP  # type: ignore
    has_ortools = True
except Exception as e:
    ORToolsTSP = None  # type: ignore
    has_ortools = False
    logger.exception('Failed to import OR-Tools TSP module (ORToolsTSP). OR-Tools may not be installed: %s', e)


def sample_nodes(G: nx.DiGraph, k: int) -> List[str]:
    nodes = list(G.nodes())
    if len(nodes) <= k:
        return nodes
    return nodes[:k]


def simple_pd_pairs(nodes: List[str]) -> List[Tuple[str, str]]:
    # pair first half pickups with second half deliveries when possible
    if len(nodes) < 4:
        return []
    mid = len(nodes) // 2
    pairs = []
    for i in range(min(mid, len(nodes)-mid)):
        pairs.append((nodes[i], nodes[mid + i]))
    return pairs


def expand_compact_tour(G: nx.DiGraph, tour: List[str]) -> Tuple[List[str], float]:
    # Expand compact tour into full node-level path using shortest_path
    if not tour or len(tour) < 2:
        return [], 0.0
    full = []
    total = 0.0
    for i in range(len(tour) - 1):
        u, v = tour[i], tour[i+1]
        path = nx.shortest_path(G, u, v, weight='weight')
        # compute cost
        cost = 0.0
        for j in range(len(path)-1):
            cost += G[path[j]][path[j+1]]['weight']
        if full and full[-1] == path[0]:
            full.extend(path[1:])
        else:
            full.extend(path)
        total += cost
    return full, total


def main():
    tsp_nx = NX_TSP()
    G_map, all_nodes = tsp_nx._build_networkx_map_graph()

    # choose sample size
    SAMPLE_K = 8
    nodes = sample_nodes(G_map, SAMPLE_K)
    pd_pairs = simple_pd_pairs(nodes)

    print('Sample nodes:', nodes)
    print('Pickup-delivery pairs:', pd_pairs)

    # Run NetworkX solver
    t0 = perf_counter()
    # Build a Tour-like object expected by the new NetworkX solver signature
    from types import SimpleNamespace
    sample_tour = SimpleNamespace(deliveries=pd_pairs)

    try:
        tour_nx, cost_nx = tsp_nx.solve(sample_tour)
    except TypeError:
        # fallback to old signature if the solver still expects nodes + pairs
        try:
            tour_nx, cost_nx = tsp_nx.solve(nodes=nodes, pickup_delivery_pairs=pd_pairs)
        except Exception as e:
            print('NetworkX solver failed:', e)
            return
    except Exception as e:
        print('NetworkX solver failed:', e)
        return
    t1 = perf_counter()
    time_nx = t1 - t0

    full_nx, full_cost_nx = expand_compact_tour(G_map, tour_nx)

    print('\nNetworkX Christofides:')
    print('  time: {:.3f}s'.format(time_nx))
    print('  compact cost:', cost_nx)
    print('  compact tour:', tour_nx)
    print('  expanded cost:', full_cost_nx)

    # Run OR-Tools solver if available
    if has_ortools and ORToolsTSP is not None:
        ort = ORToolsTSP()
        t0 = perf_counter()
        # OR-Tools wrapper may implement different signatures. Try the new Tour signature first.
        try:
            tour_or, cost_or, sp_paths = ort.solve(sample_tour, time_limit_s=30)  # type: ignore
        except TypeError:
            try:
                tour_or, cost_or, sp_paths = ort.solve(nodes=nodes, pickup_delivery_pairs=pd_pairs, time_limit_s=30)  # type: ignore
            except Exception as e:
                print('\nOR-Tools solver failed:', e)
                return
        except Exception as e:
            print('\nOR-Tools solver failed:', e)
            return
        t1 = perf_counter()
        time_or = t1 - t0

        # Expand OR-Tools compact tour using networkx shortest paths (fallback)
        full_or, full_cost_or = expand_compact_tour(G_map, tour_or)

        print('\nOR-Tools Routing:')
        print('  time: {:.3f}s'.format(time_or))
        print('  compact cost:', cost_or)
        print('  compact tour:', tour_or)
        print('  expanded cost:', full_cost_or)
    else:
        print('\nOR-Tools not available; skipping OR-Tools run. Install ortools in the backend venv to enable it.')


if __name__ == '__main__':
    main()
