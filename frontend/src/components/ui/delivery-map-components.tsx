import { useEffect } from "react";
import { useMapEvents, useMap } from "react-leaflet";
import L from "leaflet";

// Minimal helper to listen to Leaflet right-clicks
export function MapRightClickHandler({
  onContextMenu,
}: {
  onContextMenu: (e: L.LeafletMouseEvent) => void;
}) {
  useMapEvents({
    contextmenu: (e) => {
      // Prevent the browser native context menu
      e.originalEvent?.preventDefault?.();
      onContextMenu(e);
    },
  });
  return null;
}

// Map updater components - must be outside to avoid recreation on each render
export const MapCenterUpdater = ({ target }: { target: [number, number] }) => {
  const map = useMap();
  useEffect(() => {
    if (Array.isArray(target) && target.length === 2 && !isNaN(target[0]) && !isNaN(target[1])) {
      console.log("MapCenterUpdater: panning to", target);
      map.panTo(target, { animate: false }); // Use panTo to only change center, not zoom
    }
  }, [map, target?.[0], target?.[1]]);
  return null;
};

export const MapZoomUpdater = ({ level }: { level: number }) => {
  const map = useMap();
  useEffect(() => {
    if (typeof level === "number" && !Number.isNaN(level) && level >= 0 && level <= 20) {
      console.log("MapZoomUpdater: setting zoom to", level);
      // Use setView with the current center to force Leaflet to apply the new zoom reliably
      const center = map.getCenter();
      if (center) {
        map.setView([center.lat, center.lng], level, { animate: false });
      }
    }
  }, [map, level]);
  return null;
};

// Component to handle map click events
export function MapClickHandler({
  onMapClick,
}: {
  onMapClick: () => void;
}) {
  useMapEvents({
    click: onMapClick,
  });
  return null;
}