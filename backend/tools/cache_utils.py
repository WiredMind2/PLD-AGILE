"""Caching utilities for optimal tour computations."""

import json
import os
import hashlib
from pathlib import Path
from typing import Optional, Dict


def compute_file_hash(filepath: str) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()[:16]


def get_cache_key(map_path: str, req_path: str) -> str:
    """Generate cache key from map and request file paths."""
    map_hash = compute_file_hash(map_path)
    req_hash = compute_file_hash(req_path)
    map_name = Path(map_path).stem
    req_name = Path(req_path).stem
    return f"{map_name}_{req_name}_{map_hash}_{req_hash}"


def load_cached_optimal_tour(map_path: str, req_path: str) -> Optional[Dict]:
    """Load cached optimal tour if it exists."""
    if not map_path or not req_path:
        return None

    try:
        cache_key = get_cache_key(os.path.abspath(map_path), os.path.abspath(req_path))
        cache_path = Path(__file__).parent / "data" / "optimal_tours" / f"{cache_key}_optimal.json"

        if not cache_path.exists():
            return None

        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load cached optimal tour: {e}")
        return None


def save_cached_optimal_tour(
    map_path: str,
    req_path: str,
    tour: list,
    cost: float,
    num_permutations: int,
    computation_time: float,
) -> None:
    """Save optimal tour to cache."""
    if not map_path or not req_path:
        return

    try:
        cache_key = get_cache_key(os.path.abspath(map_path), os.path.abspath(req_path))
        cache_dir = Path(__file__).parent / "data" / "optimal_tours"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"{cache_key}_optimal.json"

        import datetime

        cache_data = {
            "tour": tour,
            "cost": cost,
            "num_nodes": len(tour),
            "num_permutations_checked": num_permutations,
            "computation_time_s": computation_time,
            "computed_at": datetime.datetime.now().isoformat(),
            "map_file": os.path.basename(map_path),
            "req_file": os.path.basename(req_path),
            "solver": "brute_force",
        }

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)

        print(f"  ✓ Cached optimal tour to: {cache_path.relative_to(Path(__file__).parent.parent)}")
    except Exception as e:
        print(f"  Warning: Failed to save cached optimal tour: {e}")