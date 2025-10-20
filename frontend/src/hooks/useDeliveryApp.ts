import { useState, useCallback } from 'react';
import { apiClient } from '@/lib/api';
import type { Map, Delivery, Tour, Courier } from '@/types/api';

export function useDeliveryApp() {
  const [map, setMap] = useState<Map | null>(null);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [tours] = useState<Tour[]>([]);
  const [couriers] = useState<Courier[]>([]);
  const [toursState, setToursState] = useState<Tour[]>([]);
  const [couriersState, setCouriersState] = useState<Courier[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback((err: unknown) => {
    const message = err instanceof Error ? err.message : 'An unexpected error occurred';
    setError(message);
    console.error('API Error:', err);
  }, []);

  // Map operations
  const uploadMap = useCallback(async (file: File) => {
    try {
      (true);
      setError(null);
      const mapData = await apiClient.uploadMap(file);
      setMap(mapData);
      // populate couriersState from map if present
      try {
        if (mapData && Array.isArray(mapData.couriers)) {
          setCouriersState(mapData.couriers as unknown as Courier[]);
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

  const saveTours = useCallback(async (tour: any) => {
    try {
      setLoading(true);
      setError(null);
      await apiClient.saveTours(tour);
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  // Computed values
  const stats = {
    activeCouriers: couriers.length,
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
    computeTours,
    saveTours,
    
    // Utils
    clearError: () => setError(null),
  };
}