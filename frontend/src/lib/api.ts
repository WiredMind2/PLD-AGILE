import type { Map, Delivery, Tour, Intersection, SavedTourInfo, ApiError } from "@/types/api";

const API_BASE_URL = "http://localhost:8000/api/v1";

class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;

    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Map helpers
  async mapAckPair(
    pickup: [number, number],
    delivery: [number, number]
  ): Promise<{ pickup: Intersection | null; delivery: Intersection | null }> {
    const params = new URLSearchParams({
      pickup_lat: String(pickup[0]),
      pickup_lng: String(pickup[1]),
      delivery_lat: String(delivery[0]),
      delivery_lng: String(delivery[1]),
    });
    return this.request<{ pickup: Intersection | null; delivery: Intersection | null }>(
      `/map/ack_pair?${params.toString()}`,
      {
        method: "GET",
      }
    );
  }

  async clearState(): Promise<void> {
    return this.request<void>("/state/clear_state", { method: "DELETE" });
  }

  // Map endpoints
  async uploadMap(file: File): Promise<Map> {
    const formData = new FormData();
    formData.append("file", file);

    return this.request<Map>("/map/", {
      method: "POST",
      headers: {},
      body: formData,
    });
  }

  async getUnreachableNodes(targetNodeId?: string): Promise<{ target_node_id: string; unreachable_count: number; unreachable_nodes: string[] }> {
    const url = targetNodeId ? `/map/unreachable_nodes?target_node_id=${encodeURIComponent(String(targetNodeId))}` : `/map/unreachable_nodes`;
    // Use base request method but pass full endpoint
    return this.request<{ target_node_id: string; unreachable_count: number; unreachable_nodes: string[] }>(url, {
      method: "GET",
    });
  }

  // Delivery endpoints
  async uploadDeliveryRequests(file: File): Promise<Delivery[]> {
    const formData = new FormData();
    formData.append("file", file);

    return this.request<Delivery[]>("/deliveries/", {
      method: "POST",
      headers: {},
      body: formData,
    });
  }

  async uploadRequestsFile(file: File): Promise<Delivery[]> {
    const formData = new FormData();
    formData.append("file", file);
    return this.request<Delivery[]>("/requests/upload", {
      method: "POST",
      headers: {},
      body: formData,
    });
  }

  async getState(): Promise<{ map: Map | null; couriers: string[]; deliveries: Delivery[]; tours: Tour[] }> {
    return this.request<{ map: Map | null; couriers: string[]; deliveries: Delivery[]; tours: Tour[] }>("/state/", { method: "GET" });
  }

  async addCourier(courier: string): Promise<string> {
    return this.request<string>("/couriers/", {
      method: "POST",
      body: JSON.stringify(courier),
    });
  }

  async getCouriers(): Promise<string[]> {
    return this.request<string[]>("/couriers/", { method: "GET" });
  }

  async deleteCourier(courierId: string): Promise<{ detail: string }> {
    return this.request<{ detail: string }>(`/couriers/${courierId}`, {
      method: "DELETE",
    });
  }

  async addRequest(request: Omit<Delivery, 'id'>): Promise<Delivery> {
    return this.request<Delivery>("/requests/", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  async computeTours(): Promise<Tour[]> {
    return this.request<Tour[]>(`/tours/compute`, { method: "POST" });
  }

  async deleteRequest(deliveryId: string): Promise<{ detail: string }> {
    return this.request<{ detail: string }>(`/requests/${deliveryId}`, {
      method: "DELETE",
    });
  }

  async assignDelivery(
    deliveryId: string,
    courierId: string | null
  ): Promise<{ detail: string }> {
    return this.request<{ detail: string }>(`/requests/${deliveryId}/assign`, {
      method: "PATCH",
      body: JSON.stringify({ courier_id: courierId }),
    });
  }

  async listSavedTours(): Promise<SavedTourInfo[]> {
    return this.request<SavedTourInfo[]>("/saved_tours/", { method: "GET" });
  }

  async saveNamedTour(name: string): Promise<SavedTourInfo> {
    return this.request<SavedTourInfo>("/saved_tours/save", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  }

  async loadNamedTour(name: string): Promise<{ detail: string; state: { map: Map | null; couriers: string[]; deliveries: Delivery[]; tours: Tour[] } }> {
    return this.request<{ detail: string; state: { map: Map | null; couriers: string[]; deliveries: Delivery[]; tours: Tour[] } }>("/saved_tours/load", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  }

  async deleteNamedTour(name: string): Promise<{ detail: string }> {
    return this.request<{ detail: string }>(`/saved_tours/delete`, {
      method: "DELETE",
      body: JSON.stringify({ name }),
    });
  }
}

export const apiClient = new ApiClient();
