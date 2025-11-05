import types
from types import SimpleNamespace
import networkx as nx

from app.utils.TSP.TSP_base import TSPBase
from app.utils.TSP.TSP_solver import TSP


def test_build_networkx_map_graph_cache_and_bad_length(monkeypatch, tmp_path):
    """Test TSPBase building with a monkeypatched XMLParser returning a
    road segment with a non-numeric length to exercise the float exception path,
    and then test the cached-graph return path.
    """
    base = TSPBase()

    # Create a fake map_data with intersections and a bad-length road segment
    fake_map = SimpleNamespace(
        intersections=['N1', 'N2'],
        road_segments=[
            SimpleNamespace(start='N1', end='N2', length_m='not-a-number', street_name='Main')
        ]
    )

    # Monkeypatch the XMLParser.parse_map used inside _build_networkx_map_graph
    from app.services.XMLParser import XMLParser
    monkeypatch.setattr(XMLParser, 'parse_map', lambda xml_text: fake_map, raising=True)

    # Create the dummy xml file so the function will read it (our parse_map ignores content)
    dummy_file = tmp_path / 'dummy.xml'
    dummy_file.write_text('<map></map>', encoding='utf-8')

    # Call with a dummy path - parse_map will be called and return our fake_map
    G, nodes = base._build_networkx_map_graph(xml_file_path=str(dummy_file))
    assert isinstance(G, nx.DiGraph)
    assert 'N1' in nodes and 'N2' in nodes

    # Now call again without xml_file_path to trigger cache return branch
    G2, nodes2 = base._build_networkx_map_graph()
    assert G2 is G
    assert nodes2 == list(G.nodes())


def test_expand_tour_raises_on_missing_path():
    base = TSPBase()
    # sp_graph missing path entry between A->B
    sp_graph = {'A': {'B': {'path': None, 'cost': float('inf')}}}
    try:
        base.expand_tour_with_paths(['A', 'B'], sp_graph)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_compute_shortest_paths_handles_dijkstra_exception(monkeypatch):
    tsp = TSP()
    # Prepare a tiny graph
    G = nx.DiGraph()
    G.add_node('A')
    # Monkeypatch networkx single_source_dijkstra to raise
    import networkx as nx_mod
    monkeypatch.setattr(nx_mod, 'single_source_dijkstra', lambda *args, **kwargs: (_ for _ in ()).throw(Exception('boom')))

    sp = tsp._compute_shortest_paths(G, ['A'])
    assert 'A' in sp
    assert sp['A']['A']['path'] == ['A']
    assert sp['A']['A']['cost'] == 0.0
