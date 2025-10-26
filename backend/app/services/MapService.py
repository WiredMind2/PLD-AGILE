"""MapService

This service provides small helper operations related to the map that can be
invoked by API endpoints. It mirrors the simple, self-contained style used in
TSPService to keep responsibilities clear and testable.
"""
from __future__ import annotations
from app.core import state
from typing import Tuple, Optional


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

