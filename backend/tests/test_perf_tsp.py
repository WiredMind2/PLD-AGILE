import time
import os
import json
import pytest
from pathlib import Path

from app.services.XMLParser import XMLParser
from app.utils.TSP.TSP_networkx import TSP

# Skip performance tests - uses old TSP API that's been replaced
# TODO: Update to use TSP_networkx API
pytest.skip('Performance tests use deprecated TSP API. Needs update to TSP_networkx.', allow_module_level=True)


@pytest.mark.performance
def test_tsp_performance_on_all_xml_files() -> None:
    project_root = Path(__file__).resolve().parents[2]
    xml_dir = project_root / 'fichiersXMLPickupDelivery'
    if not xml_dir.exists():
        pytest.skip(f'No XML directory found at {xml_dir}')

    files = sorted(xml_dir.glob('*Plan.xml'))
    if not files:
        pytest.skip(f'No XML files found in {xml_dir}')

    results = []
    for path in files:
        fname = path.name
        content = path.read_text(encoding='utf-8')

        entry = {
            'file': fname,
            'status': 'unknown',
            'parse_s': None,
            'prepare_nodes_s': None,
            'sp_graph_s': None,
            'solve_s': None,
            'tour_len': None,
            'cost': None,
            'error': None,
        }

        t0 = time.perf_counter()
        try:
            m = XMLParser.parse_map(content)
        except Exception as e:
            entry.update(status='parse_map_error', error=str(e))
            results.append(entry)
            print(f"{fname}: parse_map failed: {e}")
            continue
        t1 = time.perf_counter()

        tsp = TSP()
        try:
            nodes = {}
            for inter in getattr(m, 'intersections', []):
                nid = getattr(inter, 'id', None)
                lat = float(getattr(inter, 'latitude', 0.0))
                lon = float(getattr(inter, 'longitude', 0.0))
                if nid is None:
                    continue
                nodes[str(nid)] = (lat, lon)
            if not nodes:
                entry.update(status='no_nodes')
                results.append(entry)
                print(f"{fname}: no intersections found, skipping")
                continue
            tsp.astar.nodes = nodes
        except Exception as e:
            entry.update(status='prepare_nodes_error', error=str(e))
            results.append(entry)
            print(f"{fname}: prepare nodes failed: {e}")
            continue
        t2 = time.perf_counter()

        # build shortest path graph
        try:
            # If astar.adj already present, skip load_data
            if not getattr(tsp.astar, 'adj', None):
                # construct adjacency/edges based on nodes if available
                tsp.astar.load_data()
            sp_t0 = time.perf_counter()
            sp_graph = tsp.astar.compute_shortest_paths_graph()
            sp_t1 = time.perf_counter()
        except Exception as e:
            entry.update(status='sp_graph_error', error=str(e))
            results.append(entry)
            print(f"{fname}: shortest-path graph failed: {e}")
            continue

        # solve tsp with heuristic
        try:
            solve_t0 = time.perf_counter()
            tour, cost = tsp.solve_multi_start_nn_2opt()
            solve_t1 = time.perf_counter()
        except Exception as e:
            entry.update(status='tsp_solve_error', error=str(e))
            results.append(entry)
            print(f"{fname}: tsp solve failed: {e}")
            continue

        entry.update(
            status='ok',
            parse_s=(t1 - t0),
            prepare_nodes_s=(t2 - t1),
            sp_graph_s=(sp_t1 - sp_t0),
            solve_s=(solve_t1 - solve_t0),
            tour_len=(len(tour) if tour else 0),
            cost=cost,
        )
        results.append(entry)

        print(f"{fname}: parse={entry['parse_s']:.3f}s sp_build={entry['sp_graph_s']:.3f}s solve={entry['solve_s']:.3f}s tour_len={entry['tour_len']} cost={entry['cost']}")

    # Write results to JSON for later analysis. Allow override via PERF_OUT env var.
    project_root = Path(__file__).resolve().parents[2]
    default_out = project_root / 'backend' / 'perf_tsp_results.json'
    out_path = Path(os.environ.get('PERF_OUT', str(default_out)))
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open('w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f'Wrote performance results to {out_path}')
    except Exception as e:
        print(f'Failed to write perf results to {out_path}: {e}')

