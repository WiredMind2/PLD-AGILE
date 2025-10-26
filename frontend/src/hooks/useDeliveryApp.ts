import { useState, useCallback } from "react";
import { apiClient } from "@/lib/api";
import type { Map, Delivery, Tour } from "@/types/api";

export function useDeliveryApp() {
  const [map, setMap] = useState<Map | null>(null);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [tours] = useState<Tour[]>([]);
  const [toursState, setToursState] = useState<Tour[]>([]);
  const [couriersState, setCouriersState] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback((err: unknown) => {
    const message =
      err instanceof Error ? err.message : "An unexpected error occurred";
    setError(message);
    console.error("API Error:", err);
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
          setCouriersState(mapData.couriers as unknown as string[]);
          // if map has no couriers, create a default one on the server and update local state
          if ((mapData.couriers || []).length === 0) {
            try {
              const newId = `C${Date.now()}`;
              const created = await apiClient.addCourier(newId).catch(() => null);
              if (created) setCouriersState((prev) => [...(prev || []), String(created)]);
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
  const uploadDeliveryRequests = useCallback(
    async (file: File) => {
      try {
        setLoading(true);
        setError(null);
        const newDeliveries = await apiClient.uploadDeliveryRequests(file);
        const defaultCourierId = couriersState?.[0] ?? null;
        if (defaultCourierId) {
          await Promise.all(
            newDeliveries.map((d: any) =>
              apiClient
                .assignDelivery(String(d.id), String(defaultCourierId))
                .catch(() => undefined)
            )
          );
        }
        setDeliveries((prev) => [
          ...prev,
          ...(defaultCourierId
            ? newDeliveries.map((d: any) => ({
                ...(d as any),
                courier: String(defaultCourierId),
              }))
            : newDeliveries),
        ]);
        return newDeliveries;
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError, couriersState]
  );

  const addRequest = useCallback(
    async (
      request: Pick<
        Delivery,
        | "pickup_addr"
        | "delivery_addr"
        | "pickup_service_s"
        | "delivery_service_s"
      >
    ) => {
      try {
        setLoading(true);
        setError(null);
        const created = await apiClient.addRequest(request);
        const defaultCourierId = couriersState?.[0] ?? null;
        if (defaultCourierId) {
          await apiClient
            .assignDelivery(String(created.id), String(defaultCourierId))
            .catch(() => undefined);
          setDeliveries((prev) => [
            ...prev,
            {
              ...(created as any),
              courier: String(defaultCourierId),
            } as unknown as Delivery,
          ]);
        } else {
          setDeliveries((prev) => [...prev, created as unknown as Delivery]);
        }
        return created;
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError, couriersState]
  );

  // Resolve nearest nodes then create request
  const createRequestFromCoords = useCallback(
    async (
      pickup: [number, number],
      delivery: [number, number],
      options?: { pickup_service_s?: number; delivery_service_s?: number }
    ) => {
      const pickup_service_s = options?.pickup_service_s ?? 120;
      const delivery_service_s = options?.delivery_service_s ?? 120;
      try {
        setLoading(true);
        setError(null);
        const ack = await apiClient.mapAckPair(pickup, delivery);
        const pickupNode = ack?.pickup.id;
        const deliveryNode = ack?.delivery.id;
        if (!pickupNode || !deliveryNode) {
          throw new Error("Nearest nodes not found for provided coordinates");
        }
        const created = await apiClient.addRequest({
          pickup_addr: pickupNode as any,
          delivery_addr: deliveryNode as any,
          pickup_service_s,
          delivery_service_s,
        });
        setDeliveries((prev) => [...prev, created as unknown as Delivery]);
        return { created, pickupNode, deliveryNode };
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

  // Courier operations
  const fetchCouriers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const cs = await apiClient.getCouriers();
      setCouriersState(cs as string[]);
      return cs;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  const addCourier = useCallback(
    async (courier: string) => {
      try {
        setLoading(true);
        setError(null);
        const created = await apiClient.addCourier(courier as any);
        setCouriersState((prev) => [...prev, created as string]);
        return created;
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

  const deleteCourier = useCallback(async (courierId: string) => {
    try {
      setLoading(true);
      setError(null);
      await apiClient.deleteCourier(courierId);
      setCouriersState((prev) => prev.filter((c) => c !== courierId));
      try {
        const toUnassign = deliveries.filter((d) => {
          try {
            const assignedId = d?.courier;
            return assignedId && assignedId === courierId;
          } catch {
            return false;
          }
        });
        await Promise.all(
          toUnassign.map((d) =>
            apiClient.assignDelivery(String(d.id), null).catch(() => undefined)
          )
        );
      } catch (e) {
      }
      setDeliveries((prev) => prev.map((d) => {
        try {
          const assignedId = d?.courier;
          if (assignedId && assignedId === courierId) {
            return { ...d, courier: null } as any;
          }
        } catch (e) {
        }
        return d;
      }));
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError, deliveries]);

  const uploadRequestsFile = useCallback(
    async (file: File) => {
      try {
        setLoading(true);
        setError(null);
        const newDeliveries = await apiClient.uploadRequestsFile(file);
        // Assign to default courier if present
        const defaultCourierId = couriersState?.[0] ?? null;
        if (defaultCourierId) {
          await Promise.all(
            newDeliveries.map((d: any) =>
              apiClient
                .assignDelivery(String(d.id), String(defaultCourierId))
                .catch(() => undefined)
            )
          );
        }

        setDeliveries((prev) => [
          ...prev,
          ...(defaultCourierId
            ? newDeliveries.map((d: any) => ({
                ...(d as any),
                courier: String(defaultCourierId),
              }))
            : newDeliveries),
        ]);
        return newDeliveries;
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError, couriersState]
  );

  const deleteRequest = useCallback(
    async (deliveryId: string) => {
      try {
        setLoading(true);
        setError(null);
        await apiClient.deleteRequest(deliveryId);
        setDeliveries((prev) =>
          prev.filter((d) => String(d.id) !== String(deliveryId))
        );
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

  const assignDeliveryToCourier = useCallback(
    async (deliveryId: string, courierId: string | null) => {
      try {
        setLoading(true);
        setError(null);
        await apiClient.assignDelivery(deliveryId, courierId);
        // update local state to reflect assignment
        setDeliveries((prev) =>
          prev.map((d) =>
            String(d.id) === String(deliveryId)
              ? ({ ...d, courier: courierId as unknown as any } as Delivery)
              : d
          )
        );
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

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

  const geocodeAddress = useCallback(
    async (address: string): Promise<{ lat: number; lon: number } | null> => {
      // Utilise Nominatim (OpenStreetMap) pour géocoder
      try {
        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
          address
        )}`;
        console.log("Geocoding address with URL:", url);
        const res = await fetch(url);
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return { lat: parseFloat(data[0].lat), lon: parseFloat(data[0].lon) };
        }
        throw new Error(`Aucun résultat pour l'adresse: ${address}`);
      } catch (e) {
        if (e instanceof Error) {
          setError(`${e.message}`);
          throw new Error(`${e.message}`);
        }
        setError(`Erreur inattendue lors du géocodage`);
        throw new Error("Erreur inattendue lors du géocodage");
      }
    },
    []
  );

  // Saved tours (named snapshots)
  const listSavedTours = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      return await apiClient.listSavedTours();
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  const saveNamedTour = useCallback(
    async (name: string) => {
      try {
        setLoading(true);
        setError(null);
        return await apiClient.saveNamedTour(name);
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

  const deleteNamedTour = useCallback(
    async (name: string) => {
      try {
        setLoading(true);
        setError(null);
        return await apiClient.deleteNamedTour(name);
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

  const loadNamedTour = useCallback(
    async (name: string) => {
      try {
        setLoading(true);
        setError(null);
        const res = await apiClient.loadNamedTour(name);
        const st = (res && (res as any).state) || (await apiClient.getState());
        const mp = st?.map ?? null;
        setMap(mp as Map | null);
        setCouriersState((st?.couriers ?? []) as string[]);
        setDeliveries((st?.deliveries ?? []) as Delivery[]);
        setToursState((st?.tours ?? []) as Tour[]);
        return st;
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

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
