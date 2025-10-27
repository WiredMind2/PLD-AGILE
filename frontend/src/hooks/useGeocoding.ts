import { useCallback } from "react";

export function useGeocoding(setError: (error: string | null) => void) {
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
          throw new Error(`${e.message}`);
        }
        throw new Error("Erreur inattendue lors du géocodage");
      }
    },
    []
  );

  return {
    geocodeAddress,
  };
}