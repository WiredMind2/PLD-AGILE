import { useCallback } from "react";
import { apiClient } from "@/lib/api";
import type { Tour } from "@/types/api";

export function useTourOperations(
  handleError: (err: unknown) => void,
  setLoading: (loading: boolean) => void,
  setError: (error: string | null) => void,
  setToursState: React.Dispatch<React.SetStateAction<Tour[]>>
) {
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
  }, [handleError, setLoading, setError, setToursState]);

  return {
    computeTours,
  };
}