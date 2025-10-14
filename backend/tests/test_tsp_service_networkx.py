import pytest
import importlib

try:
    import networkx  # type: ignore
    HAS_NX = True
except Exception:
    HAS_NX = False


@pytest.mark.skipif(not HAS_NX, reason="networkx not installed")
def test_tsp_service_smoke():
    # Import the service and instantiate it to run the constructor flow.
    from app.services.TSPService import TSPService
    # Just ensure instantiation runs without raising
    TSPService()
