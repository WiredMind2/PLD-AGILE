import { useCallback } from "react";
import { apiClient } from "@/lib/api";
import type { Map } from "@/types/api";

export function useMapOperations(
  handleError: (err: unknown) => void,
  setLoading: (loading: boolean) => void,
  setError: (error: string | null) => void,
  setMap: (map: Map | null) => void
) {
  const uploadMap = useCallback(async (file: File) => {
    try {
      setLoading(true);
      setError(null);
      console.log(`Uploading map file: ${file.name}`);
      const mapData = await apiClient.uploadMap(file);
      setMap(mapData);
      return mapData;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError, setLoading, setError, setMap]);

  return { uploadMap };
}