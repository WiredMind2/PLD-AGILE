import { useCallback } from "react";
import { apiClient } from "@/lib/api";
import type { Delivery } from "@/types/api";

export function useCourierOperations(
  handleError: (err: unknown) => void,
  setLoading: (loading: boolean) => void,
  setError: (error: string | null) => void,
  setCouriersState: React.Dispatch<React.SetStateAction<string[]>>,
  deliveries: Delivery[],
  setDeliveries: React.Dispatch<React.SetStateAction<Delivery[]>>
) {
  // This should only be called by the user, not automatically
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
  }, [handleError, setLoading, setError, setCouriersState]);

  const addCourier = useCallback(
    async (courier: string) => {
      try {
        setLoading(true);
        setError(null);
        await apiClient.addCourier(courier);
        setCouriersState((prev) => [...prev, courier]);
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError, setLoading, setError, setCouriersState]
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
            return { ...d, courier: null };
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
  }, [handleError, setLoading, setError, setCouriersState, deliveries, setDeliveries]);

  return {
    fetchCouriers,
    addCourier,
    deleteCourier,
  };
}