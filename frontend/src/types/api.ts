export interface Intersection {
  id: string;
  latitude: number;
  longitude: number;
}

export interface DeliveryRequest {
  pickup_addr: string;
  delivery_addr: string;
  pickup_service_s: number;
  delivery_service_s: number;
}

export interface Courier {
  id: string;
  current_location: Intersection;
  name: string;
}

export interface RoadSegment {
  start: Intersection;
  end: Intersection;
  length_m: number;
  travel_time_s: number;
  street_name: string;
}

export interface Delivery {
  id: string;
  pickup_addr: Intersection;
  delivery_addr: Intersection;
  pickup_service_s: number;
  delivery_service_s: number;
  courier?: Courier;
  hour_departure?: string;
}

export interface Tour {
  courier: Courier;
  deliveries: Delivery[];
  total_travel_time_s: number;
  total_service_time_s: number;
  total_distance_m: number;
  start_time?: string;
  end_time?: string;
}

export interface Map {
  intersections: Intersection[];
  road_segments: RoadSegment[];
  couriers: Courier[];
  deliveries: Delivery[];
}

// API Error response
export interface ApiError {
  detail: string;
  status_code: number;
}