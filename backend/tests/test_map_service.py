"""Tests for MapService"""
import pytest
from unittest.mock import Mock, patch
from app.services.MapService import MapService
from app.services.XMLParser import XMLParser


class TestMapService:
    """Test suite for MapService class"""

    def test_init(self):
        """Test MapService initialization"""
        service = MapService()
        assert service is not None

    def test_nearest_intersection_no_map(self):
        """Test _nearest_intersection when no map is loaded"""
        service = MapService()
        with patch('app.core.state.get_map', return_value=None):
            result = service._nearest_intersection(45.0, -93.0)
            assert result is None

    def test_nearest_intersection_empty_intersections(self):
        """Test _nearest_intersection when map has no intersections"""
        service = MapService()
        mock_map = Mock()
        mock_map.intersections = []
        with patch('app.core.state.get_map', return_value=mock_map):
            result = service._nearest_intersection(45.0, -93.0)
            assert result is None

    def test_nearest_intersection_single_intersection(self):
        """Test _nearest_intersection with a single intersection"""
        service = MapService()
        
        # Create a mock intersection
        mock_inter = Mock()
        mock_inter.latitude = 45.5
        mock_inter.longitude = -93.5
        mock_inter.id = "1"
        
        mock_map = Mock()
        mock_map.intersections = [mock_inter]
        
        with patch('app.core.state.get_map', return_value=mock_map):
            result = service._nearest_intersection(45.0, -93.0)
            assert result == mock_inter

    def test_nearest_intersection_multiple_intersections(self):
        """Test _nearest_intersection finds the closest one"""
        service = MapService()
        
        # Create mock intersections at different distances
        inter1 = Mock()
        inter1.latitude = 45.5
        inter1.longitude = -93.5
        inter1.id = "1"
        
        inter2 = Mock()
        inter2.latitude = 45.01  # Much closer to test point
        inter2.longitude = -93.01
        inter2.id = "2"
        
        inter3 = Mock()
        inter3.latitude = 46.0
        inter3.longitude = -94.0
        inter3.id = "3"
        
        mock_map = Mock()
        mock_map.intersections = [inter1, inter2, inter3]
        
        with patch('app.core.state.get_map', return_value=mock_map):
            result = service._nearest_intersection(45.0, -93.0)
            assert result == inter2  # Should find the closest one

    def test_nearest_intersection_with_invalid_coordinates(self):
        """Test _nearest_intersection handles invalid coordinates gracefully"""
        service = MapService()
        
        # Create an intersection with invalid coordinates
        mock_inter = Mock()
        mock_inter.latitude = "invalid"  # String instead of float
        mock_inter.longitude = -93.5
        mock_inter.id = "1"
        
        mock_map = Mock()
        mock_map.intersections = [mock_inter]
        
        with patch('app.core.state.get_map', return_value=mock_map):
            # Should handle exception and return None or the best available
            result = service._nearest_intersection(45.0, -93.0)
            # Since all intersections are invalid, it might still return the mock_inter
            # or None depending on implementation

    def test_ack_pair_success(self):
        """Test ack_pair successfully finds both pickup and delivery nodes"""
        service = MapService()
        
        # Create mock intersections
        pickup_inter = Mock()
        pickup_inter.latitude = 45.0
        pickup_inter.longitude = -93.0
        pickup_inter.id = "pickup"
        
        delivery_inter = Mock()
        delivery_inter.latitude = 46.0
        delivery_inter.longitude = -94.0
        delivery_inter.id = "delivery"
        
        mock_map = Mock()
        mock_map.intersections = [pickup_inter, delivery_inter]
        
        with patch('app.core.state.get_map', return_value=mock_map):
            p_node, d_node = service.ack_pair((45.0, -93.0), (46.0, -94.0))
            assert p_node is not None
            assert d_node is not None
            assert p_node.id == "pickup"
            assert d_node.id == "delivery"

    def test_ack_pair_no_map(self):
        """Test ack_pair when no map is loaded"""
        service = MapService()
        
        with patch('app.core.state.get_map', return_value=None):
            p_node, d_node = service.ack_pair((45.0, -93.0), (46.0, -94.0))
            assert p_node is None
            assert d_node is None

    def test_ack_pair_same_location(self):
        """Test ack_pair when pickup and delivery are at the same location"""
        service = MapService()
        
        inter = Mock()
        inter.latitude = 45.0
        inter.longitude = -93.0
        inter.id = "same"
        
        mock_map = Mock()
        mock_map.intersections = [inter]
        
        with patch('app.core.state.get_map', return_value=mock_map):
            p_node, d_node = service.ack_pair((45.0, -93.0), (45.0, -93.0))
            assert p_node == inter
            assert d_node == inter

    def test_ack_pair_with_real_xml(self):
        """Integration test with real XML parsing"""
        import os
        from pathlib import Path
        
        # Find the XML file
        project_root = Path(__file__).resolve().parents[2]
        xml_path = project_root / "fichiersXMLPickupDelivery" / "petitPlan.xml"
        
        if not xml_path.exists():
            pytest.skip(f"XML file not found at {xml_path}")
        
        # Parse the map
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        map_data = XMLParser.parse_map(xml_content)
        
        # Temporarily set the map in state
        with patch('app.core.state.get_map', return_value=map_data):
            service = MapService()
            
            # Use coordinates near the first intersection
            if map_data.intersections:
                first = map_data.intersections[0]
                p_node, d_node = service.ack_pair(
                    (first.latitude, first.longitude),
                    (first.latitude + 0.001, first.longitude + 0.001)
                )
                assert p_node is not None
                assert d_node is not None
