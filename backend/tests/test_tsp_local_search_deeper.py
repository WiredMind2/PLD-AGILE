import random
import math
import networkx as nx
from app.utils.TSP.TSP_local_search import LocalSearchOptimizer
from app.utils.TSP.TSP_solver import TSP


def make_weighted_cost(weight_map):
    def cost(seq):
        if not seq or len(seq) < 2:
            return 0.0
        s = 0.0
        for i in range(len(seq) - 1):
            s += weight_map.get((seq[i], seq[i+1]), 100.0)
        return s
    return cost


def always_valid(seq):
    return True


def test_two_opt_improvement_strict_and_sa(monkeypatch):
    # Create a core where reversing a middle segment strictly improves cost
    core = ['N0','N1','N2','N3','N4','N5']

    # Build weight map such that edges between sequential nodes are expensive
    # but edges after reversing become cheap
    weight_map = {}
    # default high cost
    for u in core:
        for v in core:
            if u != v:
                weight_map[(u,v)] = 50.0

    # Setup current sequence edges expensive
    weight_map[('N1','N2')] = 50.0
    weight_map[('N2','N3')] = 50.0
    weight_map[('N3','N4')] = 50.0

    # Edges after reversing N2..N4 become cheap
    weight_map[('N1','N4')] = 1.0
    weight_map[('N4','N3')] = 1.0
    weight_map[('N3','N2')] = 1.0
    weight_map[('N2','N5')] = 1.0

    cost_fn = make_weighted_cost(weight_map)

    # First test with strict improvement (temperature 0 -> only accept improvements)
    new_core, new_cost, improved = LocalSearchOptimizer.two_opt_improvement(
        core[:], cost_fn, always_valid, max_neighborhood_size=5,
        closed=True, temperature=0.0, min_temperature=0.0
    )
    assert improved is True
    assert new_cost < cost_fn(core + [core[0]])

    # Now test SA acceptance branch by forcing random.random to 0.0
    monkeypatch.setattr('random.random', lambda: 0.0)
    # Create a scenario with small positive delta so SA may accept
    # tweak weight map to make current slightly better, but SA should accept worse
    weight_map[('N1','N2')] = 1.0
    weight_map[('N2','N3')] = 1.0
    weight_map[('N3','N4')] = 1.0
    # but set the reversed edges as also small delta -> small positive delta
    weight_map[('N1','N4')] = 2.0
    weight_map[('N4','N3')] = 2.0
    weight_map[('N3','N2')] = 2.0

    cost_fn2 = make_weighted_cost(weight_map)
    new_core2, new_cost2, improved2 = LocalSearchOptimizer.two_opt_improvement(
        core[:], cost_fn2, always_valid, max_neighborhood_size=5,
        closed=True, temperature=10.0, min_temperature=0.0
    )
    # SA may accept; improved2 should be a boolean and cost numeric
    assert isinstance(improved2, bool)
    assert isinstance(new_cost2, float)


def test_or_opt_and_multi_start_search_exercise_branches(monkeypatch):
    # Prepare core with 6 nodes
    core = ['A','B','C','D','E','F']
    # Simple linear costs
    weight_map = {}
    for u in core:
        for v in core:
            if u != v:
                weight_map[(u,v)] = 1.0
    cost_fn = make_weighted_cost(weight_map)

    # Or-opt should run without errors
    new_core, new_cost, improved = LocalSearchOptimizer.or_opt_improvement(
        core[:], cost_fn, always_valid, closed=False, temperature=0.0, min_temperature=0.0
    )
    assert isinstance(new_core, list)

    # Multi-start local search: use simulated annealing and or-opt to hit branches
    # Fix random seed for deterministic perturbations
    random.seed(0)
    best_core, best_cost = LocalSearchOptimizer.multi_start_local_search(
        core[:], cost_fn(core + [core[0]]), cost_fn, always_valid,
        closed=False, num_restarts=2, iterations_per_restart=5,
        use_simulated_annealing=True, use_or_opt=True, strategy='balanced'
    )
    assert isinstance(best_core, list)
    assert isinstance(best_cost, float)


def test_tsp_generate_initial_tour_uses_heuristics():
    tsp = TSP()
    # Build a small complete metric graph for nodes
    G = nx.Graph()
    nodes = ['A','B','C','D']
    G.add_nodes_from(nodes)
    for u in nodes:
        for v in nodes:
            if u != v:
                G.add_edge(u, v, weight=1.0)

    pd_pairs = [('A','B'), ('C','D')]
    pickups = [p for p,_ in pd_pairs]
    deliveries = [d for _,d in pd_pairs]
    delivery_map = {d: p for p, d in pd_pairs}

    # create cost and validation functions as TSP would
    tour_cost_fn = tsp._make_tour_cost_function(G)
    is_valid = tsp._make_validation_function(delivery_map)

    route, cost = tsp._generate_initial_tour(
        G, pd_pairs, pickups, deliveries, delivery_map,
        tour_cost_fn, is_valid, None, {'num_heuristics': 2}
    )
    assert isinstance(route, list)
    assert isinstance(cost, float)
