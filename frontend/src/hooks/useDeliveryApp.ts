import { useState, useCallback, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import type { Map, Delivery, Tour, Courier } from '@/types/api';

export function useDeliveryApp() {
  const [map, setMap] = useState<Map | null>(null);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [tours] = useState<Tour[]>([]);
  const [toursState, setToursState] = useState<Tour[]>([]);
  const [couriersState, setCouriersState] = useState<Courier[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback((err: unknown) => {
    const message = err instanceof Error ? err.message : 'An unexpected error occurred';
    setError(message);
    console.error('API Error:', err);
  }, []);

  const clearServerState = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      await apiClient.clearState();
      setMap(null);
      setDeliveries([]);
      setToursState([]);
      setCouriersState([]);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  // Map operations
  const uploadMap = useCallback(async (file: File) => {
    try {
      setLoading(true);
      setError(null);
      const mapData = await apiClient.uploadMap(file);
      setMap(mapData);
      // populate couriersState from map if present
      try {
        if (mapData && Array.isArray(mapData.couriers)) {
          setCouriersState(mapData.couriers as unknown as Courier[]);
          // if map has no couriers, create a default one on the server and update local state
          if ((mapData.couriers || []).length === 0) {
            try {
              const loc = mapData.intersections?.[0] ?? { id: '0', latitude: 45.764043, longitude: 4.835659 };
              const created = await apiClient.addCourier({ name: 'Courier 1', id: `C${Date.now()}`, current_location: loc as any });
              setCouriersState((prev) => [...(prev || []), created as unknown as Courier]);
            } catch (e) {
              // ignore creation errors
            }
          }
        }
      } catch (e) {
        // ignore
      }
      //setCouriers(mapData.couriers);
      return mapData;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  // Delivery operations
  const uploadDeliveryRequests = useCallback(async (file: File) => {
    try {
      setLoading(true);
      setError(null);
      const newDeliveries = await apiClient.uploadDeliveryRequests(file);
      setDeliveries((prev) => [...prev, ...newDeliveries]);
      return newDeliveries;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  const addRequest = useCallback(async (request: Pick<Delivery, 'pickup_addr' | 'delivery_addr' | 'pickup_service_s' | 'delivery_service_s'>) => {
    try {
      setLoading(true);
      setError(null);
      const created = await apiClient.addRequest(request);
      // Append to local state; backend may return string node ids, so cast for now
      setDeliveries((prev) => [...prev, created as unknown as Delivery]);
      return created;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  // Courier operations
  const fetchCouriers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const cs = await apiClient.getCouriers();
      setCouriersState(cs as unknown as Courier[]);
      return cs;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  const addCourier = useCallback(async (courier: Partial<Courier>) => {
    try {
      setLoading(true);
      setError(null);
      const created = await apiClient.addCourier(courier as any);
      setCouriersState((prev) => [...prev, created as unknown as Courier]);
      return created;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  const deleteCourier = useCallback(async (courierId: string) => {
    try {
      setLoading(true);
      setError(null);
      await apiClient.deleteCourier(courierId);
      setCouriersState((prev) => prev.filter((c) => String(c.id) !== String(courierId)));
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  const uploadRequestsFile = useCallback(async (file: File) => {
    try {
      setLoading(true);
      setError(null);
      const newDeliveries = await apiClient.uploadRequestsFile(file);
      setDeliveries((prev) => [...prev, ...newDeliveries]);
      return newDeliveries;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  const deleteRequest = useCallback(async (deliveryId: string) => {
    try {
      setLoading(true);
      setError(null);
      await apiClient.deleteRequest(deliveryId);
      setDeliveries((prev) => prev.filter((d) => String(d.id) !== String(deliveryId)));
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  const assignDeliveryToCourier = useCallback(async (deliveryId: string, courierId: string | null) => {
    try {
      setLoading(true);
      setError(null);
      await apiClient.assignDelivery(deliveryId, courierId);
      // update local state to reflect assignment
      setDeliveries((prev) => prev.map((d) => (String(d.id) === String(deliveryId) ? ({ ...d, courier: (courierId as unknown) as any } as Delivery) : d)));
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  const computeTours = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.computeTours();
      // assume res is an array of tours
      setToursState(res as unknown as Tour[]);
      return res;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  // Computed values
  const stats = {
    activeCouriers: couriersState.length,
    deliveryRequests: deliveries.length,
    totalDistance: tours.reduce((sum, tour) => sum + tour.total_distance_m, 0),
    totalTime: tours.reduce((sum, tour) => sum + tour.total_travel_time_s, 0),
  };

  return {
    // State
    map,
    deliveries,
    tours: toursState,
    couriers: couriersState,
    loading,
    error,
    stats,
    
    // Actions
    uploadMap,
    uploadDeliveryRequests,
    addRequest,
    uploadRequestsFile,
    deleteRequest,
    fetchCouriers,
    addCourier,
    deleteCourier,
    computeTours,
    assignDeliveryToCourier,

    clearServerState,
    
    // Utils
    clearError: () => setError(null),
  };
}