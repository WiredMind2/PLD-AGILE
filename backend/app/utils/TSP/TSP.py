import heapq
from .Astar import Astar


class TSP():
    def __init__(self):
        self.astar = Astar()

    def solve(self, graph):
        graph = self.astar.solve(graph)

        start = list(graph.nodes)[0]
        que = [(0, start, set())]
        while que:
            cost, node, visited = heapq.heappop(que)

            for neighbor in graph.neighbors(node):
                if neighbor not in visited:
                    new_cost = cost + graph[node][neighbor]['weight']

                    if len(visited) == len(graph.nodes) - 1 and neighbor == start:
                        # Found a complete tour
                        full_path = list(visited) + [start]
                        return full_path, new_cost

                    heapq.heappush(que, (new_cost, neighbor, visited | {neighbor}))
        
        return None, float('inf')