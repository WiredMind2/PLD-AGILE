"""
Tests for UML diagram generation script
"""
import pytest
import sys
from pathlib import Path
import tempfile
import shutil

# Add tools directory to path
tools_dir = Path(__file__).parent.parent / "tools"
sys.path.insert(0, str(tools_dir))

try:
    from generate_uml_diagrams import (
        APIEndpointExtractor,
        UMLDiagramGenerator,
        SVGConverter
    )
except ImportError:
    # If running from different location, try alternative import
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "generate_uml_diagrams",
        tools_dir / "generate_uml_diagrams.py"
    )
    generate_uml_diagrams = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generate_uml_diagrams)
    APIEndpointExtractor = generate_uml_diagrams.APIEndpointExtractor
    UMLDiagramGenerator = generate_uml_diagrams.UMLDiagramGenerator
    SVGConverter = generate_uml_diagrams.SVGConverter


class TestAPIEndpointExtractor:
    """Test API endpoint extraction functionality"""
    
    def test_extract_endpoints_from_valid_file(self, tmp_path):
        """Test extracting endpoints from a valid route file"""
        # Create a temporary endpoints directory
        endpoints_dir = tmp_path / "endpoints"
        endpoints_dir.mkdir()
        
        # Create a sample route file
        route_content = '''
from fastapi import APIRouter
from app.models.schemas import Map

router = APIRouter(prefix="/map")

@router.post("/", response_model=Map, tags=["Map"], summary="Upload city map")
async def upload_map(file: UploadFile):
    """Upload a city map XML file."""
    pass

@router.get("/", response_model=Map, tags=["Map"], summary="Get loaded map")
def get_map():
    """Return the currently loaded map."""
    pass

@router.get("/ack_pair", tags=["Map"], summary="Nearest nodes for pickup and delivery")
def ack_pair(pickup_lat: float, pickup_lng: float):
    """Return nearest intersections."""
    pass
'''
        
        route_file = endpoints_dir / "map.py"
        route_file.write_text(route_content)
        
        # Extract endpoints
        extractor = APIEndpointExtractor(endpoints_dir)
        endpoints = extractor.extract_endpoints()
        
        # Assertions
        assert "map" in endpoints
        assert len(endpoints["map"]) == 3
        
        # Check first endpoint
        ep1 = endpoints["map"][0]
        assert ep1["method"] == "POST"
        assert ep1["path"] == "/map/"
        assert ep1["summary"] == "Upload city map"
        
        # Check second endpoint
        ep2 = endpoints["map"][1]
        assert ep2["method"] == "GET"
        assert ep2["path"] == "/map/"
        assert ep2["summary"] == "Get loaded map"
        
        # Check third endpoint
        ep3 = endpoints["map"][2]
        assert ep3["method"] == "GET"
        assert ep3["path"] == "/map/ack_pair"
        assert ep3["summary"] == "Nearest nodes for pickup and delivery"
    
    def test_extract_endpoints_with_parameters(self, tmp_path):
        """Test extracting endpoints with path parameters"""
        endpoints_dir = tmp_path / "endpoints"
        endpoints_dir.mkdir()
        
        route_content = '''
from fastapi import APIRouter

router = APIRouter(prefix="/couriers")

@router.get("/{courier_id}", tags=["Couriers"], summary="Get courier details")
def get_courier(courier_id: str):
    pass

@router.delete("/{courier_id}", tags=["Couriers"], summary="Delete courier")
def delete_courier(courier_id: str):
    pass
'''
        
        route_file = endpoints_dir / "couriers.py"
        route_file.write_text(route_content)
        
        extractor = APIEndpointExtractor(endpoints_dir)
        endpoints = extractor.extract_endpoints()
        
        assert "couriers" in endpoints
        assert len(endpoints["couriers"]) == 2
        assert endpoints["couriers"][0]["path"] == "/couriers/{courier_id}"
        assert endpoints["couriers"][1]["path"] == "/couriers/{courier_id}"
    
    def test_extract_endpoints_no_files(self, tmp_path):
        """Test extraction when no route files exist"""
        endpoints_dir = tmp_path / "endpoints"
        endpoints_dir.mkdir()
        
        extractor = APIEndpointExtractor(endpoints_dir)
        endpoints = extractor.extract_endpoints()
        
        assert endpoints == {}
    
    def test_extract_endpoints_directory_not_exists(self, tmp_path):
        """Test extraction when directory doesn't exist"""
        endpoints_dir = tmp_path / "nonexistent"
        
        extractor = APIEndpointExtractor(endpoints_dir)
        endpoints = extractor.extract_endpoints()
        
        assert endpoints == {}


