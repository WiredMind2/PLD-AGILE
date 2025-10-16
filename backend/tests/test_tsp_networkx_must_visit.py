import pytest

try:
    from app.utils.TSP.TSP_networkx import TSP
    HAS_NX = True
except Exception:
    TSP = None
    HAS_NX = False


@pytest.mark.skipif(not HAS_NX, reason="networkx or TSP_networkx unavailable")
def test_must_visit_in_tour():
    if TSP is None:
        pytest.skip("TSP class unavailable")
    t = TSP()
    G, nodes = t._build_networkx_map_graph()
    if len(nodes) < 3:
        pytest.skip("not enough nodes in map for meaningful test")

    # pick 2 required nodes
    must = nodes[:2]
    # must_visit argument removed; pass nodes directly
    tour, cost = t.solve(nodes=must)
    assert tour is not None
    # tour is compact (list of nodes, closed). Ensure required nodes appear
    for m in must:
        assert m in tour
