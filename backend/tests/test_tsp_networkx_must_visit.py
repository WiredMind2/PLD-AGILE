import pytest
from types import SimpleNamespace
from typing import cast
from app.models.schemas import Tour

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
    # new interface: build a Tour-like object with deliveries containing the must nodes
    sample = cast(Tour, SimpleNamespace(courier=None, deliveries=[(must[0], must[1])]))
    tour, cost = t.solve(sample)
    assert tour is not None
    # tour is compact (list of nodes, closed). Ensure required nodes appear
    for m in must:
        assert m in tour
