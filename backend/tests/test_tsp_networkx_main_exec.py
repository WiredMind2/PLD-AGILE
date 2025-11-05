import runpy
import types
import networkx as nx
from types import SimpleNamespace


def test_tsp_networkx_main_exec(monkeypatch):
    """Execute the TSP_networkx module as __main__ while monkeypatching
    TSP building and solving methods to ensure the demo code runs.
    """
    # Prepare a small graph and nodes
    G = nx.DiGraph()
    nodes = ['A', 'B', 'C', 'D']
    G.add_nodes_from(nodes)

    # Monkeypatch the TSP class methods in the module that will be imported
    import app.utils.TSP.TSP_solver as mod_solver

    def fake_build(self, xml_file_path=None):
        return G, nodes

    def fake_solve(self, tour_obj, start_node=None):
        # Return a compact sample tour and cost
        return (['A', 'B', 'C', 'A'], 3.0)

    monkeypatch.setattr(mod_solver.TSP, '_build_networkx_map_graph', fake_build, raising=True)
    monkeypatch.setattr(mod_solver.TSP, 'solve', fake_solve, raising=True)

    # Running the module as __main__ should execute the demo section without error
    runpy.run_module('app.utils.TSP.TSP_networkx', run_name='__main__')
