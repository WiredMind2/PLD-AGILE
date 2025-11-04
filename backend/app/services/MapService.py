"""MapService

This service provides small helper operations related to the map that can be
invoked by API endpoints. It mirrors the simple, self-contained style used in
TSPService to keep responsibilities clear and testable.
"""
from __future__ import annotations
from app.core import state
from typing import Tuple, Optional, List, Dict
from collections import deque, defaultdict


class MapService:
	"""Lightweight service for map-related utilities.

	Currently exposes a method to acknowledge two coordinate pairs and print
	them to the server console. Intended as a stub to be expanded later
	(e.g., converting coordinates to nearest intersections, etc.).
	"""

	def __init__(self) -> None:
		pass

	def _nearest_intersection(self, lat: float, lng: float):
		"""Return the nearest Intersection from current state to given lat/lng.

		Uses a fast equirectangular approximation to compute distances in meters.
		Returns None if map or intersections are unavailable.
		"""
		mp = state.get_map()
		if mp is None or not mp.intersections:
			return None

		best = None
		best_dist = float('inf')
		# meters per degree approximations
		for inter in mp.intersections:
			try:
				lat_avg = (lat + float(inter.latitude)) / 2.0
				dx = (lat - float(inter.latitude)) * 111_320.0
				dy = (lng - float(inter.longitude)) * 111_320.0 * __import__('math').cos(__import__('math').radians(lat_avg))
				dist = (dx*dx + dy*dy) ** 0.5
			except Exception:
				dist = float('inf')
			if dist < best_dist:
				best_dist = dist
				best = inter
		return best

	def ack_pair(self, pickup: Tuple[float, float], delivery: Tuple[float, float]):
		"""Resolve the nearest intersections for pickup and delivery coordinates.

		Returns a tuple (pickup_node, delivery_node) where each element is an
		Intersection object or None if not found.
		"""
		p_lat, p_lng = pickup
		d_lat, d_lng = delivery
		p_node = self._nearest_intersection(p_lat, p_lng)
		d_node = self._nearest_intersection(d_lat, d_lng)
		return p_node, d_node

	def compute_unreachable_nodes(self, target_node_id: str) -> List[str]:
		"""Compute nodes that cannot reach the target node using reverse BFS.

		Args:
			target_node_id: The ID of the target node

		Returns:
			List of node IDs that cannot reach the target node
		"""
		mp = state.get_map()
		if mp is None or not mp.intersections:
			return []

		# Build reverse adjacency list (destination -> [origins])
		reverse_adj: Dict[str, List[str]] = defaultdict(list)
		all_node_ids = set()

		for inter in mp.intersections:
			all_node_ids.add(str(inter.id))

		# If target node doesn't exist in the map, return all nodes
		if target_node_id not in all_node_ids:
			return list(all_node_ids)

		for seg in mp.road_segments:
			start_id = str(getattr(seg.start, 'id', seg.start))
			end_id = str(getattr(seg.end, 'id', seg.end))

			# Add edge in reverse direction
			if start_id in all_node_ids and end_id in all_node_ids:
				reverse_adj[end_id].append(start_id)

		# Reverse BFS from target node to find all nodes that can reach target
		reachable = set()
		queue = deque([target_node_id])
		reachable.add(target_node_id)

		while queue:
			current = queue.popleft()
			# Get all nodes that can reach current node (predecessors)
			for predecessor in reverse_adj.get(current, []):
				if predecessor not in reachable:
					reachable.add(predecessor)
					queue.append(predecessor)

		# Unreachable nodes are all nodes minus reachable nodes
		unreachable_nodes = list(all_node_ids - reachable)
		unreachable_nodes.sort(key=lambda x: int(x))  # Sort numerically if possible

		return unreachable_nodes

	def _reachable_from_target(self, reverse_adj: Dict[str, List[str]], target: str) -> set:
		"""Helper: return set of nodes that can reach the target (i.e., reachable from target in reverse_adj)."""
		visited = set()
		q = deque([target])
		while q:
			cur = q.popleft()
			if cur in visited:
				continue
			visited.add(cur)
			for p in reverse_adj.get(cur, []):
				if p not in visited:
					q.append(p)
		return visited

	def find_best_target_node(self, max_full_scan: int = 2000, top_k: int = 50, random_samples: int = 20) -> Optional[str]:
		"""Pick a target node automatically such that the number of nodes that can reach it is maximized.

		Strategy:
		- Build reverse adjacency and indegree counts.
		- If number of nodes <= max_full_scan, evaluate every node by BFS and pick the best.
		- Otherwise, evaluate a candidate set consisting of the top_k nodes by indegree and a handful of random nodes.
		
		Returns the chosen node id or None if no map is loaded.
		"""
		import random
		mp = state.get_map()
		if mp is None or not mp.intersections:
			return None

		all_node_ids = [str(i.id) for i in mp.intersections]
		all_node_set = set(all_node_ids)

		# Build reverse adjacency
		reverse_adj: Dict[str, List[str]] = defaultdict(list)
		for seg in mp.road_segments:
			start_id = str(getattr(seg.start, 'id', seg.start))
			end_id = str(getattr(seg.end, 'id', seg.end))
			if start_id in all_node_set and end_id in all_node_set:
				reverse_adj[end_id].append(start_id)

		# indegree in original graph equals length of reverse_adj[node]
		indeg = {nid: len(reverse_adj.get(nid, [])) for nid in all_node_ids}
		n_nodes = len(all_node_ids)

		candidates = []
		if n_nodes <= max_full_scan:
			candidates = all_node_ids
		else:
			# pick top_k by indegree
			top_by_indeg = sorted(all_node_ids, key=lambda x: indeg.get(x, 0), reverse=True)[:top_k]
			candidates = list(top_by_indeg)
			# add a few random samples from the rest
			remaining = [x for x in all_node_ids if x not in candidates]
			rand_count = min(random_samples, len(remaining))
			if rand_count > 0:
				candidates += random.sample(remaining, rand_count)

		# Evaluate candidates and pick the one with largest reachable set
		best_node = None
		best_reach = -1
		for cand in candidates:
			reachable = self._reachable_from_target(reverse_adj, cand)
			reach_size = len(reachable)
			if reach_size > best_reach:
				best_reach = reach_size
				best_node = cand

		return best_node

