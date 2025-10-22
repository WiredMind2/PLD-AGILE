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
  const [computedTours, setComputedTours] = useState<any[] | null>(null);


  const handleError = useCallback((err: unknown) => {
    const message = err instanceof Error ? err.message : 'An unexpected error occurred';
    setError(message);
    console.error('API Error:', err);
  }, []);

  // Map operations
  const uploadMap = useCallback(async (file: File) => {
    try {
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

  const loadTours = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const loadedTours = await apiClient.getTours();
      setComputedTours(loadedTours as unknown as Tour[]);
      return loadedTours;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  // Test function to set sample tour data for testing UI
  const setTestTours = useCallback(() => {
    const sampleTours = [
      {
        courier: { id: 'courier-1', name: 'Courier 1' },
        total_distance_m: 2500,
        total_travel_time_s: 1800,
        deliveries: [
          {
            id: 'delivery-1',
            pickup_addr: '12345',
            delivery_addr: '67890',
            pickup_service_s: 300,
            delivery_service_s: 300
          },
          {
            id: 'delivery-2',
            pickup_addr: '11111',
            delivery_addr: '22222',
            pickup_service_s: 240,
            delivery_service_s: 180
          }
        ],
        route_intersections: ['12345', '11111', '22222', '67890']
      },
      {
        courier: { id: 'courier-2', name: 'Courier 2' },
        total_distance_m: 3200,
        total_travel_time_s: 2400,
        deliveries: [
          {
            id: 'delivery-3',
            pickup_addr: '33333',
            delivery_addr: '44444',
            pickup_service_s: 360,
            delivery_service_s: 240
          },
          {
            id: 'delivery-4',
            pickup_addr: '55555',
            delivery_addr: '66666',
            pickup_service_s: 180,
            delivery_service_s: 300
          },
          {
            id: 'delivery-5',
            pickup_addr: '77777',
            delivery_addr: '88888',
            pickup_service_s: 300,
            delivery_service_s: 180
          }
        ],
        route_intersections: ['33333', '55555', '77777', '44444', '66666', '88888']
      }
    ];
    
    setToursState(sampleTours as unknown as Tour[]);
    setComputedTours(sampleTours);
    console.log('Test tours set:', sampleTours);
  }, []);


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
    loadTours,
    computedTours,

    
    // Utils
    clearError: () => setError(null),
  };
}