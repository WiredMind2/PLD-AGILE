"""Tests for TSPService"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import networkx as nx
from app.services.TSPService import TSPService
from app.models.schemas import Tour, Delivery, Courrier, Intersection, RoadSegment
from types import SimpleNamespace


class TestTSPService:
    """Test suite for TSPService class"""

    def test_init(self):
        """Test TSPService initialization"""
        service = TSPService()
        assert service is not None

    def test_build_nx_graph_from_map(self):
        """Test _build_nx_graph_from_map creates correct graph"""
        service = TSPService()
        
        # Create mock map data
        inter1 = Mock()
        inter1.id = "1"
        
        inter2 = Mock()
        inter2.id = "2"
        
        seg1 = Mock()
        seg1.start = Mock(id="1")
        seg1.end = Mock(id="2")
        seg1.length_m = 100.0
        seg1.street_name = "Main St"
        
        mock_map = Mock()
        mock_map.intersections = [inter1, inter2]
        mock_map.road_segments = [seg1]
        
        G = service._build_nx_graph_from_map(mock_map)
        
        assert isinstance(G, nx.DiGraph)
        assert "1" in G.nodes()
        assert "2" in G.nodes()
        assert G.has_edge("1", "2")
        assert G["1"]["2"]["weight"] == 100.0

    def test_build_nx_graph_with_duplicate_edges(self):
        """Test that duplicate edges keep minimum weight"""
        service = TSPService()
        
        inter1 = Mock(id="1")
        inter2 = Mock(id="2")
        
        # Two segments with different weights
        seg1 = Mock(start=Mock(id="1"), end=Mock(id="2"), length_m=100.0, street_name="St1")
        seg2 = Mock(start=Mock(id="1"), end=Mock(id="2"), length_m=50.0, street_name="St2")
        
        mock_map = Mock()
        mock_map.intersections = [inter1, inter2]
        mock_map.road_segments = [seg1, seg2]
        
        G = service._build_nx_graph_from_map(mock_map)
        
        # Should keep the minimum weight
        assert G["1"]["2"]["weight"] == 50.0

    def test_build_nx_graph_with_invalid_weight(self):
        """Test handling of invalid segment weights"""
        service = TSPService()
        
        inter1 = Mock(id="1")
        inter2 = Mock(id="2")
        
        seg1 = Mock(start=Mock(id="1"), end=Mock(id="2"), length_m="invalid", street_name="St")
        
        mock_map = Mock()
        mock_map.intersections = [inter1, inter2]
        mock_map.road_segments = [seg1]
        
        G = service._build_nx_graph_from_map(mock_map)
        
        # Should have infinite weight for invalid length
        assert G["1"]["2"]["weight"] == float("inf")

    def test_build_sp_graph(self):
        """Test _build_sp_graph creates shortest path graph"""
        service = TSPService()
        
        # Create a simple graph
        G = nx.DiGraph()
        G.add_edge("A", "B", weight=10.0)
        G.add_edge("B", "C", weight=20.0)
        G.add_edge("A", "C", weight=50.0)  # Longer direct path
        
        sp_graph = service._build_sp_graph(G, ["A", "B", "C"])
        
        assert "A" in sp_graph
        assert "B" in sp_graph["A"]
        assert "C" in sp_graph["A"]
        
        # Cost from A to B should be direct edge
        assert sp_graph["A"]["B"]["cost"] == 10.0
        
        # Cost from A to C should be via B (30.0), not direct (50.0)
        assert sp_graph["A"]["C"]["cost"] == 30.0
        
        # Path from A to C should go through B
        assert sp_graph["A"]["C"]["path"] == ["A", "B", "C"]

    def test_build_sp_graph_with_unreachable_nodes(self):
        """Test _build_sp_graph handles unreachable nodes"""
        service = TSPService()
        
        # Create graph with disconnected node
        G = nx.DiGraph()
        G.add_edge("A", "B", weight=10.0)
        G.add_node("C")  # Disconnected node
        
        sp_graph = service._build_sp_graph(G, ["A", "B", "C"])
        
        # Cost to unreachable node should be inf
        assert sp_graph["A"]["C"]["cost"] == float("inf")

    def test_compute_tours_no_map(self):
        """Test compute_tours raises error when no map is loaded"""
        service = TSPService()
        
        with patch('app.core.state.get_map', return_value=None):
            with pytest.raises(RuntimeError, match="No map loaded"):
                service.compute_tours()

    def test_compute_tours_no_deliveries(self):
        """Test compute_tours with empty deliveries"""
        service = TSPService()
        
        mock_map = Mock()
        mock_map.deliveries = []
        mock_map.intersections = []
        mock_map.road_segments = []
        
        with patch('app.core.state.get_map', return_value=mock_map):
            with patch('app.core.state.clear_tours'):
                with patch('app.core.state.save_tour'):
                    tours = service.compute_tours()
                    assert tours == []

    def test_compute_tours_unassigned_deliveries(self):
        """Test compute_tours ignores deliveries without courier"""
        service = TSPService()

        delivery = self._extracted_from_test_compute_tours_tsp_solver_exception_6(
            None, "1", "2"
        )
        mock_map = self._extracted_from_test_compute_tours_tsp_solver_exception_11(
            delivery, "1", "2"
        )
        mock_map.road_segments = []

        with patch('app.core.state.get_map', return_value=mock_map):
            with patch('app.core.state.clear_tours'):
                with patch('app.core.state.save_tour'):
                    tours = service.compute_tours()
                    assert tours == []

    def test_compute_tours_with_assigned_delivery(self):
        """Test compute_tours processes assigned deliveries"""
        service = TSPService()

        # Create courier
        courier = Courrier(id="courier1", name="Test Courier")

        # Create intersections
        inter1 = Mock(id="1")
        inter2 = Mock(id="2")

        delivery = self._extracted_from_test_compute_tours_tsp_solver_exception_6(
            courier, "1", "2"
        )
        delivery.warehouse = "1"
        delivery.pickup_service_s = 60
        delivery.delivery_service_s = 60

        # Create road segment
        seg = Mock(start=Mock(id="1"), end=Mock(id="2"), length_m=100.0, street_name="Main")

        mock_map = self._extracted_from_test_compute_tours_tsp_solver_exception_11(
            delivery, inter1, inter2
        )
        mock_map.road_segments = [seg]

        with patch('app.core.state.get_map', return_value=mock_map):
            with patch('app.core.state.clear_tours') as mock_clear:
                with patch('app.core.state.save_tour') as mock_save:
                    tours = service.compute_tours()

                    # Should have called clear and save
                    mock_clear.assert_called_once()
                    assert mock_save.call_count >= 1

                    # Should return tours
                    assert len(tours) > 0
                    assert tours[0].courier == courier

    def test_compute_tours_with_missing_nodes(self):
        """Test compute_tours handles deliveries with nodes not in map"""
        service = TSPService()

        courier = Courrier(id="courier1", name="Test Courier")

        delivery = self._extracted_from_test_compute_tours_tsp_solver_exception_6(
            courier, "99", "2"
        )
        mock_map = self._extracted_from_test_compute_tours_tsp_solver_exception_11(
            delivery, "1", "2"
        )
        mock_map.road_segments = []

        with patch('app.core.state.get_map', return_value=mock_map):
            with patch('app.core.state.clear_tours'):
                with patch('app.core.state.save_tour'):
                    if tours := service.compute_tours():
                        # Tour should not include invalid delivery
                        assert len(tours[0].deliveries) == 0

    def test_compute_tours_multiple_couriers(self):
        """Test compute_tours with deliveries for multiple couriers"""
        service = TSPService()
        
        courier1 = Courrier(id="c1", name="Courier 1")
        courier2 = Courrier(id="c2", name="Courier 2")

        inter1 = "1"
        inter2 = "2"
        inter3 = "3"

        # Deliveries for different couriers
        del1 = Mock(courier=courier1, pickup_addr="1", delivery_addr="2",
                    pickup_service_s=60, delivery_service_s=60)
        del2 = Mock(courier=courier2, pickup_addr="2", delivery_addr="3",
                    pickup_service_s=60, delivery_service_s=60)

        seg1 = Mock(start="1", end="2", length_m=100.0, street_name="St1")
        seg2 = Mock(start="2", end="3", length_m=150.0, street_name="St2")

        mock_map = Mock()
        mock_map.deliveries = [del1, del2]
        mock_map.intersections = [inter1, inter2, inter3]
        mock_map.road_segments = [seg1, seg2]
        
        with patch('app.core.state.get_map', return_value=mock_map):
            with patch('app.core.state.clear_tours'):
                with patch('app.core.state.save_tour'):
                    tours = service.compute_tours()
                    
                    # Should have tours for both couriers
                    assert len(tours) == 2
                    courier_ids = {t.courier for t in tours}
                    assert "c1" in courier_ids
                    assert "c2" in courier_ids

    def test_compute_tours_with_warehouse(self):
        """Test compute_tours uses warehouse as depot node"""
        service = TSPService()

        courier = Courrier(id="courier1", name="Test Courier")

        inter1 = "warehouse"
        inter2 = "pickup"
        inter3 = "delivery"

        delivery = self._extracted_from_test_compute_tours_tsp_solver_exception_6(
            courier, "pickup", "delivery"
        )
        delivery.warehouse = "warehouse"
        delivery.pickup_service_s = 60
        delivery.delivery_service_s = 60

        # Create connections
        seg1 = Mock(start="warehouse", end="pickup", length_m=100.0, street_name="St1")
        seg2 = Mock(start="pickup", end="delivery", length_m=200.0, street_name="St2")
        seg3 = Mock(start="delivery", end="warehouse", length_m=150.0, street_name="St3")

        mock_map = Mock()
        mock_map.deliveries = [delivery]
        mock_map.intersections = [inter1, inter2, inter3]
        mock_map.road_segments = [seg1, seg2, seg3]

        with patch('app.core.state.get_map', return_value=mock_map):
            with patch('app.core.state.clear_tours'):
                with patch('app.core.state.save_tour'):
                    self._extracted_from_test_compute_tours_with_warehouse_31(service)

    # TODO Rename this here and in `test_compute_tours_with_warehouse`
    def _extracted_from_test_compute_tours_with_warehouse_31(self, service):
        tours = service.compute_tours()

        assert len(tours) == 1
        tour = tours[0]

        # Tour should have route intersections
        assert hasattr(tour, 'route_intersections')
        assert hasattr(tour, 'total_distance_m')
        assert hasattr(tour, 'total_travel_time_s')

    def test_compute_tours_tsp_solver_exception(self):
        """Test compute_tours handles TSP solver exceptions gracefully"""
        service = TSPService()

        courier = Courrier(id="courier1", name="Test Courier")

        delivery = self._extracted_from_test_compute_tours_tsp_solver_exception_6(
            courier, "1", "2"
        )
        delivery.pickup_service_s = 60
        delivery.delivery_service_s = 60

        mock_map = self._extracted_from_test_compute_tours_tsp_solver_exception_11(
            delivery, "1", "2"
        )
        mock_map.road_segments = [Mock(start="1", end="2", length_m=100.0, street_name="St")]

        with patch('app.core.state.get_map', return_value=mock_map):
            with patch('app.core.state.clear_tours'):
                with patch('app.core.state.save_tour'):
                    # Mock TSP to raise exception
                    with patch('app.utils.TSP.TSP_networkx.TSP.solve', side_effect=Exception("TSP Error")):
                        tours = service.compute_tours()

                        # Should still return tours (with fallback)
                        assert len(tours) > 0

    # TODO Rename this here and in `test_compute_tours_unassigned_deliveries`, `test_compute_tours_with_assigned_delivery`, `test_compute_tours_with_missing_nodes`, `test_compute_tours_with_warehouse` and `test_compute_tours_tsp_solver_exception`
    def _extracted_from_test_compute_tours_tsp_solver_exception_11(self, delivery, arg1, arg2):
        result = Mock()
        result.deliveries = [delivery]
        result.intersections = [arg1, arg2]
        return result

    # TODO Rename this here and in `test_compute_tours_unassigned_deliveries`, `test_compute_tours_with_assigned_delivery`, `test_compute_tours_with_missing_nodes`, `test_compute_tours_with_warehouse` and `test_compute_tours_tsp_solver_exception`
    def _extracted_from_test_compute_tours_tsp_solver_exception_6(self, arg0, arg1, arg2):
        result = Mock()
        result.courier = arg0
        result.pickup_addr = arg1
        result.delivery_addr = arg2
        return result
