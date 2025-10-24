"""
Local search optimization operators for TSP solver.

This module provides local search improvement methods including:
- 2-opt
- Or-Opt
- Simulated Annealing
"""

import random
import math
from typing import List, Callable


class LocalSearchOptimizer:
    """Local search optimization methods for improving TSP tours."""

    @staticmethod
    def two_opt_improvement(
        core: List[str],
        tour_cost_fn: Callable[[List[str]], float],
        is_valid_tour_fn: Callable[[List[str]], bool],
        max_neighborhood_size: int,
        closed: bool,
        temperature: float,
        min_temperature: float
    ) -> tuple[List[str], float, bool]:
        """Apply 2-opt local search operator.
        
        Args:
            core: Current tour (without closing edge if closed)
            tour_cost_fn: Function to compute tour cost
            is_valid_tour_fn: Function to validate precedence constraints
            max_neighborhood_size: Maximum j-i distance to consider
            closed: Whether the tour should be closed
            temperature: Current simulated annealing temperature
            min_temperature: Minimum temperature threshold
            
        Returns:
            Tuple of (new_core, new_cost, improved)
        """
        n = len(core)
        total = tour_cost_fn(core + ([core[0]] if closed else []))
        improved = False
        
        for i in range(1, min(n - 2, n)):
            # Limit neighborhood size based on parameter
            max_j = min(n, i + max_neighborhood_size) if max_neighborhood_size > 0 else n
            
            for j in range(i + 2, max_j):
                # Reverse segment [i:j]
                new_core = core[:i] + list(reversed(core[i:j])) + core[j:]
                
                if not is_valid_tour_fn(new_core):
                    continue
                
                new_seq = new_core + ([new_core[0]] if closed else [])
                new_cost = tour_cost_fn(new_seq)
                delta = new_cost - total
                
                # Accept if better OR with SA probability
                accept = delta < -1e-9
                if not accept and temperature > min_temperature:
                    accept = random.random() < math.exp(-delta / temperature)
                
                if accept:
                    core = new_core
                    total = new_cost
                    improved = True
                    
                    if delta < -1e-9:  # Real improvement
                        break
            
            if improved and temperature <= min_temperature:
                break
        
        return core, total, improved

    @staticmethod
    def or_opt_improvement(
        core: List[str],
        tour_cost_fn: Callable[[List[str]], float],
        is_valid_tour_fn: Callable[[List[str]], bool],
        closed: bool,
        temperature: float,
        min_temperature: float
    ) -> tuple[List[str], float, bool]:
        """Apply Or-Opt local search operator.
        
        Or-Opt removes a segment of 1 or 2 consecutive nodes and reinserts
        it at a different position in the tour.
        
        Args:
            core: Current tour (without closing edge if closed)
            tour_cost_fn: Function to compute tour cost
            is_valid_tour_fn: Function to validate precedence constraints
            closed: Whether the tour should be closed
            temperature: Current simulated annealing temperature
            min_temperature: Minimum temperature threshold
            
        Returns:
            Tuple of (new_core, new_cost, improved)
        """
        n = len(core)
        total = tour_cost_fn(core + ([core[0]] if closed else []))
        improved = False
        
        for length in [1, 2]:
            if length >= n - 1:
                continue
                
            for i in range(1, n - length):
                segment = core[i:i+length]
                # Try only nearby positions for efficiency
                positions = list(range(max(1, i - 4), min(n - length + 1, i + 5)))
                
                for j in positions:
                    if j == i or (j > i and j < i + length):
                        continue
                    
                    # Remove segment and insert at position j
                    new_core = core[:i] + core[i+length:]
                    insert_pos = j if j < i else j - length
                    new_core = new_core[:insert_pos] + segment + new_core[insert_pos:]
                    
                    if not is_valid_tour_fn(new_core):
                        continue
                    
                    new_seq = new_core + ([new_core[0]] if closed else [])
                    new_cost = tour_cost_fn(new_seq)
                    delta = new_cost - total
                    
                    accept = delta < -1e-9
                    if not accept and temperature > min_temperature:
                        accept = random.random() < math.exp(-delta / temperature)
                    
                    if accept:
                        core = new_core
                        total = new_cost
                        improved = True
                        
                        if delta < -1e-9:
                            break
                
                if improved and temperature <= min_temperature:
                    break
            
            if improved and temperature <= min_temperature:
                break
        
        return core, total, improved

    @staticmethod
    def multi_start_local_search(
        initial_core: List[str],
        initial_cost: float,
        tour_cost_fn: Callable[[List[str]], float],
        is_valid_tour_fn: Callable[[List[str]], bool],
        closed: bool,
        num_restarts: int,
        iterations_per_restart: int,
        use_simulated_annealing: bool,
        use_or_opt: bool,
        strategy: str
    ) -> tuple[List[str], float]:
        """Multi-start local search with adaptive operators.
        
        Args:
            initial_core: Initial tour sequence
            initial_cost: Cost of initial tour
            tour_cost_fn: Function to compute tour cost
            is_valid_tour_fn: Function to validate precedence constraints
            closed: Whether tour should be closed
            num_restarts: Number of restart iterations
            iterations_per_restart: Maximum iterations per restart
            use_simulated_annealing: Whether to use simulated annealing
            use_or_opt: Whether to use Or-Opt operator
            strategy: Strategy name ("fast", "balanced", or "focused")
            
        Returns:
            Tuple of (best_core, best_cost)
        """
        best_core = list(initial_core)
        best_cost = initial_cost
        core = list(initial_core)
        total = initial_cost
        
        for restart in range(num_restarts):
            if restart > 0 and len(best_core) >= 3:
                # Perturb by doing random swaps that maintain precedence
                perturbed = list(best_core)
                num_swaps = min(3, len(perturbed) // 3)
                for _ in range(num_swaps):
                    if len(perturbed) < 3:
                        break
                    i = random.randint(1, len(perturbed) - 2)
                    j = random.randint(1, len(perturbed) - 2)
                    if i != j:
                        perturbed[i], perturbed[j] = perturbed[j], perturbed[i]
                        if not is_valid_tour_fn(perturbed):
                            perturbed[i], perturbed[j] = perturbed[j], perturbed[i]
                core = perturbed
                total = tour_cost_fn(core + ([core[0]] if closed else []))
            
            # Simulated annealing parameters (only for medium problems)
            if use_simulated_annealing:
                temperature = total * 0.05
                cooling_rate = 0.99
                min_temperature = 0.01
            else:
                temperature = 0.0
                cooling_rate = 1.0
                min_temperature = 0.0
            
            improved = True
            iters = 0
            
            while (improved or temperature > min_temperature) and iters < iterations_per_restart:
                improved = False
                iters += 1
                
                # Operator 1: 2-opt (always enabled)
                max_neighborhood = 15 if strategy == "focused" else 0
                core, total, two_opt_improved = LocalSearchOptimizer.two_opt_improvement(
                    core, tour_cost_fn, is_valid_tour_fn, max_neighborhood,
                    closed, temperature, min_temperature
                )
                improved = improved or two_opt_improved
                
                if iters >= iterations_per_restart:
                    break
                
                # Operator 2: Or-Opt (only for medium problems with balance strategy)
                if use_or_opt and (not improved or temperature > min_temperature):
                    core, total, or_opt_improved = LocalSearchOptimizer.or_opt_improvement(
                        core, tour_cost_fn, is_valid_tour_fn,
                        closed, temperature, min_temperature
                    )
                    improved = improved or or_opt_improved
                
                # Cool down temperature
                if use_simulated_annealing:
                    temperature *= cooling_rate
            
            # Update best if improved
            if total < best_cost - 1e-9:
                best_cost = total
                best_core = list(core)
        
        return best_core, best_cost
