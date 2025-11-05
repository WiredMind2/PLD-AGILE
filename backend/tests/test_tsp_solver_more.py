import networkx as nx
from app.utils.TSP.TSP_solver import TSP
from app.utils.TSP.TSP_heuristics import TourHeuristics


def test_generate_initial_with_savings_and_multiple_heuristics():
    tsp = TSP()
    # Create metric graph
    G = nx.Graph()
    nodes = ['A','B','C','D','Z']
    G.add_nodes_from(nodes)
    for u in nodes:
        for v in nodes:
            if u != v:
                G.add_edge(u, v, weight=1.0)

    pd_pairs = [('A','B'), ('C','D')]
    pickups = [p for p,_ in pd_pairs]
    deliveries = [d for _,d in pd_pairs]
    delivery_map = {d: p for p, d in pd_pairs}

    tour_cost_fn = tsp._make_tour_cost_function(G)
    is_valid = tsp._make_validation_function(delivery_map)

    # Request 3 heuristics to force savings heuristic path
    route, cost = tsp._generate_initial_tour(
        G, pd_pairs, pickups, deliveries, delivery_map,
        tour_cost_fn, is_valid, 'Z', {'num_heuristics': 3}
    )
    assert isinstance(route, list)
    assert isinstance(cost, float)


def test_optimize_tour_appends_closure_when_closed():
    tsp = TSP()
    # small closed tour with 3 nodes
    tour_seq = ['A','B','C','A']
    # cost function: sum of 1 per edge
    def cost_fn(seq):
        return float(len(seq))

    # run optimize_tour with parameters that will run local search but keep core
    params = {'num_restarts':1,'iterations_per_restart':2,'use_simulated_annealing':False,'use_or_opt':False,'strategy':'fast'}
    best_core, best_cost = tsp._optimize_tour(tour_seq, cost_fn(tour_seq), cost_fn, lambda s: True, params)
    # If closed and best_core non-empty, result should be a closed tour (last == first)
    assert isinstance(best_core, list)
    if best_core:
        assert best_core[0] == best_core[-1]
