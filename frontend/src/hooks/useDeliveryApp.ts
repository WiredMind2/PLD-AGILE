import { useState, useCallback } from 'react';
import { apiClient } from '@/lib/api';
import { type Map, type Delivery, type Tour, Courier } from '@/types/api';

export function useDeliveryApp() {
  const [map, setMap] = useState<Map | null>(null);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [tours] = useState<Tour[]>([]);
  const [toursState, setToursState] = useState<Tour[]>([]);
  const [couriers, setCouriers] = useState<Courier[]>([{ id: 'courier-1', name: 'Courier 1' }]);
  const [courierAssignments, setCourierAssignments] = useState<Record<string, string[]>>({ 'courier-1': [] });
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
      setLoading(true);
      setError(null);
      const mapData = await apiClient.uploadMap(file);
      setMap(mapData);
      // populate couriersState from map if present
      try {
        if (mapData && Array.isArray(mapData.couriers)) {
          //console.log("Setting couriers from map data:", mapData.couriers.length);
          //setCouriersState(mapData.couriers.length);
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

  const addRequest = useCallback(async (request: Pick<Delivery, 'pickup_addr' | 'delivery_addr' | 'pickup_service_s' | 'delivery_service_s'>) => {
    try {
      setLoading(true);
      setError(null);
      const created = await apiClient.addRequest(request);
      // Append to local state; backend may return string node ids, so cast for now
      setDeliveries((prev) => [...prev, created as unknown as Delivery]);
      // auto-assign created request to first courier by default
      const firstCourierId = couriers.length > 0 ? couriers[0].id : 'courier-1';
      if (created && (created as any).id != null) {
        setCourierAssignments((prev) => {
          const copy = { ...prev } as Record<string, string[]>;
          if (!copy[firstCourierId]) copy[firstCourierId] = [];
          const idStr = String((created as any).id);
          if (!copy[firstCourierId].includes(idStr)) {
            copy[firstCourierId] = [...copy[firstCourierId], idStr];
          }
          return copy;
        });
      }
      return created;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError, couriers]);

  const uploadRequestsFile = useCallback(async (file: File) => {
    try {
      setLoading(true);
      setError(null);
      const newDeliveries = await apiClient.uploadRequestsFile(file);
      setDeliveries((prev) => [...prev, ...newDeliveries]);
      // auto-assign uploaded requests to first courier by default
      const firstCourierId = couriers.length > 0 ? couriers[0].id : 'courier-1';
      setCourierAssignments((prev) => {
        const copy = { ...prev } as Record<string, string[]>;
        const oldArr = copy[firstCourierId] || [];
        // set for quick deduplication including existing ids
        const existing = new Set(oldArr.map(String));
        const toAdd: string[] = [];
        newDeliveries.forEach((d: any) => {
          const idStr = d && d.id != null ? String(d.id) : null;
          if (idStr && !existing.has(idStr)) {
            existing.add(idStr);
            toAdd.push(idStr);
          }
        });
        // create a new array instead of mutating
        copy[firstCourierId] = [...oldArr, ...toAdd];
        return copy;
      });
      return newDeliveries;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError, couriers]);

  const deleteRequest = useCallback(async (deliveryId: string) => {
    try {
      setLoading(true);
      setError(null);
      await apiClient.deleteRequest(deliveryId);
      setDeliveries((prev) => prev.filter((d) => String(d.id) !== String(deliveryId)));
      // remove from any courier assignments
      setCourierAssignments((prev) => {
        const copy = { ...prev } as Record<string, string[]>;
        Object.keys(copy).forEach((k) => {
          copy[k] = (copy[k] || []).filter((id) => String(id) !== String(deliveryId));
        });
        return copy;
      });
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

  // Couriers management
  const addCourier = useCallback(() => {
    setCouriers((prev) => {
      const next = [
        ...prev,
        {
          id: `courier-${prev.length + 1}`,
          name: `Courier ${prev.length + 1}`,
        },
      ];
      const newId = `courier-${next.length}`;
      setCourierAssignments((assignPrev) => ({ ...assignPrev, [newId]: [] }));
      return next;
    });

  }, []);

  const removeCourier = useCallback(() => {
    setCouriers((prev) => {
      let next = prev.length > 0 ? prev.slice(0, -1) : prev;
      // remove assignment bucket for removed courier
      setCourierAssignments((assignPrev) => {
        const copy = { ...assignPrev } as Record<string, string[]>;
        const removed = prev.length > 0 ? prev[prev.length - 1] : null;
        if (removed && copy[removed.id]) {
          delete copy[removed.id];
        }
        return copy;
      });
      return next;
    });
  }, []);

  const assignCourierToDelivery = useCallback((deliveryId: string, courierId?: string | null) => {
    setCourierAssignments((prev) => {
      const next: Record<string, string[]> = {};
      // Start with empty arrays for all known couriers to preserve keys
      Object.keys(prev).forEach((k) => { next[k] = [...(prev[k] || [])]; });
      // Ensure all current couriers have an entry
      couriers.forEach((c) => { if (!next[c.id]) next[c.id] = []; });
      // remove deliveryId from any courier that has it
      Object.keys(next).forEach((k) => { next[k] = next[k].filter((id) => String(id) !== String(deliveryId)); });
      // if courierId provided, add it
      if (courierId) {
        if (!next[courierId]) next[courierId] = [];
        next[courierId] = [...next[courierId], deliveryId];
      }
      return next;
    });
  }, [couriers]);

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
    loading,
    error,
    stats,
    couriers,
    courierAssignments,
    
    // Actions
    uploadMap,
    addRequest,
    uploadRequestsFile,
    deleteRequest,
    computeTours,
    addCourier,
    removeCourier,
  assignCourierToDelivery,
    
    // Utils
    clearError: () => setError(null),
  };
}