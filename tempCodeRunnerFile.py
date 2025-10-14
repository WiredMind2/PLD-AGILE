import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
import networkx as nx
from utils.TSP.TSP_networkx import TSP

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))



class TestTSPInit:
    def test_init_creates_instance(self):
        tsp = TSP()
        assert tsp.graph is None


class TestBuildNetworkxMapGraph:
    @patch('utils.TSP.TSP_networkx.XMLParser')
    @patch('builtins.open')
    def test_build_graph_with_valid_xml(self, mock_open, mock_parser):
        # Mock XML data
        mock_file = MagicMock()
        mock_file.read.return_value = '<map></map>'
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Mock parsed data
        mock_intersection1 = Mock()
        mock_intersection1.id = '1'
        mock_intersection2 = Mock()
        mock_intersection2.id = '2'
        
        mock_segment = Mock()
        mock_segment.start = Mock(id='1')
        mock_segment.end = Mock(id='2')
        mock_segment.length_m = 100.0
        mock_segment.street_name = 'Test Street'
        
        mock_map_data = Mock()
        mock_map_data.intersections = [mock_intersection1, mock_intersection2]
        mock_map_data.road_segments = [mock_segment]
        
        mock_parser.parse_map.return_value = mock_map_data
        
        tsp = TSP()
        G, nodes = tsp._build_networkx_map_graph('test.xml')
        
        assert isinstance(G, nx.DiGraph)
        assert len(nodes) == 2
        assert '1' in nodes and '2' in nodes
        assert G.has_edge('1', '2')
        assert G['1']['2']['weight'] == 100.0

    @patch('utils.TSP.TSP_networkx.XMLParser')
    @patch('builtins.open')
    def test_build_graph_keeps_minimum_weight_edge(self, mock_open, mock_parser):
        mock_file = MagicMock()
        mock_file.read.return_value = '<map></map>'
        mock_open.return_value.__enter__.return_value = mock_file
        
        mock_intersection1 = Mock()
        mock_intersection1.id = '1'
        mock_intersection2 = Mock()
        mock_intersection2.id = '2'
        
        # Multiple segments between same nodes
        mock_segment1 = Mock()
        mock_segment1.start = Mock(id='1')
        mock_segment1.end = Mock(id='2')
        mock_segment1.length_m = 150.0
        mock_segment1.street_name = 'Street A'
        
        mock_segment2 = Mock()
        mock_segment2.start = Mock(id='1')
        mock_segment2.end = Mock(id='2')
        mock_segment2.length_m = 100.0
        mock_segment2.street_name = 'Street B'
        
        mock_map_data = Mock()
        mock_map_data.intersections = [mock_intersection1, mock_intersection2]
        mock_map_data.road_segments = [mock_segment1, mock_segment2]
        
        mock_parser.parse_map.return_value = mock_map_data
        
        tsp = TSP()
        G, _ = tsp._build_networkx_map_graph('test.xml')
        
        assert G['1']['2']['weight'] == 100.0


class TestBuildMetricCompleteGraph:
    def test_empty_graph_returns_empty(self):
        tsp = TSP()
        G = tsp._build_metric_complete_graph({})
        assert len(G.nodes()) == 0

    def test_single_node_returns_empty(self):
        tsp = TSP()
        graph = {'A': {'A': {'cost': 0.0}}}
        G = tsp._build_metric_complete_graph(graph)
        assert len(G.nodes()) <= 1

    def test_metric_graph_with_two_nodes(self):
        tsp = TSP()
        graph = {
            'A': {'A': {'cost': 0.0}, 'B': {'cost': 10.0}},
            'B': {'A': {'cost': 15.0}, 'B': {'cost': 0.0}}
        }
        G = tsp._build_metric_complete_graph(graph)
        
        assert len(G.nodes()) == 2
        assert G.has_edge('A', 'B')
        assert G['A']['B']['weight'] == 10.0  # min(10, 15)

    def test_metric_graph_with_disconnected_nodes(self):
        tsp = TSP()
        graph = {
            'A': {'A': {'cost': 0.0}, 'B': {'cost': float('inf')}},
            'B': {'A': {'cost': float('inf')}, 'B': {'cost': 0.0}}
        }
        G = tsp._build_metric_complete_graph(graph)
        
        # Should handle disconnected components
        assert isinstance(G, nx.Graph)


