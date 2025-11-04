import { useState } from "react";
import { DeliveryPoint } from "@/components/ui/delivery-map-types";
import type { SavedTourInfo } from "@/types/api";

export interface DisplayRoadSegment {
  start: [number, number];
  end: [number, number];
  street_name: string;
}

export interface Route {
  id: string;
  courierId?: string;
  color?: string;
  positions: [number, number][];
}

export function useMapAndDeliveries() {
  const [mapCenter, setMapCenter] = useState<[number, number]>([
    45.764043, 4.835659,
  ]); // Default Lyon center
  const [roadSegments, setRoadSegments] = useState<DisplayRoadSegment[]>([]);
  const [mapZoom, setMapZoom] = useState(13);
  const [deliveryPoints, setDeliveryPoints] = useState<DeliveryPoint[]>([]);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [showSegmentLabels, setShowSegmentLabels] = useState<boolean>(false);
  const [hiddenRoutes, setHiddenRoutes] = useState<Record<string, boolean>>({});
  const [savedTours, setSavedTours] = useState<SavedTourInfo[]>([]);
  const [openSaveSheet, setOpenSaveSheet] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [successAlert, setSuccessAlert] = useState<string | null>(null);
  const [overworkAlert, setOverworkAlert] = useState<string | null>(null);
  const [warningAlert, setWarningAlert] = useState<string | null>(null);

  const toggleRouteVisibility = (courierId: string) => {
    setHiddenRoutes((prev) => ({
      ...prev,
      [String(courierId)]: !prev[String(courierId)],
    }));
  };

  const handlePointClick = (point: DeliveryPoint) => {
    console.log("Clicked delivery point:", point);
  };

  const addPickupDeliveryMarkers = (
    createdId: string,
    pickupPos: [number, number] | null,
    deliveryPos: [number, number] | null
  ) => {
    if (!pickupPos && !deliveryPos) return;
    setDeliveryPoints((prev) => {
      const base = prev ? [...prev] : [];
      if (pickupPos) {
        base.push({
          id: `pickup-${createdId}`,
          position: pickupPos,
          address: "Pickup Location",
          type: "pickup",
          status: "pending",
        });
      }
      if (deliveryPos) {
        base.push({
          id: `delivery-${createdId}`,
          position: deliveryPos,
          address: "Delivery Location",
          type: "delivery",
          status: "pending",
        });
      }
      return base;
    });
  };

  return {
    mapCenter,
    setMapCenter,
    roadSegments,
    setRoadSegments,
    mapZoom,
    setMapZoom,
    deliveryPoints,
    setDeliveryPoints,
    routes,
    setRoutes,
    showSegmentLabels,
    setShowSegmentLabels,
    hiddenRoutes,
    setHiddenRoutes,
    savedTours,
    setSavedTours,
    openSaveSheet,
    setOpenSaveSheet,
    saveName,
    setSaveName,
    successAlert,
    setSuccessAlert,
    overworkAlert,
    setOverworkAlert,
    warningAlert,
    setWarningAlert,
    toggleRouteVisibility,
    handlePointClick,
    addPickupDeliveryMarkers,
  };
}