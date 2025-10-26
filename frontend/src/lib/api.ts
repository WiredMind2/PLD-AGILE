import type { Map, Delivery, ApiError } from "@/types/api";

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
  ): Promise<{ pickup: any | null; delivery: any | null }> {
    const params = new URLSearchParams({
      pickup_lat: String(pickup[0]),
      pickup_lng: String(pickup[1]),
      delivery_lat: String(delivery[0]),
      delivery_lng: String(delivery[1]),
    });
    return this.request<{ pickup: any | null; delivery: any | null }>(
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

  async getState(): Promise<any> {
    return this.request<any>("/state/", { method: "GET" });
  }

  async addCourier(courier: any): Promise<any> {
    return this.request<any>("/couriers/", {
      method: "POST",
      body: JSON.stringify(courier),
    });
  }

  async getCouriers(): Promise<any[]> {
    return this.request<any[]>("/couriers/", { method: "GET" });
  }

  async deleteCourier(courierId: string): Promise<{ detail: string }> {
    return this.request<{ detail: string }>(`/couriers/${courierId}`, {
      method: "DELETE",
    });
  }

  async addRequest(request: any): Promise<any> {
    return this.request<any>("/requests/", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  async computeTours(): Promise<any> {
    return this.request<any>(`/tours/compute`, { method: "POST" });
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
    console.log("API assignDelivery", deliveryId, courierId);
    return this.request<{ detail: string }>(`/requests/${deliveryId}/assign`, {
      method: "PATCH",
      body: JSON.stringify({ courier_id: courierId }),
    });
  }

  // Saved tours endpoints
  async listSavedTours(): Promise<
    Array<{ name: string; saved_at?: string; size_bytes?: number }>
  > {
    return this.request("/saved_tours/", { method: "GET" });
  }

  async saveNamedTour(name: string): Promise<any> {
    return this.request("/saved_tours/save", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  }

  async loadNamedTour(name: string): Promise<any> {
    return this.request("/saved_tours/load", {
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
