class Astar:
    def __init__(self, alpha: float = 0.5):
        """
        alpha: blend between Euclidean and Manhattan for the heuristic
               h = alpha * euclidean + (1 - alpha) * manhattan
               (0 <= alpha <= 1)

        Initialization does not automatically load data.
        Use load_data() to populate self.nodes and self.adj.
        """
        self.alpha = float(alpha)
        self.nodes: Dict[str, Tuple[float, float]] = {}
        self.adj: Dict[str, Dict[str, float]] = {}

        # optional structures used by load_data()
        self.edges = []

    def load_data(self, xml_file_path: Optional[str] = None):
        """
        Load data from an XML file using XMLParser.
        If no file is specified, use a default file.
        """
        if xml_file_path is None:
            # Use a default XML file from the project directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(current_dir, "..", "..", "..", "..")
            xml_file_path = os.path.join(project_root, "fichiersXMLPickupDelivery", "petitPlan.xml")
        
        try:
            # Read the XML file content
            with open(xml_file_path, 'r', encoding='utf-8') as file:
                xml_content = file.read()
            
            # Parse data with XMLParser
            map_data = XMLParser.parse_map(xml_content)
            
            # Build self.nodes from intersections
            self.nodes = {}
            for intersection in map_data.intersections:
                # Use (longitude, latitude) as coordinates (x, y)
                self.nodes[intersection.id] = (intersection.longitude, intersection.latitude)
            
            # Build self.adj from road segments
            self.adj = {}
            for segment in map_data.road_segments:
                # start/end may be either a string ID or an Intersection object.
                start_id = getattr(segment.start, 'id', segment.start)
                end_id = getattr(segment.end, 'id', segment.end)

                # Normalize to strings
                try:
                    start_id = str(start_id)
                    end_id = str(end_id)
                except Exception:
                    # Skip malformed segment
                    continue

                # Verify that source and destination nodes exist
                if start_id in self.nodes and end_id in self.nodes:
                    if start_id not in self.adj:
                        self.adj[start_id] = {}

                    # Use the segment length as the cost
                    cost = float(segment.length_m)

                    # If there's already an edge between these nodes, keep the shortest
                    existing_cost = self.adj[start_id].get(end_id)
                    if existing_cost is None or cost < existing_cost:
                        self.adj[start_id][end_id] = cost
            
            print(f"Data loaded: {len(self.nodes)} nodes, {sum(len(adj) for adj in self.adj.values())} edges")
            
        except FileNotFoundError:
            print(f"XML file not found: {xml_file_path}")
        except Exception as e:
            print(f"Error while loading XML file: {e}")

    def _euclid(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def _manhattan(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def heuristic(self, n1: str, n2: str) -> float:
        p1 = self.nodes[n1]
        p2 = self.nodes[n2]
        return self.alpha * self._euclid(p1, p2) + (1.0 - self.alpha) * self._manhattan(p1, p2)

    def multipleTarget_astar(self, idNode):
        """
        Find shortest paths from idNode to all other nodes.
        Optimized version with early termination and better heuristics.
        Returns a dict:
          target -> {'path': [idNode, ..., target] or None, 'cost': float('inf') if unreachable}
        """
        if idNode not in self.nodes:
            raise ValueError(f"start node {idNode!r} not in graph")

        # set of goals (all nodes except the start)
        goals = set(self.nodes.keys()) - {idNode}
        if not goals:
            return {}

        # Pre-compute goal positions for faster heuristic calculation
        goal_positions = {goal: self.nodes[goal] for goal in goals}

        # helpers
        def reconstruct_path(came_from: Dict[str, str], current: str) -> List[str]:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        def compute_min_heuristic(node_pos: Tuple[float, float], remaining_goals: set) -> float:
            """Optimized heuristic computation using pre-computed positions"""
            if not remaining_goals:
                return 0.0
            
            min_h = float('inf')
            for goal in remaining_goals:
                goal_pos = goal_positions[goal]
                h = self.alpha * self._euclid(node_pos, goal_pos) + (1.0 - self.alpha) * self._manhattan(node_pos, goal_pos)
                if h < min_h:
                    min_h = h
                    if min_h == 0:  # Can't get better than 0
                        break
            return min_h

        # Multi-target A*: admissible heuristic = min heuristic to any remaining goal
        remaining_goals = set(goals)
        g_score: Dict[str, float] = {idNode: 0.0}
        came_from: Dict[str, str] = {}
        found: Dict[str, Dict] = {}
        
        # Cache for visited states to avoid recomputation
        closed_set = set()

        heap = []
        # f, g, node
        start_pos = self.nodes[idNode]
        h0 = compute_min_heuristic(start_pos, remaining_goals)
        heapq.heappush(heap, (h0, 0.0, idNode))

        while heap and len(found) < len(goals):
            f, g, node = heapq.heappop(heap)
            
            # Skip if already processed with better cost
            if node in closed_set:
                continue
            
            # outdated entry?
            if g > g_score.get(node, float("inf")):
                continue
                
            closed_set.add(node)

            # if we are on a goal not yet found, record it
            if node in remaining_goals:
                path = reconstruct_path(came_from, node)
                found[node] = {"path": path, "cost": g}
                remaining_goals.remove(node)
                
                # Early termination: if all goals found, stop
                if len(found) == len(goals):
                    break
                
                # Update goal_positions to remove found goal for faster heuristic
                del goal_positions[node]

            # explore neighbors
            node_neighbors = self.adj.get(node, {})
            if not node_neighbors:
                continue
                
            node_pos = self.nodes[node]
            
            for nbr, edge_cost in node_neighbors.items():
                if nbr in closed_set:
                    continue
                    
                tentative_g = g + float(edge_cost)
                
                # Skip if we already found a better path to this neighbor
                if tentative_g >= g_score.get(nbr, float("inf")):
                    continue
                
                g_score[nbr] = tentative_g
                came_from[nbr] = node
                
                # Optimized heuristic calculation
                nbr_pos = self.nodes[nbr]
                h = compute_min_heuristic(nbr_pos, remaining_goals)
                
                heapq.heappush(heap, (tentative_g + h, tentative_g, nbr))

        # build result: for unreachable targets, put None / inf
        result: Dict[str, Dict] = {}
        for tgt in goals:
            if tgt in found:
                result[tgt] = found[tgt]
            else:
                result[tgt] = {"path": None, "cost": float("inf")}
        return result
        

    def compute_shortest_paths_graph(self) -> Dict[str, Dict[str, Dict]]:
        """
        Compute the shortest paths graph for every node in self.nodes using multipleTarget_astar.
        Optimized version with progress tracking and early validation.
        Returns a dict mapping source -> (dict returned by multipleTarget_astar for that source)
        """
        if not self.nodes:
            return {}
            
        result: Dict[str, Dict[str, Dict]] = {}
        total_nodes = len(self.nodes)
        
        # Pre-filter nodes that have no outgoing edges to avoid unnecessary computation
        valid_sources = [node for node in self.nodes.keys() if node in self.adj and self.adj[node]]
        isolated_nodes = [node for node in self.nodes.keys() if node not in self.adj or not self.adj[node]]
        
        print(f"Computing shortest paths for {total_nodes} nodes ({len(valid_sources)} with outgoing edges, {len(isolated_nodes)} isolated)...")
        
        # Process nodes with outgoing edges
        for i, src in enumerate(valid_sources):
            if i % 10 == 0:  # Progress indicator
                print(f"Progress: {i}/{len(valid_sources)} connected nodes processed...")
                
            result[src] = self.multipleTarget_astar(src)
        
        # For nodes without outgoing edges, create empty result (much faster)
        print(f"Adding {len(isolated_nodes)} isolated nodes...")
        for src in isolated_nodes:
            # All destinations are unreachable from isolated nodes
            unreachable_result = {}
            for tgt in self.nodes.keys():
                if tgt != src:
                    unreachable_result[tgt] = {"path": None, "cost": float("inf")}
            result[src] = unreachable_result
                
        print(f"Shortest paths computation completed for {total_nodes} nodes.")
        return result

    def print_for_test(self) -> Dict[str, Dict[str, Dict]]:
        """
        For tests only (temporary).

        Loads data from an XML file via XMLParser if needed, computes all shortest
        paths with multipleTarget_astar, prints results and returns the dictionary.
        """
        if not self.nodes:
            self.load_data()

        result = self.compute_shortest_paths_graph()

        def _sort_key(k: str):
            try:
                return int(k)
            except Exception:
                return k

        # Print only a sample to avoid excessively long output
        sorted_sources = sorted(result.keys(), key=_sort_key)
        max_display = min(5, len(sorted_sources))  # limit to 5 sources max
        
        print(f"=== A* Results (showing first {max_display} nodes out of {len(sorted_sources)}) ===")
        for i, src in enumerate(sorted_sources[:max_display]):
            print(f"\nFrom {src}:")
            tgt_map = result[src]
            sorted_targets = sorted(tgt_map.items(), key=lambda it: _sort_key(it[0]))
            max_targets = min(5, len(sorted_targets))  # limit to 5 destinations max
            
            for j, (tgt, info) in enumerate(sorted_targets[:max_targets]):
                path = info.get("path")
                cost = info.get("cost", float("inf"))
                if path is None:
                    print(f"  to {tgt}: unreachable (cost=inf)")
                else:
                    print(f"  to {tgt}: cost={cost:.2f}m, path={' -> '.join(path)}")
            
            if len(sorted_targets) > max_targets:
                print(f"  ... and {len(sorted_targets) - max_targets} other destinations")
        
        if len(sorted_sources) > max_display:
            print(f"\n... and {len(sorted_sources) - max_display} other sources")
            
        return result
