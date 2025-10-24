"""Tests for state module"""
import pytest
import os
import tempfile
from unittest.mock import patch, Mock
from app.core import state
from app.models.schemas import Map, Delivery, Courrier, Tour, Intersection


class TestState:
    """Test suite for state module"""

    def setup_method(self):
        """Clear state before each test"""
        state.clear_state()

    def teardown_method(self):
        """Clean up after each test"""
        state.clear_state()

    def test_set_and_get_map(self):
        """Test setting and getting map"""
        mock_map = Map(intersections=[], road_segments=[])
        
        state.set_map(mock_map)
        retrieved = state.get_map()
        
        assert retrieved is mock_map

    def test_get_map_returns_none_initially(self):
        """Test get_map returns None when no map is set"""
        result = state.get_map()
        assert result is None

    def test_clear_map(self):
        """Test clearing map"""
        mock_map = Map(intersections=[], road_segments=[])
        state.set_map(mock_map)
        
        state.clear_map()
        
        assert state.get_map() is None

    def test_list_deliveries_no_map(self):
        """Test list_deliveries returns empty list when no map"""
        deliveries = state.list_deliveries()
        assert deliveries == []

    def test_list_deliveries_with_map(self):
        """Test list_deliveries returns deliveries from map"""
        delivery1 = Mock(id="d1")
        delivery2 = Mock(id="d2")
        
        mock_map = Map(intersections=[], road_segments=[])
        mock_map.deliveries = [delivery1, delivery2]
        
        state.set_map(mock_map)
        deliveries = state.list_deliveries()
        
        assert len(deliveries) == 2
        assert delivery1 in deliveries
        assert delivery2 in deliveries

    def test_add_delivery_no_map(self):
        """Test add_delivery raises error when no map"""
        delivery = Mock()
        
        with pytest.raises(RuntimeError, match="No map loaded"):
            state.add_delivery(delivery)

    def test_add_delivery_with_map(self):
        """Test add_delivery adds delivery to map"""
        mock_map = Map(intersections=[], road_segments=[])
        state.set_map(mock_map)
        
        delivery = Mock(id="d1")
        state.add_delivery(delivery)
        
        assert delivery in mock_map.deliveries

    def test_remove_delivery_no_map(self):
        """Test remove_delivery returns False when no map"""
        result = state.remove_delivery("d1")
        assert result is False

    def test_remove_delivery_not_found(self):
        """Test remove_delivery returns False when delivery not found"""
        mock_map = Map(intersections=[], road_segments=[])
        state.set_map(mock_map)
        
        result = state.remove_delivery("nonexistent")
        assert result is False

    def test_remove_delivery_success(self):
        """Test remove_delivery successfully removes delivery"""
        delivery = Mock(id="d1")
        
        mock_map = Map(intersections=[], road_segments=[])
        mock_map.deliveries = [delivery]
        state.set_map(mock_map)
        
        result = state.remove_delivery("d1")
        
        assert result is True
        assert delivery not in mock_map.deliveries

    def test_update_delivery_no_map(self):
        """Test update_delivery returns False when no map"""
        result = state.update_delivery("d1", status="completed")
        assert result is False

    def test_update_delivery_not_found(self):
        """Test update_delivery returns False when delivery not found"""
        mock_map = Map(intersections=[], road_segments=[])
        state.set_map(mock_map)
        
        result = state.update_delivery("nonexistent", status="completed")
        assert result is False

    def test_update_delivery_success(self):
        """Test update_delivery successfully updates delivery"""
        delivery = Mock(id="d1", status="pending")
        
        mock_map = Map(intersections=[], road_segments=[])
        mock_map.deliveries = [delivery]
        state.set_map(mock_map)
        
        result = state.update_delivery("d1", status="completed")
        
        assert result is True
        assert delivery.status == "completed"

    def test_update_delivery_invalid_attribute(self):
        """Test update_delivery handles invalid attributes gracefully"""
        delivery = Mock(id="d1")
        # Make setattr raise an exception for 'bad_attr'
        type(delivery).bad_attr = property(lambda self: None, lambda self, v: (_ for _ in ()).throw(Exception("Cannot set")))
        
        mock_map = Map(intersections=[], road_segments=[])
        mock_map.deliveries = [delivery]
        state.set_map(mock_map)
        
        # Should not raise, should return True but skip bad attribute
        result = state.update_delivery("d1", bad_attr="value")
        assert result is True

    def test_list_couriers_no_map(self):
        """Test list_couriers returns empty list when no map"""
        couriers = state.list_couriers()
        assert couriers == []

    def test_list_couriers_with_map(self):
        """Test list_couriers returns couriers from map"""
        courier1 = Courrier(id="c1", name="Courier 1")
        courier2 = Courrier(id="c2", name="Courier 2")
        
        mock_map = Map(intersections=[], road_segments=[])
        mock_map.couriers = [courier1, courier2]
        
        state.set_map(mock_map)
        couriers = state.list_couriers()
        
        assert len(couriers) == 2
        assert courier1 in couriers
        assert courier2 in couriers

    def test_add_courier_no_map(self):
        """Test add_courier raises error when no map"""
        courier = Courrier(id="c1", name="Test")
        
        with pytest.raises(RuntimeError, match="No map loaded"):
            state.add_courier(courier)

    def test_add_courier_with_map(self):
        """Test add_courier adds courier to map"""
        mock_map = Map(intersections=[], road_segments=[])
        state.set_map(mock_map)
        
        courier = Courrier(id="c1", name="Test")
        state.add_courier(courier)
        
        assert courier in mock_map.couriers

    def test_remove_courier_no_map(self):
        """Test remove_courier returns False when no map"""
        result = state.remove_courier("c1")
        assert result is False

    def test_remove_courier_not_found(self):
        """Test remove_courier returns False when courier not found"""
        mock_map = Map(intersections=[], road_segments=[])
        state.set_map(mock_map)
        
        result = state.remove_courier("nonexistent")
        assert result is False

    def test_remove_courier_success(self):
        """Test remove_courier successfully removes courier"""
        courier = Courrier(id="c1", name="Test")
        
        mock_map = Map(intersections=[], road_segments=[])
        mock_map.couriers = [courier]
        state.set_map(mock_map)
        
        result = state.remove_courier("c1")
        
        assert result is True
        assert courier not in mock_map.couriers

    def test_save_and_list_tours(self):
        """Test saving and listing tours"""
        tour1 = Tour(courier=Courrier(id="c1", name="C1"))
        tour2 = Tour(courier=Courrier(id="c2", name="C2"))
        
        state.save_tour(tour1)
        state.save_tour(tour2)
        
        tours = state.list_tours()
        
        assert len(tours) == 2
        assert tour1 in tours
        assert tour2 in tours

    def test_clear_tours(self):
        """Test clearing tours"""
        tour = Tour(courier=Courrier(id="c1", name="C1"))
        state.save_tour(tour)
        
        state.clear_tours()
        
        tours = state.list_tours()
        assert tours == []

    def test_clear_state(self):
        """Test clear_state clears both map and tours"""
        mock_map = Map(intersections=[], road_segments=[])
        tour = Tour(courier=Courrier(id="c1", name="C1"))
        
        state.set_map(mock_map)
        state.save_tour(tour)
        
        state.clear_state()
        
        assert state.get_map() is None
        assert state.list_tours() == []

    def test_thread_safety(self):
        """Test that state operations are thread-safe"""
        import threading
        
        mock_map = Map(intersections=[], road_segments=[])
        state.set_map(mock_map)
        
        def add_tours():
            for i in range(10):
                tour = Tour(courier=Courrier(id=f"c{i}", name=f"C{i}"))
                state.save_tour(tour)
        
        # Create multiple threads
        threads = [threading.Thread(target=add_tours) for _ in range(5)]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Should have 50 tours (5 threads × 10 tours)
        tours = state.list_tours()
        assert len(tours) == 50
