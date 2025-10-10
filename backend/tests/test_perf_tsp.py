import time
import glob
import os
import pytest

from app.services.XMLParser import XMLParser
from app.utils.TSP.TSP import TSP


@pytest.mark.performance
def test_tsp_performance_on_all_xml_files():
    base = os.path.join(os.path.dirname(__file__), '..', '..', 'fichiersXMLPickupDelivery')
    base = os.path.abspath(base)
    pattern = os.path.join(base, '*Plan.xml')
    files = sorted(glob.glob(pattern))
    if not files:
        pytest.skip(f'No XML files found in {base}')

    results = []
    for path in files:
        fname = os.path.basename(path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        t0 = time.perf_counter()
        # parse map (and ignore deliveries for TSP) -- adapt if parser expects different root
        try:
            m = XMLParser.parse_map(content)
        except Exception as e:
            results.append((fname, 'parse_map_error', str(e)))
            print(f"{fname}: parse_map failed: {e}")
            continue
        t1 = time.perf_counter()

        # Prepare TSP / Astar
        tsp = TSP()
        # If parse_map returns Map with intersections as list, covert to nodes dict expected by Astar
        try:
            nodes = {}
            # try to extract node ids and coords robustly
            for inter in getattr(m, 'intersections', []):
                # intersection may have id, latitude, longitude
                nid = getattr(inter, 'id', None) or str(getattr(inter, 'id', None))
                lat = float(getattr(inter, 'latitude', 0.0))
                lon = float(getattr(inter, 'longitude', 0.0))
                if nid is None:
                    continue
                nodes[str(nid)] = (lat, lon)
            if not nodes:
                # no node information, skip
                results.append((fname, 'no_nodes', None))
                print(f"{fname}: no intersections found, skipping")
                continue
            tsp.astar.nodes = nodes
        except Exception as e:
            results.append((fname, 'prepare_nodes_error', str(e)))
            print(f"{fname}: prepare nodes failed: {e}")
            continue
        t2 = time.perf_counter()

        # build shortest path graph
        try:
            tsp.astar.load_data() if not tsp.astar.adj else None
            # Ensure adj is constructed from nodes; If load_data uses its own sample nodes,
            # instead call compute_shortest_paths_graph directly when adj is present.
            sp_t0 = time.perf_counter()
            sp_graph = tsp.astar.compute_shortest_paths_graph()
            sp_t1 = time.perf_counter()
        except Exception as e:
            results.append((fname, 'sp_graph_error', str(e)))
            print(f"{fname}: shortest-path graph failed: {e}")
            continue

        # solve tsp with heuristic
        try:
            solve_t0 = time.perf_counter()
            tour, cost = tsp.solve_multi_start_nn_2opt()
            solve_t1 = time.perf_counter()
        except Exception as e:
            results.append((fname, 'tsp_solve_error', str(e)))
            print(f"{fname}: tsp solve failed: {e}")
            continue

        results.append((fname,
                        'ok',
                        { 'parse_s': t1 - t0,
                          'prepare_nodes_s': t2 - t1,
                          'sp_graph_s': sp_t1 - sp_t0,
                          'solve_s': solve_t1 - solve_t0,
                          'tour_len': len(tour) if tour else 0,
                          'cost': cost
                        }))

        print(f"{fname}: parse={t1-t0:.3f}s sp_build={sp_t1-sp_t0:.3f}s solve={solve_t1-solve_t0:.3f}s tour_len={len(tour) if tour else 0} cost={cost}")

    # Print summary
    print('\nPerformance results:')
    for r in results:
        print(r)
