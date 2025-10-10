USE_LIBS = True

if USE_LIBS:
    from app.utils.TSP.TSP_networkx import TSP
else:
    from app.utils.TSP.TSP import TSP

class TSPService:
    def __init__(self) -> None:
            tsp = TSP()
            if USE_LIBS:
                # Use the new solve() (renamed Christofides) which returns a
                # compact tour. Then compute the pairwise sp_graph among the
                # compact tour nodes so we can expand the route.
                path, cost = tsp.solve()

                try:
                    G_map, all_nodes = tsp._build_networkx_map_graph()
                    sp_graph = {}
                    compact_nodes = list(dict.fromkeys(path[:-1])) if path else []
                    import networkx as nx
                    for src in compact_nodes:
                        lengths, paths = nx.single_source_dijkstra(G_map, src, weight='weight')
                        sp_graph[src] = {}
                        for tgt in compact_nodes:
                            if src == tgt:
                                sp_graph[src][tgt] = {'path': [src], 'cost': 0.0}
                            else:
                                sp_graph[src][tgt] = {'path': paths.get(tgt), 'cost': lengths.get(tgt, float('inf'))}
                except Exception:
                    sp_graph = {}
            else:
                # legacy A* implementation: compute full shortest-paths graph
                tsp.astar.load_data()
                sp_graph = tsp.astar.compute_shortest_paths_graph()
                path, cost = tsp.solve_multi_start_nn_2opt()
            print("Compact tour:", path)
            print("Compact cost:", cost)

            try:
                full_route, full_cost = tsp.expand_tour_with_paths(path, sp_graph)
                print("Expanded route:", full_route)
                print("Expanded cost:", full_cost)
                if abs(full_cost - cost) > 1e-6:
                    print("Warning: expanded cost differs from compact cost!")
                else:
                    print("Expanded cost matches compact cost.")
            except ValueError as e:
                print("Could not expand tour:", e)