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
        # Mock XML content
        mock_open.return_value.__enter__.return_value.read.return_value = '<map></map>'
        
        # Mock parsed data
        mock_intersection1 = Mock(id='1')
        mock_intersection2 = Mock(id='2')
        mock_segment = Mock(start='1', end='2', length_m=100.0, street_name='Main St')
        
        mock_map_data = Mock()
        mock_map_data.intersections = [mock_intersection1, mock_intersection2]
        mock_map_data.road_segments = [mock_segment]
        
        mock_parser.parse_map.return_value = mock_map_data
        
        tsp = TSP()
        G, nodes = tsp._build_networkx_map_graph('test.xml')
        
        assert isinstance(G, nx.DiGraph)
        assert '1' in nodes
        assert '2' in nodes

    @patch('utils.TSP.TSP_networkx.XMLParser')
    @patch('builtins.open')
    def test_build_graph_filters_duplicate_edges(self, mock_open, mock_parser):
        mock_open.return_value.__enter__.return_value.read.return_value = '<map></map>'
        
        mock_intersection1 = Mock(id='1')
        mock_intersection2 = Mock(id='2')
        
        # Two segments with different weights
        mock_segment1 = Mock(start='1', end='2', length_m=100.0, street_name='St1')
        mock_segment2 = Mock(start='1', end='2', length_m=50.0, street_name='St2')
        
        mock_map_data = Mock()
        mock_map_data.intersections = [mock_intersection1, mock_intersection2]
        mock_map_data.road_segments = [mock_segment1, mock_segment2]
        
        mock_parser.parse_map.return_value = mock_map_data
        
        tsp = TSP()
        G, nodes = tsp._build_networkx_map_graph('test.xml')
        
        # Should keep smallest weight
        assert G['1']['2']['weight'] == 50.0


class TestBuildMetricCompleteGraph:
    def test_empty_graph(self):
        tsp = TSP()
        G = tsp._build_metric_complete_graph({})
        assert len(G.nodes()) == 0

    def test_single_node(self):
        tsp = TSP()
        sp_graph = {'A': {'A': {'cost': 0.0, 'path': ['A']}}}
        G = tsp._build_metric_complete_graph(sp_graph)
        # Single node component has size 1, returns empty graph
        assert len(G.nodes()) == 0

    def test_two_mutually_reachable_nodes(self):
        tsp = TSP()
        sp_graph = {
            'A': {'A': {'cost': 0.0}, 'B': {'cost': 10.0}},
            'B': {'A': {'cost': 10.0}, 'B': {'cost': 0.0}}
        }
        G = tsp._build_metric_complete_graph(sp_graph)
        assert len(G.nodes()) == 2
        assert G.has_edge('A', 'B')
        assert G['A']['B']['weight'] == 10.0

    def test_asymmetric_costs_uses_minimum(self):
        tsp = TSP()
        sp_graph = {
            'A': {'A': {'cost': 0.0}, 'B': {'cost': 15.0}},
            'B': {'A': {'cost': 10.0}, 'B': {'cost': 0.0}}
        }
        G = tsp._build_metric_complete_graph(sp_graph)
        assert G['A']['B']['weight'] == 10.0

    def test_unreachable_nodes_excluded(self):
        tsp = TSP()
        sp_graph = {
            'A': {'A': {'cost': 0.0}, 'B': {'cost': float('inf')}},
            'B': {'A': {'cost': float('inf')}, 'B': {'cost': 0.0}}
        }
        G = tsp._build_metric_complete_graph(sp_graph)
        # No mutual reachability
        assert len(G.nodes()) == 0


class TestSolve:
    @patch.object(TSP, '_build_networkx_map_graph')
    def test_solve_returns_tour_and_cost(self, mock_build_graph):
        # Create simple graph: 3 nodes in triangle
        G = nx.DiGraph()
        G.add_edge('A', 'B', weight=10.0)
        G.add_edge('B', 'C', weight=10.0)
        G.add_edge('C', 'A', weight=10.0)
        G.add_edge('A', 'C', weight=10.0)
        G.add_edge('C', 'B', weight=10.0)
        G.add_edge('B', 'A', weight=10.0)
        
        mock_build_graph.return_value = (G, ['A', 'B', 'C'])
        
        tsp = TSP()
        tour, cost = tsp.solve(nodes=['A', 'B', 'C'])
        
        assert isinstance(tour, list)
        assert isinstance(cost, float)
        assert len(tour) >= 4  # At least 3 nodes + return to start
        assert tour[0] == tour[-1]  # Circular tour

    @patch.object(TSP, '_build_networkx_map_graph')
    def test_solve_with_must_visit(self, mock_build_graph):
        G = nx.DiGraph()
        G.add_edge('A', 'B', weight=10.0)
        G.add_edge('B', 'A', weight=10.0)
        
        mock_build_graph.return_value = (G, ['A', 'B', 'C'])
        
        tsp = TSP()
        # must_visit parameter removed; pass nodes directly
        tour, cost = tsp.solve(nodes=['A', 'B'])
        
        assert 'A' in tour
        assert 'B' in tour

    @patch.object(TSP, '_build_networkx_map_graph')
    def test_solve_filters_missing_nodes(self, mock_build_graph):
        G = nx.DiGraph()
        G.add_edge('A', 'B', weight=10.0)
        
        mock_build_graph.return_value = (G, ['A', 'B'])
        
        tsp = TSP()
        tour, cost = tsp.solve(nodes=['A', 'B', 'Z'])  # Z doesn't exist
        
        assert 'Z' not in tour


    # Multi-courier solver removed from the utility; multi-agent routing
    # responsibilities belong to the service layer which should call `solve`
    # per agent after splitting locations.


class TestExpandTourWithPaths:
    def test_empty_tour(self):
        tsp = TSP()
        route, cost = tsp.expand_tour_with_paths([], {})
        assert route == []
        assert cost == 0.0

    def test_single_node_tour(self):
        tsp = TSP()
        route, cost = tsp.expand_tour_with_paths(['A'], {})
        assert route == []
        assert cost == 0.0

    def test_valid_tour_expansion(self):
        sp_graph = {
            'A': {
                'B': {'path': ['A', 'X', 'B'], 'cost': 20.0}
            },
            'B': {
                'C': {'path': ['B', 'Y', 'C'], 'cost': 15.0}
            }
        }
        
        tsp = TSP()
        route, cost = tsp.expand_tour_with_paths(['A', 'B', 'C'], sp_graph)
        
        assert route == ['A', 'X', 'B', 'Y', 'C']
        assert cost == 35.0

    def test_missing_path_raises_error(self):
        sp_graph = {
            'A': {'B': {'path': None, 'cost': float('inf')}}
        }
        
        tsp = TSP()
        with pytest.raises(ValueError, match="No shortest-path"):
            tsp.expand_tour_with_paths(['A', 'B'], sp_graph)

    def test_overlapping_paths_deduplicated(self):
        sp_graph = {
            'A': {'B': {'path': ['A', 'M', 'B'], 'cost': 10.0}},
            'B': {'C': {'path': ['B', 'N', 'C'], 'cost': 10.0}}
        }
        
        tsp = TSP()
        route, cost = tsp.expand_tour_with_paths(['A', 'B', 'C'], sp_graph)
        
        # B should not be duplicated
        assert route.count('B') == 1