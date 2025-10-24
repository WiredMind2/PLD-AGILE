import sys
from pathlib import Path
import shutil


def pytest_configure():
    # Ensure the backend package root is on sys.path so tests can import `app`.
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def pytest_sessionfinish(session, exitstatus):
    """Clean up test artifacts after all tests have finished."""
    # Remove all test snapshot files from saved_tours directory
    repo_root = Path(__file__).resolve().parent.parent
    saved_tours_dir = repo_root / "app" / "data" / "saved_tours"
    
    if saved_tours_dir.exists():
        # Remove all .pkl files (test snapshots)
        for pkl_file in saved_tours_dir.glob("*.pkl"):
            try:
                pkl_file.unlink()
                print(f"Cleaned up test file: {pkl_file.name}")
            except Exception as e:
                print(f"Warning: Could not remove {pkl_file.name}: {e}")
