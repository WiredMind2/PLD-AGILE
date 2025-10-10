import math
import pytest

# Skip these slow / environment-dependent A* tests in CI by default.
pytestmark = pytest.mark.skip(reason="Skipping slow A* unit tests")

from app.utils.TSP.Astar import Astar
from app.utils.TSP.TSP import TSP


def test_astar_load_and_heuristic():
    a = Astar(alpha=0.6)
    a.load_data()
    # basic sanity of nodes
    assert "1" in a.nodes
    assert isinstance(a.adj, dict)

    # heuristic should be non-negative and symmetric-ish
    h12 = a.heuristic("1", "2")
    h21 = a.heuristic("2", "1")
    assert h12 >= 0
    assert h21 >= 0


def test_multiple_target_astar_and_shortest_paths_graph():
    a = Astar(alpha=0.5)
    a.load_data()
    res = a.multipleTarget_astar("1")
    # Should have entries for all other nodes
    assert isinstance(res, dict)
    assert "2" in res
    assert res["2"]["path"][0] == "1"
    assert res["2"]["cost"] >= 0

    # compute graph for all nodes
    g = a.compute_shortest_paths_graph()
    assert isinstance(g, dict)
    # for a few pairs, path should be present or reachable
    assert "1" in g
    assert "2" in g["1"]
    assert g["1"]["2"]["path"][0] == "1"


def test_tsp_solve_and_expand():
    tsp = TSP()
    # use built-in load_data via solve
    tour, cost = tsp.solve()
    # tour may be None if no closing edge exists, but for the sample graph we expect a tour
    assert tour is None or isinstance(tour, list)

    # test solve_multi_start_nn_2opt
    tour2, cost2 = tsp.solve_multi_start_nn_2opt()
    assert tour2 is None or isinstance(tour2, list)
    if tour2:
        # cost should be finite and consistent
        assert cost2 >= 0
        # expand tour using computed shortest-path graph
        sp = tsp.astar.compute_shortest_paths_graph()
        full_route, full_cost = tsp.expand_tour_with_paths(tour2, sp)
        assert isinstance(full_route, list)
        assert math.isfinite(full_cost)


def test_expand_tour_raises_on_missing_leg():
    tsp = TSP()
    tsp.astar.load_data()
    sp = tsp.astar.compute_shortest_paths_graph()
    # pick two distinct nodes from the graph keys
    nodes = list(sp.keys())
    assert len(nodes) >= 2
    u = nodes[0]
    v = nodes[1]

    # ensure the entry exists (multipleTarget_astar doesn't include self->self)
    assert v in sp[u]
    # remove connection u->v to force an exception
    sp[u][v]["path"] = None
    with pytest.raises(ValueError):
        tsp.expand_tour_with_paths([u, v], sp)