class TestSolve:
    @patch.object(TSP, '_build_networkx_map_graph')
    def test_solve_returns_tour_and_cost(self, mock_build_graph):
        # Create simple test graph
        G = nx.DiGraph()
        G.add_edge('A', 'B', weight=10)
        G.add_edge('B', 'C', weight=15)
        G.add_edge('C', 'A', weight=20)
        
        mock_build_graph.return_value = (G, ['A', 'B', 'C'])
        
        tsp = TSP()
        tour, cost = tsp.solve(nodes=['A', 'B', 'C'])
        
        assert isinstance(tour, list)
        assert isinstance(cost, float)
        assert len(tour) >= 3
        assert tour[0] == tour[-1]  # Tour should be closed

    @patch.object(TSP, '_build_networkx_map_graph')
    def test_solve_with_must_visit(self, mock_build_graph):
        G = nx.DiGraph()
        G.add_edge('A', 'B', weight=10)
        G.add_edge('B', 'C', weight=15)
        G.add_edge('C', 'A', weight=20)
        
        mock_build_graph.return_value = (G, ['A', 'B', 'C'])
        
        tsp = TSP()
        tour, cost = tsp.solve(must_visit=['A', 'B'])
        
        assert 'A' in tour
        assert 'B' in tour


class TestSolveMultiCouriers:
    @patch.object(TSP, '_build_networkx_map_graph')
    def test_multi_couriers_basic(self, mock_build_graph):
        G = nx.DiGraph()
        nodes = ['depot', 'A', 'B', 'C', 'D']
        for i, n1 in enumerate(nodes):
            for n2 in nodes[i+1:]:
                G.add_edge(n1, n2, weight=10)
                G.add_edge(n2, n1, weight=10)
        
        mock_build_graph.return_value = (G, nodes)
        
        tsp = TSP()
        result = tsp.solve_multi_couriers(2, must_visit=['A', 'B', 'C', 'D'], depot_node='depot')
        
        assert 'courier_1' in result
        assert 'courier_2' in result
        assert 'total_cost' in result
        assert isinstance(result['total_cost'], float)

    @patch.object(TSP, '_build_networkx_map_graph')
    def test_multi_couriers_empty_nodes(self, mock_build_graph):
        G = nx.DiGraph()
        mock_build_graph.return_value = (G, [])
        
        tsp = TSP()
        result = tsp.solve_multi_couriers(2, nodes=[])
        
        assert result['total_cost'] == 0.0

    @patch.object(TSP, '_build_networkx_map_graph')
    def test_multi_couriers_only_depot(self, mock_build_graph):
        G = nx.DiGraph()
        G.add_node('depot')
        mock_build_graph.return_value = (G, ['depot'])
        
        tsp = TSP()
        result = tsp.solve_multi_couriers(2, must_visit=['depot'], depot_node='depot')
        
        assert result['courier_1']['tour'] == ['depot']
        assert result['courier_1']['cost'] == 0.0


class TestExpandTourWithPaths:
    def test_expand_tour_empty(self):
        tsp = TSP()
        route, cost = tsp.expand_tour_with_paths([], {})
        assert route == []
        assert cost == 0.0

    def test_expand_tour_single_node(self):
        tsp = TSP()
        route, cost = tsp.expand_tour_with_paths(['A'], {})
        assert route == []
        assert cost == 0.0

    def test_expand_tour_valid_path(self):
        tsp = TSP()
        sp_graph = {
            'A': {
                'B': {'path': ['A', 'X', 'B'], 'cost': 25.0}
            },
            'B': {
                'C': {'path': ['B', 'Y', 'C'], 'cost': 30.0}
            }
        }
        
        tour = ['A', 'B', 'C']
        route, cost = tsp.expand_tour_with_paths(tour, sp_graph)
        
        assert 'A' in route
        assert 'B' in route
        assert 'C' in route
        assert cost == 55.0

    def test_expand_tour_missing_path_raises(self):
        tsp = TSP()
        sp_graph = {
            'A': {'B': {'path': None, 'cost': float('inf')}}
        }
        
        with pytest.raises(ValueError, match="No shortest-path from A to B"):
            tsp.expand_tour_with_paths(['A', 'B'], sp_graph)

    def test_expand_tour_consecutive_paths_merged(self):
        tsp = TSP()
        sp_graph = {
            'A': {'B': {'path': ['A', 'X', 'B'], 'cost': 10.0}},
            'B': {'C': {'path': ['B', 'Y', 'C'], 'cost': 15.0}}
        }
        
        route, cost = tsp.expand_tour_with_paths(['A', 'B', 'C'], sp_graph)
        
        # 'B' should appear only once in the route
        assert route.count('B') == 1
        assert cost == 25.0