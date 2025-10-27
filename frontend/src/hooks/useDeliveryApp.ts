import { useState, useCallback } from "react";
import { apiClient } from "@/lib/api";
import type { Map, Delivery, Tour } from "@/types/api";
import { useMapOperations } from "./useMapOperations";
import { useDeliveryOperations } from "./useDeliveryOperations";
import { useCourierOperations } from "./useCourierOperations";
import { useTourOperations } from "./useTourOperations";
import { useSavedTours } from "./useSavedTours";
import { useGeocoding } from "./useGeocoding";

export function useDeliveryApp() {
  const [map, setMap] = useState<Map | null>(null);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [tours] = useState<Tour[]>([]);
  const [toursState, setToursState] = useState<Tour[]>([]);
  const [couriersState, setCouriersState] = useState<string[]>([]);
  const [courierCounter, setCourierCounter] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback((err: unknown) => {
    const message =
      err instanceof Error ? err.message : "An unexpected error occurred";
    setError(message);
    console.error("API Error:", err);
  }, []);

  const clearServerState = useCallback(async () => {
    console.log("Clearing server state...");
    try {
      setLoading(true);
      setError(null);
      await apiClient.clearState();
      setMap(null);
      setDeliveries([]);
      setToursState([]);
      setCouriersState([]);
      setCourierCounter(1);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  // Use sub-hooks
  const { uploadMap } = useMapOperations(handleError, setLoading, setError, setMap);
  const { uploadDeliveryRequests, addRequest, createRequestFromCoords, uploadRequestsFile, deleteRequest, assignDeliveryToCourier } = useDeliveryOperations(handleError, setLoading, setError, setDeliveries, couriersState);
  const { fetchCouriers, addCourier, deleteCourier } = useCourierOperations(handleError, setLoading, setError, setCouriersState, deliveries, setDeliveries);
  const { computeTours } = useTourOperations(handleError, setLoading, setError, setToursState);
  const { listSavedTours, saveNamedTour, deleteNamedTour, loadNamedTour } = useSavedTours(handleError, setLoading, setError, setMap, setCouriersState, setDeliveries, setToursState);
  const { geocodeAddress } = useGeocoding(setError);

  const createNewCourier = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const newId = `${courierCounter}`;
      console.log("Creating new courier with ID:", newId);
      const created = await apiClient.addCourier(newId);
      if (created) {
        setCouriersState(prev => [...prev, String(created)]);
        setCourierCounter(prev => prev + 1);
        return String(created);
      }
      return null;
    } catch (err) {
      handleError(err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [handleError, setLoading, setError, setCouriersState, courierCounter, setCourierCounter]);

  // Computed values
  const stats = {
    activeCouriers: couriersState.length,
    totalCouriers: 1,
    deliveryRequests: deliveries.length,
    totalDistance: tours.reduce((sum, tour) => sum + tour.total_distance_m, 0),
    totalTime: tours.reduce((sum, tour) => sum + tour.total_travel_time_s, 0),
  };

  return {
    // State
    map,
    setMap,
    deliveries,
    setDeliveries,
    tours: toursState,
    couriers: couriersState,
    setCouriersState,
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
    createNewCourier,
    computeTours,
    assignDeliveryToCourier,
    geocodeAddress,
    createRequestFromCoords,

    clearServerState,
    listSavedTours,
    saveNamedTour,
    loadNamedTour,
    deleteNamedTour,

    // Utils
    clearError: () => setError(null),
  };
}
