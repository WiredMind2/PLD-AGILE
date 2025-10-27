"""Data structures and types for TSP benchmarking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class BenchmarkResult:
    """Store results from a single TSP benchmark run."""
    map_file: str
    request_file: str
    num_deliveries: int
    num_nodes: int
    tsp_time_seconds: float
    tsp_cost: float
    tsp_expanded_nodes: int
    tsp_expanded_cost: float
    optimal_time_seconds: Optional[float] = None
    optimal_cost: Optional[float] = None
    optimal_expanded_cost: Optional[float] = None
    optimality_gap_percent: Optional[float] = None
    error: Optional[str] = None