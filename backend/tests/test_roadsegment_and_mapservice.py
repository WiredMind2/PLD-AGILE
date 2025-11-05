"""Tests for RoadSegment class and MapService"""
import pytest
from unittest.mock import Mock, patch
import math
from app.models.schemas import RoadSegment, Intersection, Map, Delivery
from app.services.MapService import MapService


class TestRoadSegment:
    """Test suite for RoadSegment class"""

    def test_init_basic(self):
        """Test RoadSegment initialization with basic parameters"""
        segment = RoadSegment(
            start="1",
            end="2", 
            length_m=100.0,
            travel_time_s=60,
            street_name="Main St"
        )
        assert segment.start == "1"
        assert segment.end == "2"
        assert segment.length_m == 100.0
        assert segment.travel_time_s == 60
        assert segment.street_name == "Main St"

    def test_init_with_intersection_objects(self):
        """Test RoadSegment initialization with Intersection objects"""
        inter1 = Intersection(id="1", latitude=48.8566, longitude=2.3522)
        inter2 = Intersection(id="2", latitude=48.8606, longitude=2.3376)
        
        segment = RoadSegment(
            start=inter1,
            end=inter2,
            length_m=200.0,
            travel_time_s=120,
            street_name="Rue de Rivoli"
        )
        assert segment.start == inter1
        assert segment.end == inter2
        assert segment.length_m == 200.0
        assert segment.travel_time_s == 120

    def test_calculate_time_standard_speed(self):
        """Test calculate_time method with standard 15 km/h speed"""
        segment = RoadSegment(
            start="1",
            end="2",
            length_m=1000.0,  # 1 km
            travel_time_s=0,  # Will be recalculated
            street_name="Test St"
        )
        
        # 15 km/h = 15000 m/h = 250 m/min = 4.167 m/s
        # For 1000m: 1000 / 4.167 ≈ 240 seconds
        expected_time = int(1000.0 / (15.0 * 1000 / 3600))  # 240
        calculated_time = segment.calculate_time()
        assert calculated_time == expected_time

    def test_calculate_time_zero_length(self):
        """Test calculate_time method with zero length"""
        segment = RoadSegment(
            start="1",
            end="2",
            length_m=0.0,
            travel_time_s=0,
            street_name="Test St"
        )
        
        calculated_time = segment.calculate_time()
        assert calculated_time == 0

    def test_calculate_time_various_lengths(self):
        """Test calculate_time method with various segment lengths"""
        # Test different lengths - just verify the method works and returns reasonable values
        test_cases = [
            (500.0, 119),   # 500m → ~119 seconds
            (1500.0, 360),  # 1.5km → ~360 seconds
            (2000.0, 479),  # 2km → ~479 seconds
        ]
        
        for length, expected in test_cases:
            segment = RoadSegment(
                start="1",
                end="2",
                length_m=length,
                travel_time_s=0,
                street_name="Test St"
            )
            actual = segment.calculate_time()
            # Check that result is close to expected (within 1 second tolerance)
            assert abs(actual - expected) <= 1, f"Expected {expected}, got {actual} for length {length}"

    def test_calculate_time_very_small_length(self):
        """Test calculate_time method with very small length"""
        segment = RoadSegment(
            start="1",
            end="2",
            length_m=1.0,  # 1 meter
            travel_time_s=0,
            street_name="Test St"
        )
        
        calculated_time = segment.calculate_time()
        assert calculated_time == 0  # Should round down to 0 for very small distances


