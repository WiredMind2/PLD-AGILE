import networkx as nx
from app.utils.TSP.TSP_heuristics import TourHeuristics
from app.utils.TSP.TSP_local_search import LocalSearchOptimizer
from app.utils.TSP.TSP_solver import TSP


def simple_tour_cost(seq):
    # Simple additive cost: A->B:1, B->C:1, C->A:1 else 10
    cost_map = {('A','B'):1.0, ('B','C'):1.0, ('C','A'):1.0,
                ('A','C'):2.0, ('C','B'):2.0, ('B','A'):2.0}
    if not seq or len(seq) < 2:
        return 0.0
    s = 0.0
    for i in range(len(seq)-1):
        s += cost_map.get((seq[i], seq[i+1]), 10.0)
    return s


def always_valid(seq):
    # For these tests, assume sequence is valid when all nodes present
    return True


def test_build_nearest_neighbor_basic():
    G = nx.Graph()
    G.add_nodes_from(['A','B','C'])
    G.add_edge('A','B', weight=1.0)
    G.add_edge('B','C', weight=1.0)
    G.add_edge('A','C', weight=2.0)

    pickups = ['A']
    deliveries = ['B']
    delivery_map = {'B':'A'}

    tour, cost = TourHeuristics.build_nearest_neighbor_tour(
        G, pickups, deliveries, delivery_map, simple_tour_cost, always_valid
    )

    assert isinstance(tour, list)
    assert cost >= 0.0


def test_build_savings_and_insertion():
    G = nx.Graph()
    nodes = ['A','B','C','D','Z']
    G.add_nodes_from(nodes)
    # make a small metric with symmetric weights
    for u in nodes:
        for v in nodes:
            if u == v:
                continue
            G.add_edge(u, v, weight=1.0 if (u,v) in [( 'A','B'),('C','D')] else 2.0)

    pd_pairs = [('A','B'), ('C','D')]

    # Test savings heuristic with depot
    sv_route, sv_cost = TourHeuristics.build_savings_tour(
        G, pd_pairs, simple_tour_cost, always_valid, start_node='Z'
    )
    assert isinstance(sv_route, list)
    assert sv_cost >= 0.0

    # Test insertion heuristic
    ins_route, ins_cost = TourHeuristics.build_insertion_tour(
        G, pd_pairs, simple_tour_cost, always_valid, start_node=None
    )
    assert isinstance(ins_route, list)
    assert ins_cost >= 0.0


def test_two_opt_and_or_opt_improvements():
    # Use simple core sequence that allows improvements
    core = ['A','B','C']

    # two_opt: set temperature low to prefer strict improvements
    new_core, new_cost, improved = LocalSearchOptimizer.two_opt_improvement(
        core[:], simple_tour_cost, always_valid, max_neighborhood_size=2,
        closed=True, temperature=0.0, min_temperature=0.0
    )
    assert isinstance(new_core, list)
    assert isinstance(new_cost, float)
    assert isinstance(improved, bool)

    # or_opt: similarly
    new_core2, new_cost2, improved2 = LocalSearchOptimizer.or_opt_improvement(
        core[:], simple_tour_cost, always_valid, closed=True, temperature=0.0, min_temperature=0.0
    )
    assert isinstance(new_core2, list)
    assert isinstance(new_cost2, float)
    assert isinstance(improved2, bool)


def test_multi_start_local_search_results():
    # Basic smoke test for multi-start local search
    core = ['A','B','C']
    initial_cost = simple_tour_cost(core + [core[0]])
    best_core, best_cost = LocalSearchOptimizer.multi_start_local_search(
        core, initial_cost, simple_tour_cost, always_valid, closed=True,
        num_restarts=1, iterations_per_restart=5, use_simulated_annealing=False,
        use_or_opt=False, strategy='fast'
    )
    assert isinstance(best_core, list)
    assert isinstance(best_cost, float)


def test_tsp_solver_helpers():
    tsp = TSP()
    # strategy parameters
    p_small = tsp._get_strategy_parameters(4)
    assert p_small['strategy'] in ('fast','balanced','focused')

    # extract nodes
    nodes = tsp._extract_nodes_from_pairs([('A','B'), ('C','D')])
    assert 'A' in nodes and 'B' in nodes

    # compute shortest paths on a tiny directed graph
    G = nx.DiGraph()
    G.add_edge('A','B', weight=1.0)
    sp = tsp._compute_shortest_paths(G, ['A','B'])
    assert 'A' in sp and 'B' in sp
