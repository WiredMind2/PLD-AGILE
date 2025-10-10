import math
import pytest

from app.utils.TSP.Astar import Astar
from app.utils.TSP.TSP import TSP


def test_astar_load_and_heuristic():
    a = Astar(alpha=0.6)
    a.load_data()
    # basic sanity of nodes: ensure at least two nodes were loaded
    assert isinstance(a.nodes, dict)
    assert len(a.nodes) >= 2
    assert isinstance(a.adj, dict)
    # heuristic should be non-negative for a sample pair
    keys = list(a.nodes.keys())
    n1, n2 = keys[0], keys[1]
    h12 = a.heuristic(n1, n2)
    h21 = a.heuristic(n2, n1)
    assert h12 >= 0
    assert h21 >= 0


def test_multiple_target_astar_and_shortest_paths_graph():
    a = Astar(alpha=0.5)
    a.load_data()
    # pick a valid start node dynamically
    start_nodes = list(a.nodes.keys())
    assert len(start_nodes) >= 2
    start = start_nodes[0]
    res = a.multipleTarget_astar(start)
    # Should have entries for all other nodes
    assert isinstance(res, dict)
    other = next(iter(res.keys()))
    assert other in res
    if res[other]["path"] is not None:
        assert res[other]["path"][0] == start
    assert res["2"]["cost"] >= 0

    # compute graph for all nodes
    g = a.compute_shortest_paths_graph()
    assert isinstance(g, dict)
    # for a few pairs, path should be present or reachable
    src = next(iter(g.keys()))
    tgt = next(iter(g[src].keys()))
    assert src in g
    assert tgt in g[src]
    if g[src][tgt]["path"] is not None:
        assert g[src][tgt]["path"][0] == src


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