class TestUMLDiagramGenerator:
    """Test UML diagram generation functionality"""
    
    def test_generate_enhanced_plantuml_structure(self, tmp_path):
        """Test that generated PlantUML has correct structure"""
        # Create minimal project structure
        project_root = tmp_path / "project"
        backend_dir = project_root / "backend"
        app_dir = backend_dir / "app"
        endpoints_dir = app_dir / "api" / "api_v1" / "endpoints"
        endpoints_dir.mkdir(parents=True)
        
        # Create a simple endpoint file
        route_content = '''
from fastapi import APIRouter
router = APIRouter(prefix="/test")

@router.get("/", summary="Test endpoint")
def test_endpoint():
    pass
'''
        (endpoints_dir / "test.py").write_text(route_content)
        
        # Initialize generator
        generator = UMLDiagramGenerator(project_root)
        
        # Generate enhanced diagram
        output_file = generator.generate_enhanced_package_diagram()
        
        assert output_file is not None
        assert output_file.exists()
        
        # Read generated content
        content = output_file.read_text()
        
        # Check structure
        assert "@startuml app" in content
        assert "@enduml" in content
        assert "app.api.api_v1.endpoints" in content
        assert "app.models.schemas" in content
        assert "app.services" in content
        assert "app.core" in content
        assert "app.utils.TSP" in content
        
        # Check that test endpoint is included
        assert '"test"' in content
        assert "Test endpoint" in content
    
    def test_generate_enhanced_plantuml_relationships(self, tmp_path):
        """Test that relationships are included in diagram"""
        project_root = tmp_path / "project"
        backend_dir = project_root / "backend"
        app_dir = backend_dir / "app"
        endpoints_dir = app_dir / "api" / "api_v1" / "endpoints"
        endpoints_dir.mkdir(parents=True)
        
        # Create endpoint files
        (endpoints_dir / "map.py").write_text('''
from fastapi import APIRouter
router = APIRouter(prefix="/map")
@router.get("/", summary="Get map")
def get_map():
    pass
''')
        
        generator = UMLDiagramGenerator(project_root)
        output_file = generator.generate_enhanced_package_diagram()
        
        content = output_file.read_text()
        
        # Check relationships exist
        assert "Map *-- Intersection" in content
        assert "TSPBase <|-- TSP" in content
        assert "..>" in content  # Check dependency arrows exist


class TestSVGConverter:
    """Test SVG conversion functionality"""
    
    @pytest.mark.integration
    def test_convert_to_svg_simple_diagram(self, tmp_path):
        """Test converting a simple PlantUML diagram to SVG"""
        # Create a simple PlantUML file
        puml_content = """@startuml
class TestClass {
  + attribute: str
  + method()
}
@enduml
"""
        puml_file = tmp_path / "test.puml"
        puml_file.write_text(puml_content)
        
        # Convert to SVG
        svg_file = SVGConverter.convert_to_svg(puml_file, tmp_path)
        
        # Assertions
        assert svg_file is not None
        assert svg_file.exists()
        assert svg_file.suffix == ".svg"
        
        # Check SVG content
        svg_content = svg_file.read_text()
        assert svg_content.startswith("<?xml") or svg_content.startswith("<svg")
        assert "TestClass" in svg_content
    
    def test_convert_to_svg_invalid_file(self, tmp_path):
        """Test conversion with invalid file"""
        puml_file = tmp_path / "nonexistent.puml"
        
        # Should handle gracefully
        svg_file = SVGConverter.convert_to_svg(puml_file, tmp_path)
        assert svg_file is None


class TestIntegration:
    """Integration tests for the complete workflow"""
    
    def test_full_generation_workflow(self, tmp_path):
        """Test the complete diagram generation workflow"""
        # Create minimal project structure
        project_root = tmp_path / "project"
        backend_dir = project_root / "backend"
        app_dir = backend_dir / "app"
        endpoints_dir = app_dir / "api" / "api_v1" / "endpoints"
        endpoints_dir.mkdir(parents=True)
        
        # Create sample endpoint files
        (endpoints_dir / "map.py").write_text('''
from fastapi import APIRouter
router = APIRouter(prefix="/map")
@router.get("/", summary="Get map")
def get_map():
    pass
''')
        
        (endpoints_dir / "tours.py").write_text('''
from fastapi import APIRouter
router = APIRouter(prefix="/tours")
@router.post("/compute", summary="Compute tours")
def compute_tours():
    pass
''')
        
        # Initialize generator
        generator = UMLDiagramGenerator(project_root, output_dir=backend_dir)
        
        # Generate enhanced package diagram
        package_diagram = generator.generate_enhanced_package_diagram()
        
        # Assertions
        assert package_diagram is not None
        assert package_diagram.exists()
        
        content = package_diagram.read_text()
        
        # Check both endpoints are included
        assert '"map"' in content
        assert '"tours"' in content
        assert "Get map" in content
        assert "Compute tours" in content
        
        # Check structure
        assert "package" in content
        assert "component" in content
        assert "class" in content


def pytest_addoption(parser):
    """Add custom pytest options"""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run integration tests that require network access"
    )


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring network"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
