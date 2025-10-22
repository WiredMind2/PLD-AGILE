import type { Map, Delivery, ApiError, Tour } from '@/types/api';

const API_BASE_URL = 'http://localhost:8000/api/v1';

class ApiClient {
  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
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

  // Map endpoints
  async uploadMap(file: File): Promise<Map> {
    const formData = new FormData();
    formData.append('file', file);

    return this.request<Map>('/map', {
      method: 'POST',
      headers: {},
      body: formData,
    });
  }

  // Delivery endpoints
  async uploadDeliveryRequests(file: File): Promise<Delivery[]> {
    const formData = new FormData();
    formData.append('file', file);

    return this.request<Delivery[]>('/deliveries', {
      method: 'POST',
      headers: {},
      body: formData,
    });
  }
  
  async uploadRequestsFile(file: File): Promise<Delivery[]> {
    const formData = new FormData();
    formData.append('file', file);
    return this.request<Delivery[]>('/requests/upload', {
      method: 'POST',
      headers: {},
      body: formData,
    });
  }

  async getState(): Promise<any> {
    return this.request<any>('/state/', { method: 'GET' })
  }

  async addCourier(courier: any): Promise<any> {
    return this.request<any>('/couriers/', {
      method: 'POST',
      body: JSON.stringify(courier),
    })
  }

  async addRequest(request: any): Promise<any> {
    return this.request<any>('/requests/', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async computeTours(): Promise<any> {
    return this.request<any>(`/tours/compute`, { method: 'POST' })
  }

  async saveTours(tour: any): Promise<any> {
    (tour.tours || []).forEach((t: Tour) => {
      t.name=tour.tour_name;
      return this.request<any>(`/tours/save`, { 
      method: 'POST', 
      body: JSON.stringify(t),
    })
  });
}

  async saveState(): Promise<any> {
    return this.request<any>('/state/save', { method: 'POST' })
  }

  async deleteRequest(deliveryId: string): Promise<{ detail: string }> {
    return this.request<{ detail: string }>(`/requests/${deliveryId}`, {
      method: 'DELETE',
    })
  }
}

export const apiClient = new ApiClient();