import { useRef } from "react";
import { DeliveryPoint } from "@/components/ui/delivery-map-types";
import { apiClient } from "@/lib/api";
import type { Map, Delivery } from "@/types/api";
import type { DisplayRoadSegment } from "./useMapAndDeliveries";

interface UseFileUploadsProps {
  map: Map | null;
  setMap: (map: Map | null) => void;
  setDeliveries: React.Dispatch<React.SetStateAction<Delivery[]>>;
  setCouriersState: React.Dispatch<React.SetStateAction<string[]>>;
  couriers: string[];
  setDeliveryPoints: React.Dispatch<React.SetStateAction<DeliveryPoint[]>>;
  setRoadSegments: (segments: DisplayRoadSegment[]) => void;
  setMapCenter: (center: [number, number]) => void;
  setMapZoom: (zoom: number) => void;
  setSuccessAlert: (alert: string | null) => void;
  createNewCourier: () => Promise<string | null>;
  uploadMap: (file: File) => Promise<Map>;
  onRequestsUploaded?: () => void;
}

export function useFileUploads({
  map,
  setMap,
  setDeliveries,
  setCouriersState,
  couriers,
  setDeliveryPoints,
  setRoadSegments,
  setMapCenter,
  setMapZoom,
  setSuccessAlert,
  createNewCourier,
  uploadMap,
  onRequestsUploaded,
}: UseFileUploadsProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const requestsInputRef = useRef<HTMLInputElement>(null);

  const handleMapUpload = () => {
    fileInputRef.current?.click();
  };

  const handleRequestUpload = () => {
    console.log("Triggering request upload");
    requestsInputRef.current?.click();
  };

  const handleFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      try {
        const mapData = await uploadMap(file);
        setMap(mapData);
        console.log("Map uploaded successfully:", mapData);
        console.log("New global map data:", mapData);

        // Update couriers state from map
        setCouriersState(mapData.couriers || []);

        // Only show existing delivery request points (no raw map nodes or couriers)
        const getCoords = (addr: string): [number, number] | null => {
          if (!addr) return null;
          const inter = mapData.intersections?.find(
            (i) => String(i.id) === String(addr)
          );
          if (inter) {
            const lat = Number(inter.latitude);
            const lng = Number(inter.longitude);
            if (!isNaN(lat) && !isNaN(lng)) {
              return [lat, lng];
            }
          }
          return null;
        };

        const points: DeliveryPoint[] = [];
        (mapData.deliveries || []).forEach((delivery) => {
          const p1 = getCoords(delivery.pickup_addr);
          if (p1) {
            points.push({
              id: `pickup-${delivery.id}`,
              position: p1,
              address: `Pickup Location ${delivery.id}`,
              type: "pickup",
              status: "pending",
            });
          }
          const p2 = getCoords(delivery.delivery_addr);
          if (p2) {
            points.push({
              id: `delivery-${delivery.id}`,
              position: p2,
              address: `Delivery Location ${delivery.id}`,
              type: "delivery",
              status: "pending",
            });
          }
          // Add courier marker at warehouse if present on the delivery
          const wh = delivery.warehouse;
          if (wh) {
            const pwh = getCoords(wh);
            if (pwh) {
              const courierId = `courier-${String(wh)}`;
              if (!points.some((p) => p.id === courierId)) {
                points.push({
                  id: courierId,
                  position: pwh,
                  address: `Courier start (warehouse) ${courierId}`,
                  type: "courier",
                  status: "active",
                });
              }
            }
          }
        });

        console.log("Generated delivery points:", points);
        setDeliveryPoints(points);
        // show success alert
        setSuccessAlert("Map loaded successfully");
        setTimeout(() => setSuccessAlert(null), 5000);

        // Convert road segments for rendering
        const segments = (mapData.road_segments || []).map((segment) => ({
          start: [Number(segment.start.latitude), Number(segment.start.longitude)] as [
            number,
            number
          ],
          end: [Number(segment.end.latitude), Number(segment.end.longitude)] as [
            number,
            number
          ],
          street_name: segment.street_name,
        }));
        setRoadSegments(segments);
        console.log("Generated road segments:", segments.length);

        // Set map center to the first intersection if available
        if (mapData.intersections && mapData.intersections.length > 0) {
          const firstIntersection = mapData.intersections[0];
          const lat = Number(firstIntersection.latitude);
          const lng = Number(firstIntersection.longitude);
          if (!isNaN(lat) && !isNaN(lng)) {
            setMapCenter([lat, lng]);
            console.log("Map center updated to:", [lat, lng]);
          }
        }

      } catch (error) {
        console.error("Failed to upload map:", error);
      }
    }
    // Reset the input value so the same file can be uploaded again
    try {
      input.value = "";
    } catch (e) {
      // ignore
    }
  };

  const handleRequestsFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];

    console.log("Selected requests file:", file);

    if (!file) return;
    try {
      // Ensure there is at least one courier for auto-assignment
      let defaultCourierId = couriers.length > 0 ? couriers[0] : null;
      if (!defaultCourierId) {
        defaultCourierId = await createNewCourier();
      }

      const deliveries = await apiClient.uploadRequestsFile(file);

      if (defaultCourierId) {
        await Promise.all(deliveries.map((d) => apiClient.assignDelivery(d.id, defaultCourierId).catch(() => undefined)));
        deliveries.forEach(d => d.courier = defaultCourierId);
      }

      setDeliveries((prev) => [...prev, ...deliveries]);

      // Reflect on map visually using current loaded intersections
      if (map && Array.isArray(deliveries)) {
        console.log("Processing deliveries to add to map:", deliveries);
        setDeliveryPoints((prev) => {
          const base = prev ? [...prev] : [];
          deliveries.forEach((d) => {
            const pickup = map.intersections.find(
              (i) => String(i.id) === String(d.pickup_addr)
            );
            const drop = map.intersections.find(
              (i) => String(i.id) === String(d.delivery_addr)
            );
            if (pickup) {
              const lat = Number(pickup.latitude);
              const lng = Number(pickup.longitude);
              if (!isNaN(lat) && !isNaN(lng)) {
                base.push({
                  id: `pickup-${d.id}`,
                  position: [lat, lng],
                  address: `Pickup Location ${d.id}`,
                  type: "pickup",
                  status: "pending",
                });
              }
            }
            if (drop) {
              const lat = Number(drop.latitude);
              const lng = Number(drop.longitude);
              if (!isNaN(lat) && !isNaN(lng)) {
                base.push({
                  id: `delivery-${d.id}`,
                  position: [lat, lng],
                  address: `Delivery Location ${d.id}`,
                  type: "delivery",
                  status: "pending",
                });
              }
            }
            // Add courier marker at warehouse (entrepot) if available
            const wh = d.warehouse;
            if (wh) {
              const pwh = map.intersections.find((i) => String(i.id) === String(wh));
              if (pwh) {
                const lat = Number(pwh.latitude);
                const lng = Number(pwh.longitude);
                if (!isNaN(lat) && !isNaN(lng)) {
                  const courierId = `courier-${String(wh)}`;
                  if (!base.some((p) => p.id === courierId)) {
                    base.push({
                      id: courierId,
                      position: [lat, lng],
                      address: `Courier start (warehouse)`,
                      type: "courier",
                      status: "active",
                    });
                  }
                }
              }
            }
          });
          if (base.length > 0) {
            const { latSum, lngSum } = base.reduce(
              (acc, point) => {
                acc.latSum += point.position[0];
                acc.lngSum += point.position[1];
                return acc;
              },
              { latSum: 0, lngSum: 0 }
            );
            const avgLat = latSum / base.length;
            const avgLng = lngSum / base.length;
            setMapCenter([avgLat, avgLng]);

            // Calculate zoom based on point spread
            const latitudes = base.map((p) => p.position[0]);
            const longitudes = base.map((p) => p.position[1]);
            const latRange = Math.max(...latitudes) - Math.min(...latitudes);
            const lngRange = Math.max(...longitudes) - Math.min(...longitudes);
            const maxRange = Math.max(latRange, lngRange);

            //FIND A BETTER SCALE
            let zoom = 14;
            if (maxRange < 0.01) zoom = 14;
            else if (maxRange < 0.05) zoom = 13;
            else if (maxRange < 0.1) zoom = 12;
            else if (maxRange < 0.2) zoom = 11;
            else zoom = 10;

            setMapZoom(zoom);
          }
          return base;
        });
        setSuccessAlert("Delivery requests imported successfully");
        setTimeout(() => setSuccessAlert(null), 5000);
        onRequestsUploaded?.();
      }
    } catch (err) {
      console.error("Failed to upload requests:", err);
    } finally {
      try {
        input.value = "";
      } catch (e) {
        // ignore
      }
    }
  };

  return {
    fileInputRef,
    requestsInputRef,
    handleMapUpload,
    handleRequestUpload,
    handleFileChange,
    handleRequestsFileChange,
  };
}