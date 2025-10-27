import { useCallback } from "react";
import { apiClient } from "@/lib/api";
import type { Map, Delivery, Tour } from "@/types/api";

export function useSavedTours(
  handleError: (err: unknown) => void,
  setLoading: (loading: boolean) => void,
  setError: (error: string | null) => void,
  setMap: (map: Map | null) => void,
  setCouriersState: React.Dispatch<React.SetStateAction<string[]>>,
  setDeliveries: React.Dispatch<React.SetStateAction<Delivery[]>>,
  setToursState: React.Dispatch<React.SetStateAction<Tour[]>>
) {
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
  }, [handleError, setLoading, setError]);

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
    [handleError, setLoading, setError]
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
    [handleError, setLoading, setError]
  );

  const loadNamedTour = useCallback(
    async (name: string) => {
      try {
        setLoading(true);
        setError(null);
        const res = await apiClient.loadNamedTour(name);
        const st = (res && res.state) || (await apiClient.getState());
        const mp = st?.map ?? null;
        setMap(mp);
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
    [handleError, setLoading, setError, setMap, setCouriersState, setDeliveries, setToursState]
  );

  return {
    listSavedTours,
    saveNamedTour,
    deleteNamedTour,
    loadNamedTour,
  };
}