// Prefer explicit backend URL from Vite env during development. Set VITE_API_BASE
// to something like "http://127.0.0.1:8000/api/v1" in .env if needed.
const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000/api/v1'

export async function uploadMap(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${API_BASE}/map/`, { method: 'POST', body: fd })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getState() {
  const res = await fetch(`${API_BASE}/state/`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function addCourier(courier: any) {
  const res = await fetch(`${API_BASE}/couriers/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(courier) })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function addRequest(request: any) {
  const res = await fetch(`${API_BASE}/requests/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request) })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function computeTours() {
  const res = await fetch(`${API_BASE}/tours/compute`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function saveState() {
  const res = await fetch(`${API_BASE}/state/save`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
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