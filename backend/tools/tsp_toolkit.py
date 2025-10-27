"""TSP Toolkit: Unified interface for TSP algorithm testing and benchmarking.

This file has been refactored. Core functionality moved to:
- tsp_core.py: Core TSP utilities
- tsp_benchmark.py: Benchmarking functionality  
- tsp_cli.py: Interactive CLI
"""

import os
import sys

# Ensure backend root is on sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from tsp_cli import main

if __name__ == "__main__":
    main()
