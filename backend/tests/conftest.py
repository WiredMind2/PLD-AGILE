import sys
from pathlib import Path


def pytest_configure():
    # Ensure the backend package root is on sys.path so tests can import `app`.
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