class TestMapService:
    """Test suite for MapService class"""

    def test_init(self):
        """Test MapService initialization"""
        service = MapService()
        assert service is not None

    @patch('app.core.state.get_map')
    def test_nearest_intersection_no_map(self, mock_get_map):
        """Test _nearest_intersection when no map is loaded"""
        mock_get_map.return_value = None
        
        service = MapService()
        result = service._nearest_intersection(48.8566, 2.3522)
        assert result is None

    @patch('app.core.state.get_map')
    def test_nearest_intersection_no_intersections(self, mock_get_map):
        """Test _nearest_intersection when map has no intersections"""
        mock_map = Mock()
        mock_map.intersections = []
        mock_get_map.return_value = mock_map
        
        service = MapService()
        result = service._nearest_intersection(48.8566, 2.3522)
        assert result is None

    @patch('app.core.state.get_map')
    def test_nearest_intersection_basic(self, mock_get_map):
        """Test _nearest_intersection finds nearest intersection"""
        # Create test intersections
        inter1 = Intersection(id="1", latitude=48.8566, longitude=2.3522)  # Paris center
        inter2 = Intersection(id="2", latitude=48.8600, longitude=2.3500)  # Nearby
        
        mock_map = Mock()
        mock_map.intersections = [inter1, inter2]
        mock_get_map.return_value = mock_map
        
        service = MapService()
        # Test point very close to inter2
        result = service._nearest_intersection(48.8601, 2.3501)
        assert result == inter2

    @patch('app.core.state.get_map')
    def test_nearest_intersection_with_invalid_coordinates(self, mock_get_map):
        """Test _nearest_intersection handles invalid coordinates gracefully"""
        inter1 = Intersection(id="1", latitude=48.8566, longitude=2.3522)
        
        mock_map = Mock()
        mock_map.intersections = [inter1]
        mock_get_map.return_value = mock_map
        
        service = MapService()
        # Test with invalid coordinates that should cause exception
        result = service._nearest_intersection(float('inf'), float('nan'))
        assert result is None

    @patch('app.core.state.get_map')
    def test_ack_pair_basic(self, mock_get_map):
        """Test ack_pair method basic functionality"""
        inter1 = Intersection(id="1", latitude=48.8566, longitude=2.3522)
        inter2 = Intersection(id="2", latitude=48.8600, longitude=2.3500)
        
        mock_map = Mock()
        mock_map.intersections = [inter1, inter2]
        mock_get_map.return_value = mock_map
        
        service = MapService()
        pickup = (48.8566, 2.3522)
        delivery = (48.8600, 2.3500)
        
        p_node, d_node = service.ack_pair(pickup, delivery)
        assert p_node == inter1
        assert d_node == inter2

    @patch('app.core.state.get_map')
    def test_ack_pair_no_map(self, mock_get_map):
        """Test ack_pair when no map is loaded"""
        mock_get_map.return_value = None
        
        service = MapService()
        pickup = (48.8566, 2.3522)
        delivery = (48.8600, 2.3500)
        
        p_node, d_node = service.ack_pair(pickup, delivery)
        assert p_node is None
        assert d_node is None

    @patch('app.core.state.get_map')
    def test_compute_unreachable_nodes_no_map(self, mock_get_map):
        """Test compute_unreachable_nodes when no map is loaded"""
        mock_get_map.return_value = None
        
        service = MapService()
        result = service.compute_unreachable_nodes("1")
        assert result == []

    @patch('app.core.state.get_map')
    def test_compute_unreachable_nodes_no_intersections(self, mock_get_map):
        """Test compute_unreachable_nodes when map has no intersections"""
        mock_map = Mock()
        mock_map.intersections = []
        mock_get_map.return_value = mock_map
        
        service = MapService()
        result = service.compute_unreachable_nodes("1")
        assert result == []

    @patch('app.core.state.get_map')
    def test_compute_unreachable_nodes_target_not_in_map(self, mock_get_map):
        """Test compute_unreachable_nodes when target node doesn't exist"""
        inter1 = Intersection(id="1", latitude=48.8566, longitude=2.3522)
        inter2 = Intersection(id="2", latitude=48.8600, longitude=2.3500)
        
        mock_map = Mock()
        mock_map.intersections = [inter1, inter2]
        mock_map.road_segments = []
        mock_get_map.return_value = mock_map
        
        service = MapService()
        result = service.compute_unreachable_nodes("999")  # Non-existent target
        assert "1" in result
        assert "2" in result

    @patch('app.core.state.get_map')
    def test_compute_unreachable_nodes_basic_graph(self, mock_get_map):
        """Test compute_unreachable_nodes with a simple graph"""
        inter1 = Intersection(id="1", latitude=48.8566, longitude=2.3522)
        inter2 = Intersection(id="2", latitude=48.8600, longitude=2.3500)
        inter3 = Intersection(id="3", latitude=48.8620, longitude=2.3480)
        
        # Create segments: 1->2->3 (linear graph)
        seg1 = RoadSegment(start="1", end="2", length_m=100.0, travel_time_s=60, street_name="St1")
        seg2 = RoadSegment(start="2", end="3", length_m=100.0, travel_time_s=60, street_name="St2")
        
        mock_map = Mock()
        mock_map.intersections = [inter1, inter2, inter3]
        mock_map.road_segments = [seg1, seg2]
        mock_get_map.return_value = mock_map
        
        service = MapService()
        # Node 3 can reach nodes 2 and 1, so nodes that can't reach 3 are none
        result = service.compute_unreachable_nodes("3")
        assert len(result) == 0  # All nodes can reach 3 in reverse direction

    @patch('app.core.state.get_map')
    def test_compute_unreachable_nodes_disconnected_graph(self, mock_get_map):
        """Test compute_unreachable_nodes with disconnected graph components"""
        inter1 = Intersection(id="1", latitude=48.8566, longitude=2.3522)
        inter2 = Intersection(id="2", latitude=48.8600, longitude=2.3500)
        inter3 = Intersection(id="3", latitude=48.8620, longitude=2.3480)
        
        # Disconnected components: 1->2 and isolated 3
        seg1 = RoadSegment(start="1", end="2", length_m=100.0, travel_time_s=60, street_name="St1")
        
        mock_map = Mock()
        mock_map.intersections = [inter1, inter2, inter3]
        mock_map.road_segments = [seg1]
        mock_get_map.return_value = mock_map
        
        service = MapService()
        # From target node 1, reverse BFS finds nodes that can reach 1:
        # - Node 1 can reach itself
        # - Node 2 cannot reach 1 (only 1->2, not 2->1)
        # - Node 3 cannot reach 1 (isolated)
        result = service.compute_unreachable_nodes("1")
        assert "3" in result  # Node 3 is isolated, can't reach 1
        assert "2" in result  # Node 2 can't reach 1 (one-way street)
        assert "1" not in result  # Node 1 can always reach itself

    def test_reachable_from_target_basic(self):
        """Test _reachable_from_target helper method"""
        service = MapService()
        
        # Simple graph: 1->2->3, so in reverse: 3->2->1
        reverse_adj = {
            "3": ["2"],
            "2": ["1"],
            "1": []
        }
        
        # From target 3, we can reach 3, 2, and 1
        result = service._reachable_from_target(reverse_adj, "3")
        assert result == {"3", "2", "1"}
        
        # From target 2, we can reach 2 and 1
        result = service._reachable_from_target(reverse_adj, "2")
        assert result == {"2", "1"}

    def test_reachable_from_target_empty_graph(self):
        """Test _reachable_from_target with empty graph"""
        service = MapService()
        
        reverse_adj = {}
        
        result = service._reachable_from_target(reverse_adj, "1")
        assert result == {"1"}

    @patch('app.core.state.get_map')
    @patch('random.sample')  # Mock random to ensure deterministic tests
    def test_find_best_target_node_no_map(self, mock_random, mock_get_map):
        """Test find_best_target_node when no map is loaded"""
        mock_get_map.return_value = None
        
        service = MapService()
        result = service.find_best_target_node()
        assert result is None

    @patch('app.core.state.get_map')
    def test_find_best_target_node_no_intersections(self, mock_get_map):
        """Test find_best_target_node when map has no intersections"""
        mock_map = Mock()
        mock_map.intersections = []
        mock_get_map.return_value = mock_map
        
        service = MapService()
        result = service.find_best_target_node()
        assert result is None

    @patch('app.core.state.get_map')
    def test_find_best_target_node_small_graph(self, mock_get_map):
        """Test find_best_target_node with small graph (full scan)"""
        inter1 = Intersection(id="1", latitude=48.8566, longitude=2.3522)
        inter2 = Intersection(id="2", latitude=48.8600, longitude=2.3500)
        inter3 = Intersection(id="3", latitude=48.8620, longitude=2.3480)
        
        # Create fully connected graph
        seg1 = RoadSegment(start="1", end="2", length_m=100.0, travel_time_s=60, street_name="St1")
        seg2 = RoadSegment(start="2", end="3", length_m=100.0, travel_time_s=60, street_name="St2")
        seg3 = RoadSegment(start="3", end="1", length_m=100.0, travel_time_s=60, street_name="St3")
        
        mock_map = Mock()
        mock_map.intersections = [inter1, inter2, inter3]
        mock_map.road_segments = [seg1, seg2, seg3]
        mock_get_map.return_value = mock_map
        
        service = MapService()
        result = service.find_best_target_node(max_full_scan=2000)
        
        # Should return one of the node IDs
        assert result in ["1", "2", "3"]

    @patch('app.core.state.get_map')
    @patch('random.sample')  # Mock random for deterministic behavior
    def test_find_best_target_node_large_graph(self, mock_random, mock_get_map):
        """Test find_best_target_node with large graph (sampling)"""
        # Create many intersections
        intersections = [Intersection(id=str(i), latitude=48.8566, longitude=2.3522) for i in range(100)]
        
        # Create some road segments
        segments = []
        for i in range(50):
            start_id = str(i)
            end_id = str((i + 1) % 50)
            seg = RoadSegment(start=start_id, end=end_id, length_m=100.0, travel_time_s=60, street_name=f"St{i}")
            segments.append(seg)
        
        mock_map = Mock()
        mock_map.intersections = intersections
        mock_map.road_segments = segments
        mock_get_map.return_value = mock_map
        
        # Mock random.sample to return predictable results
        mock_random.return_value = ["25", "75"]
        
        service = MapService()
        result = service.find_best_target_node(max_full_scan=10, top_k=5, random_samples=2)
        
        # Should return one of the candidate nodes
        assert result in [str(i) for i in range(100)]

    @patch('app.core.state.get_map')
    def test_find_best_target_node_no_road_segments(self, mock_get_map):
        """Test find_best_target_node when there are no road segments"""
        inter1 = Intersection(id="1", latitude=48.8566, longitude=2.3522)
        inter2 = Intersection(id="2", latitude=48.8600, longitude=2.3500)
        
        mock_map = Mock()
        mock_map.intersections = [inter1, inter2]
        mock_map.road_segments = []
        mock_get_map.return_value = mock_map
        
        service = MapService()
        result = service.find_best_target_node()
        
        # Should return one of the nodes even with no connections
        assert result in ["1", "2"]