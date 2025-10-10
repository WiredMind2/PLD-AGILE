import type { 
  Map, 
  Delivery, 
  ApiError 
} from '@/types/api';

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
}

export const apiClient = new ApiClient();