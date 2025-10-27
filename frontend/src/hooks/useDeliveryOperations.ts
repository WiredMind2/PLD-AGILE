import { useCallback } from "react";
import { apiClient } from "@/lib/api";
import type { Delivery } from "@/types/api";

export function useDeliveryOperations(
  handleError: (err: unknown) => void,
  setLoading: (loading: boolean) => void,
  setError: (error: string | null) => void,
  setDeliveries: React.Dispatch<React.SetStateAction<Delivery[]>>,
  couriersState: string[]
) {
  const uploadDeliveryRequests = useCallback(
    async (file: File) => {
      try {
        setLoading(true);
        setError(null);
        const newDeliveries = await apiClient.uploadDeliveryRequests(file);
        const defaultCourierId = couriersState?.[0] ?? null;
        if (defaultCourierId) {
          await Promise.all(
            newDeliveries.map((d: Delivery) =>
              apiClient
                .assignDelivery(String(d.id), String(defaultCourierId))
                .catch(() => undefined)
            )
          );
        }
        setDeliveries((prev) => [
          ...prev,
          ...(defaultCourierId
            ? newDeliveries.map((d) => ({
                ...d,
                courier: defaultCourierId,
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
    [handleError, setLoading, setError, setDeliveries, couriersState]
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
              ...created,
              courier: defaultCourierId,
            },
          ]);
        } else {
          setDeliveries((prev) => [...prev, created]);
        }
        return created;
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError, setLoading, setError, setDeliveries, couriersState]
  );

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
        const pickupNode = ack?.pickup;
        const deliveryNode = ack?.delivery;
        if (!pickupNode || !deliveryNode) {
          throw new Error("Nearest nodes not found for provided coordinates");
        }
        const created = await apiClient.addRequest({
          pickup_addr: pickupNode.id,
          delivery_addr: deliveryNode.id,
          pickup_service_s,
          delivery_service_s,
        });
        setDeliveries((prev) => [...prev, created]);
        return { created, pickupNode, deliveryNode };
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError, setLoading, setError, setDeliveries]
  );

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
            newDeliveries.map((d) =>
              apiClient
                .assignDelivery(d.id, defaultCourierId)
                .catch(() => undefined)
            )
          );
        }

        setDeliveries((prev) => [
          ...prev,
          ...(defaultCourierId
            ? newDeliveries.map((d) => ({
                ...d,
                courier: defaultCourierId,
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
    [handleError, setLoading, setError, setDeliveries, couriersState]
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
    [handleError, setLoading, setError, setDeliveries]
  );

  const assignDeliveryToCourier = useCallback(
    async (deliveryId: string, courierId: string | null) => {
      try {
        setLoading(true);
        setError(null);
        await apiClient.assignDelivery(deliveryId, courierId);
        setDeliveries((prev) =>
          prev.map((d) =>
            String(d.id) === String(deliveryId)
              ? { ...d, courier: courierId }
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
    [handleError, setLoading, setError, setDeliveries]
  );

  return {
    uploadDeliveryRequests,
    addRequest,
    createRequestFromCoords,
    uploadRequestsFile,
    deleteRequest,
    assignDeliveryToCourier,
  };
}