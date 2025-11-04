import { DeliveryPoint } from "@/components/ui/delivery-map-types";
import { Route } from "./useMapAndDeliveries";
import type { Map, Tour } from "@/types/api";

interface UseTourManagementProps {
  map: Map | null;
  couriers: string[];
  setDeliveryPoints: React.Dispatch<React.SetStateAction<DeliveryPoint[]>>;
  setRoutes: React.Dispatch<React.SetStateAction<Route[]>>;
  setMapCenter: (center: [number, number]) => void;
  setOverworkAlert: (alert: string | null) => void;
  setWarningAlert: (alert: string | null) => void;
  computeTours: (() => Promise<any>) | undefined;
}

export function useTourManagement({
  map,
  couriers,
  setDeliveryPoints,
  setRoutes,
  setMapCenter,
  setOverworkAlert,
  setWarningAlert,
  computeTours,
}: UseTourManagementProps) {

  // Helper: Rebuild markers and routes from state (map + tours)
  const rebuildFromState = (currentMap: Map | null, currentTours: Tour[]) => {
    if (!currentMap) return;
    try {
      // Build points from deliveries
      const points: DeliveryPoint[] = [];
      const getCoords = (addr: string): [number, number] | null => {
        if (!addr) return null;
        const inter = currentMap.intersections?.find(
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
      (currentMap?.deliveries || []).forEach((d) => {
        const p1 = getCoords(d.pickup_addr);
        const p2 = getCoords(d.delivery_addr);
        if (p1)
          points.push({
            id: `pickup-${d.id}`,
            position: p1,
            address: "Pickup Location",
            type: "pickup",
            status: "pending",
          });
        if (p2)
          points.push({
            id: `delivery-${d.id}`,
            position: p2,
            address: "Delivery Location",
            type: "delivery",
            status: "pending",
          });
        const wh = d.warehouse;
        if (wh) {
          const pwh = getCoords(wh);
          if (pwh) {
            const cid = `courier-${String(wh)}`;
            if (!points.some((p) => p.id === cid)) {
              points.push({
                id: cid,
                position: pwh,
                address: "Courier start (warehouse)",
                type: "courier",
                status: "active",
              });
            }
          }
        }
      });
      setDeliveryPoints(points);

      // Build routes from tours
      const colors = ["#10b981", "#3b82f6", "#ef4444", "#f59e0b", "#8b5cf6"];
      const builtRoutes = (currentTours || [])
        .map((t, idx: number) => {
          const ids: string[] = Array.isArray(t.route_intersections)
            ? t.route_intersections
            : [];
          const positions: [number, number][] = ids
            .map((nodeId: string) => {
              const inter = currentMap?.intersections?.find(
                (i) => String(i.id) === String(nodeId)
              );
              return inter
                ? ([inter.latitude, inter.longitude] as [number, number])
                : null;
            })
            .filter(Boolean) as [number, number][];
            const courierId = String(t.courier ?? "route");
          return {
            id: `${courierId}-${idx}`,
            courierId,
            color: colors[idx % colors.length],
            positions,
          };
        })
        .filter((r) => r.positions && r.positions.length > 0);
      setRoutes(builtRoutes);

      // Drop courier markers at route starts
      setDeliveryPoints((prev) => {
        const base = prev ? [...prev] : [];
        builtRoutes.forEach((r) => {
          if (!r.positions || r.positions.length === 0) return;
          const startPos = r.positions[0];
          const cid = `courier-${String(r.id)}`;
          const idx = base.findIndex((p) => p.id === cid);
          const pt: DeliveryPoint = {
            id: cid,
            position: startPos,
            address: "Courier start (warehouse)",
            type: "courier",
            status: "active",
          };
          if (idx >= 0)
            base[idx] = {
              ...base[idx],
              position: startPos,
              status: "active",
            };
          else base.push(pt);
        });
        return base;
      });

      // Center map
      const firstPoint =
        builtRoutes[0]?.positions?.[0] ||
        (currentMap?.intersections?.[0]
          ? [
              currentMap.intersections[0].latitude,
              currentMap.intersections[0].longitude,
            ]
          : null);
      if (firstPoint) setMapCenter(firstPoint as [number, number]);
    } catch (e) {
      // ignore rebuild failures
    }
  };

  const handleOptimizeTours = async () => {
    console.log("Optimize Tours button clicked");
    try {
      const res = await computeTours?.();
      console.log("Compute tours response:", res);
      // clear any previous overwork notice
      setOverworkAlert(null);
      const formatSec = (s: number) => {
        const h = Math.floor(s / 3600);
        const m = Math.round((s % 3600) / 60);
        return `${h}h ${m}m`;
      };
      // if API returns per-tour total_travel_time_s and total_service_time_s,
      // warn when their sum > 7 hours (25200s)
      try {
        if (res && Array.isArray(res)) {
          const overworked = res.filter((t) => {
            const travel = Number(t?.total_travel_time_s ?? 0);
            const service = Number(t?.total_service_time_s ?? 0);
            return travel + service > 25200;
          });
          if (overworked && overworked.length > 0) {
            const parts = overworked.map((t) => {
              const courierIndex = couriers.indexOf(t.courier);
              const displayName = courierIndex >= 0 ? `Courier ${courierIndex + 1}` : String(t.courier);
              const travel = Number(t?.total_travel_time_s ?? 0);
              const service = Number(t?.total_service_time_s ?? 0);
              const total = travel + service;
              const totalFmt = formatSec(total);
              const travelFmt = formatSec(travel);
              const serviceFmt = formatSec(service);
              return `${displayName} scheduled ${totalFmt} (${travelFmt} travel + ${serviceFmt} service)`;
            });
            setOverworkAlert(
              `Overwork warning: ${parts.join(
                "; "
              )}. Please remove or reassign some delivery requests.`
            );
          } else {
            setOverworkAlert(null);
          }
        }
      } catch (e) {
        // ignore formatting errors
      }

      // Checks if all pickup and delivery nodes are present in the response route
      // warns the user if some requests could not be mapped but does not crash the tour building process
      try {
        setWarningAlert(null);
        if (res && Array.isArray(res)) {
          res.forEach((t) => {
            t.deliveries?.forEach((pair: [string, string]) => {
              const pickupMissing = !t.route_intersections.includes(pair[0]);
              const deliveryMissing = !t.route_intersections.includes(pair[1]);
              if (pickupMissing || deliveryMissing) {
                setWarningAlert(`Some delivery requests could not be mapped for Courier ${t.courier}`);
              }
            });
          });
        }
      } catch (e) {
        // ignore errors
      }

      // clear any previous notices (deprecated)
      if (res && Array.isArray(res)) {
        const points: DeliveryPoint[] = [];
        const deliveryIdCounter = { count: 0 }; // Counter for generating unique delivery IDs

        res.forEach((t) => {
          const { courier } = t;
          // Find courier start position from the deliveries' warehouse field
          // Many map uploads register the warehouse on each delivery (map.deliveries[].warehouse)
          // We search the loaded map deliveries for a matching warehouse id === courier.id
          const getCourierStartFromWarehouse = (c: string) => {
            if (!c) return null;
            try {
              if (map && Array.isArray(map.deliveries)) {
                const match = map.deliveries.find((d) => {
                  const whId = d?.warehouse;
                  return whId && String(whId) === String(c);
                });
                if (match && match.warehouse) {
                  const pwh = map?.intersections?.find((i) => String(i.id) === String(match.warehouse));
                  if (pwh) {
                    return [pwh.latitude, pwh.longitude] as [number, number];
                  }
                }
              }
            } catch (e) {
              // ignore and fall through to null
            }
            return null;
          };

          const startPos = getCourierStartFromWarehouse(courier);
          if (startPos) {
            const cid = `courier-${courier}`;
            points.push({
              id: cid,
              position: startPos,
              address: "Courier start (warehouse)",
              type: "courier",
              status: "active",
            });
          }

          // t.deliveries is an array of tuples: [[pickup_id, delivery_id], ...]
          (t.deliveries || []).forEach(
            (tuple: [string, string]) => {
              deliveryIdCounter.count++;
              const deliveryId = `D${deliveryIdCounter.count}`;

              // tuple[0] is pickup intersection ID, tuple[1] is delivery intersection ID
              const pickupId = tuple[0];
              const deliveryAddrId = tuple[1];

              const pickupInter = map?.intersections?.find(
                (i) => String(i.id) === String(pickupId)
              );
              const deliveryInter = map?.intersections?.find(
                (i) => String(i.id) === String(deliveryAddrId)
              );

              if (pickupInter) {
                points.push({
                  id: `pickup-${deliveryId}`,
                  position: [
                    pickupInter.latitude,
                    pickupInter.longitude,
                  ],
                  address: "Pickup Location",
                  type: "pickup",
                  status: "pending",
                });
              }
              if (deliveryInter) {
                points.push({
                  id: `delivery-${deliveryId}`,
                  position: [
                    deliveryInter.latitude,
                    deliveryInter.longitude,
                  ],
                  address: "Delivery Location",
                  type: "delivery",
                  status: "pending",
                });
              }
            }
          );
        });
        if (points.length > 0) {
          setDeliveryPoints(points);
          // pan to first point if any
          setMapCenter(points[0].position);
        } else {
          // do not clear existing points — keep markers unchanged
          console.warn(
            "Compute returned empty tour list; leaving existing markers unchanged."
          );
        }
        // build route polylines from returned tours
        try {
          if (res && Array.isArray(res) && res.length > 0 && map) {
            const colors = [
              "#10b981",
              "#3b82f6",
              "#ef4444",
              "#f59e0b",
              "#8b5cf6",
          ];
            const builtRoutes = res
              .map((t, idx: number) => {
                const ids: string[] = Array.isArray(
                  t.route_intersections
                )
                  ? t.route_intersections
                  : [];
                const positions: [number, number][] = ids
                  .map((nodeId: string) => {
                    const inter = map.intersections.find(
                      (i) => String(i.id) === String(nodeId)
                    );
                    return inter
                      ? ([inter.latitude, inter.longitude] as [
                          number,
                          number
                        ])
                      : null;
                  })
                  .filter(Boolean) as [number, number][];
              const courierId = String(t.courier ?? `route`);
              return {
                  id: `${courierId}-${idx}`,
                  courierId,
                  color: colors[idx % colors.length],
                  positions,
                };
              })
              .filter(
                (r) => r.positions && r.positions.length > 0
              );
            setRoutes(builtRoutes);

            // Ensure courier markers are placed at the start of each built route
            // The first node in `positions` is the courier's start (and last is the end)
            try {
              setDeliveryPoints((prev) => {
                const base = prev ? [...prev] : [];
                builtRoutes.forEach((route) => {
                  if (
                    !route.positions ||
                    route.positions.length === 0
                  )
                    return;
                  const startPos = route.positions[0];
                  const cid = `courier-${String(route.id)}`;
                  const existingIndex = base.findIndex(
                    (p) => p.id === cid
                  );
                  const courierPoint: DeliveryPoint = {
                    id: cid,
                    position: startPos,
                    address: "Courier start (warehouse)",
                    type: "courier",
                    status: "active",
                  };
                  if (existingIndex >= 0) {
                    // update existing marker position
                    base[existingIndex] = {
                      ...base[existingIndex],
                      position: startPos,
                      status: "active",
                    };
                  } else {
                    base.push(courierPoint);
                  }
                });
                return base;
              });
            } catch (e) {
              console.error(
                "Failed to place courier markers on map:",
                e
              );
            }
          } else {
            setRoutes([]);
          }
        } catch (e) {
          console.error("Failed to build route polylines:", e);
        }
      }
    } catch (err) {
      console.error("Failed to compute tours:", err);
    }
  };

  return {
    handleOptimizeTours,
    rebuildFromState,
  };
}