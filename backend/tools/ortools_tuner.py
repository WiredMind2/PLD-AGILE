"""Simple tuner to run OR-Tools with different search parameter choices.

Saves a CSV with (first_solution, local_search, time_limit, compact_cost, time) for each run.
"""
import os
import sys
from time import perf_counter
import csv

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(HERE)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.utils.TSP.TSP_ortools import ORToolsTSP
from app.utils.TSP.TSP_networkx import TSP as NX_TSP


def main():
    nx_tsp = NX_TSP()
    G, _ = nx_tsp._build_networkx_map_graph()
    nodes = list(G.nodes())[:8]
    pd_pairs = []

    param_grid = [
        ('PATH_CHEAPEST_ARC', None),
        ('PATH_CHEAPEST_ARC', 'GUIDED_LOCAL_SEARCH'),
        ('PARALLEL_CHEAPEST_INSERTION', 'GUIDED_LOCAL_SEARCH'),
    ]

    out_csv = os.path.join(HERE, 'ortools_tuner_results.csv')
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['first_solution', 'local_search', 'time_limit_s', 'compact_cost', 'time_s'])
        for fs, ls in param_grid:
            search_params = {'first_solution': fs}
            if ls:
                search_params['local_search'] = ls
            print('Running with', search_params)
            ort = ORToolsTSP()
            t0 = perf_counter()
            try:
                tour, cost, _ = ort.solve(nodes=nodes, pickup_delivery_pairs=pd_pairs, time_limit_s=10, search_params=search_params)
                t1 = perf_counter()
                writer.writerow([fs, ls or '', 10, cost, t1 - t0])
                print('OK:', cost, 'time', t1 - t0)
            except Exception as e:
                t1 = perf_counter()
                writer.writerow([fs, ls or '', 10, 'ERROR:'+str(e), t1 - t0])
                print('ERROR:', e)


if __name__ == '__main__':
    main()
