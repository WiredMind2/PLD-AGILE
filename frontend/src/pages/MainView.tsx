import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Map, Truck, Clock, Save, Plus, Route, Upload, Timer, Package, Activity, Trash2, Eye, EyeOff, Download, RefreshCw } from 'lucide-react'
import { ThemeToggle } from '@/components/ui/theme-toggle'
import DeliveryMap, { DeliveryPoint } from '@/components/ui/delivery-map'
import { useState, useRef, useEffect } from 'react'
import { useDeliveryApp } from '@/hooks/useDeliveryApp'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Input } from '@/components/ui/input'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'

export default function MainView(): JSX.Element {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const requestsInputRef = useRef<HTMLInputElement>(null);
  const [mapCenter, setMapCenter] = useState<[number, number]>([45.764043, 4.835659]); // Default Lyon center
  const [roadSegments, setRoadSegments] = useState<any[]>([]);
  const [mapZoom, setMapZoom] = useState(13);

  const {
    loading,
    error,
    uploadMap,
    clearError,
    uploadRequestsFile,
    deleteRequest,
    stats,
    map,
    deliveries,
    computeTours,
    fetchCouriers,
    addCourier,
    deleteCourier,
    couriers,
    clearServerState,
    assignDeliveryToCourier,
    geocodeAddress,
    createRequestFromCoords,
    listSavedTours,
    saveNamedTour,
    loadNamedTour,
  } = useDeliveryApp();

  useEffect(() => {
    clearServerState();
    // Load saved tours list initially
    refreshSavedTours();
  }, []);

  // initialize as empty array so map components never receive `undefined`
  const [deliveryPoints, setDeliveryPoints] = useState<DeliveryPoint[]>([]);
  const [successAlert, setSuccessAlert] = useState<string | null>(null);
  const [overworkAlert, setOverworkAlert] = useState<string | null>(null);
  const [routes, setRoutes] = useState<{ id: string; courierId?: string; color?: string; positions: [number, number][] }[]>([]);
  const [showSegmentLabels, setShowSegmentLabels] = useState<boolean>(false);
  // per-courier route visibility (true = hidden)
  const [hiddenRoutes, setHiddenRoutes] = useState<Record<string, boolean>>({});
  // Saved tours state
  const [savedTours, setSavedTours] = useState<Array<{ name: string; saved_at?: string; size_bytes?: number }>>([]);
  const [openSaveSheet, setOpenSaveSheet] = useState(false);
  const [saveName, setSaveName] = useState('');

  const toggleRouteVisibility = (courierId: string) => {
    setHiddenRoutes((prev) => ({ ...prev, [String(courierId)]: !prev[String(courierId)] }));
  };

  const handlePointClick = (point: any) => {
    console.log('Clicked delivery point:', point);
  };

  // Helper to add pickup/delivery markers for a manually created delivery id
  const addPickupDeliveryMarkers = (
    createdId: string,
    pickupPos: [number, number] | null,
    deliveryPos: [number, number] | null,
  ) => {
    if (!pickupPos && !deliveryPos) return;
    setDeliveryPoints((prev) => {
      const base = prev ? [...prev] : [];
      if (pickupPos) {
        base.push({
          id: `pickup-${createdId}`,
          position: pickupPos,
          address: 'Pickup Location',
          type: 'pickup',
          status: 'pending',
        });
      }
      if (deliveryPos) {
        base.push({
          id: `delivery-${createdId}`,
          position: deliveryPos,
          address: 'Delivery Location',
          type: 'delivery',
          status: 'pending',
        });
      }
      return base;
    });
  };

  const handleMapUpload = () => {
    fileInputRef.current?.click();
  };

  const handleRequestUpload = () => {
    requestsInputRef.current?.click();
    setOpenNewReq(false);
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      try {
        const mapData = await uploadMap(file);
        console.log('Map uploaded successfully:', mapData);

        // Only show existing delivery request points (no raw map nodes or couriers)
        const getCoords = (addr: any): [number, number] | null => {
          if (!addr) return null;
          if (typeof addr === 'string') {
            const inter = mapData.intersections?.find((i: any) => String(i.id) === String(addr));
            return inter ? [inter.latitude, inter.longitude] : null;
          }
          if (typeof addr.latitude === 'number' && typeof addr.longitude === 'number') {
            return [addr.latitude, addr.longitude];
          }
          return null;
        };

        const points: DeliveryPoint[] = [];
        (mapData.deliveries || []).forEach((delivery: any) => {
          const p1 = getCoords(delivery.pickup_addr);
          if (p1) {
            points.push({
              id: `pickup-${delivery.id}`,
              position: p1,
              address: 'Pickup Location',
              type: 'pickup',
              status: 'pending',
            });
          }
          const p2 = getCoords(delivery.delivery_addr);
          if (p2) {
            points.push({
              id: `delivery-${delivery.id}`,
              position: p2,
              address: 'Delivery Location',
              type: 'delivery',
              status: 'pending',
            });
          }
          // Add courier marker at warehouse if present on the delivery
          const wh = delivery.warehouse;
          const pwh = getCoords(wh);
          if (pwh) {
            const courierId = `courier-${String(wh.id)}`;
            if (!points.some((p) => p.id === courierId)) {
              points.push({
                id: courierId,
                position: pwh,
                address: 'Courier start (warehouse)',
                type: 'courier',
                status: 'active',
              });
            }
          }
        });

        console.log('Generated delivery points:', points);
        setDeliveryPoints(points);
        // show success alert
        setSuccessAlert('Map loaded successfully');
        setTimeout(() => setSuccessAlert(null), 5000);

        // Convert road segments for rendering
        const segments = (mapData.road_segments || []).map(segment => ({
          start: [segment.start.latitude, segment.start.longitude] as [number, number],
          end: [segment.end.latitude, segment.end.longitude] as [number, number],
          street_name: segment.street_name
        }));
        setRoadSegments(segments);
        console.log('Generated road segments:', segments.length);

        // Set map center to the first intersection if available
        if (mapData.intersections && mapData.intersections.length > 0) {
          const firstIntersection = mapData.intersections[0];
          setMapCenter([firstIntersection.latitude, firstIntersection.longitude]);
          console.log('Map center updated to:', [firstIntersection.latitude, firstIntersection.longitude]);
        }

      } catch (error) {
        console.error('Failed to upload map:', error);
      }
    }
    // Reset the input value so the same file can be uploaded again
    try {
      input.value = '';
    } catch (e) {
      // ignore
    }
  };

  const refreshSavedTours = async () => {
    try {
      const lst = await listSavedTours?.();
      if (Array.isArray(lst)) setSavedTours(lst as any);
    } catch (e) { }
  };

  const handleRequestsFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    try {
      const deliveries = await uploadRequestsFile(file);

      // Reflect on map visually using current loaded intersections
      if (map && Array.isArray(deliveries)) {
        setDeliveryPoints((prev) => {
          const base = prev ? [...prev] : [];
          deliveries.forEach((d: any) => {
            const pickup = map.intersections.find((i) => String(i.id) === String(d.pickup_addr.id));
            const drop = map.intersections.find((i) => String(i.id) === String(d.delivery_addr.id));
            if (pickup) {
              base.push({ id: `pickup-${d.id}`, position: [pickup.latitude, pickup.longitude], address: 'Pickup Location', type: 'pickup', status: 'pending' });
            }
            if (drop) {
              base.push({ id: `delivery-${d.id}`, position: [drop.latitude, drop.longitude], address: 'Delivery Location', type: 'delivery', status: 'pending' });
            }
            // Add courier marker at warehouse (entrepot) if available
            const wh = d.warehouse;
            const pwh = map.intersections.find((i) => String(i.id) === String(wh.id));
            if (pwh) {
              const courierId = `courier-${String(wh.id)}`;
              if (!base.some((p) => p.id === courierId)) {
                base.push({
                  id: courierId,
                  position: [pwh.latitude, pwh.longitude],
                  address: 'Courier start (warehouse)',
                  type: 'courier',
                  status: 'active',
                });
              }
            }
          });
          if (base.length > 0) {
            const { latSum, lngSum } = base.reduce((acc, point) => {
              acc.latSum += point.position[0];
              acc.lngSum += point.position[1];
              return acc;
            }, { latSum: 0, lngSum: 0 });
            const avgLat = latSum / base.length;
            const avgLng = lngSum / base.length;
            setMapCenter([avgLat, avgLng]);

            // Calculate zoom based on point spread
            const latitudes = base.map(p => p.position[0]);
            const longitudes = base.map(p => p.position[1]);
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
        setSuccessAlert('Delivery requests imported successfully');
        setTimeout(() => setSuccessAlert(null), 5000);
        setOpenNewReq(false);
      }
    } catch (err) {
      console.error('Failed to upload requests:', err);
    } finally {
      try {
        input.value = '';
      } catch (e) {
        // ignore
      }
    }
  };

  // New Delivery Request Sheet state
  const [openNewReq, setOpenNewReq] = useState(false);
  const [pickupAddr, setPickupAddr] = useState('');
  const [deliveryAddr, setDeliveryAddr] = useState('');
  const [pickupAddressText, setPickupAddressText] = useState('');
  const [deliveryAddressText, setDeliveryAddressText] = useState('');
  const [pickupGeocodeLoading, setPickupGeocodeLoading] = useState(false);
  const [deliveryGeocodeLoading, setDeliveryGeocodeLoading] = useState(false);
  const [pickupService, setPickupService] = useState(300); // default 5 min
  const [deliveryService, setDeliveryService] = useState(300); // default 5 min


  const submitNewRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    let pickupCoord: [number, number] = [0, 0];
    let deliveryCoord: [number, number] = [0, 0];
    try {
      // Handle pickup address
      if (pickupAddressText) {
        setPickupGeocodeLoading(true);
        try {
          const geo = await geocodeAddress(pickupAddressText);
          if (!geo) {
            throw new Error('Pickup address not found: ' + pickupAddressText);
          }
          pickupCoord = [geo.lat, geo.lon];
        } catch (e) {
          console.error(e);
          throw e;
        } finally {
          setPickupGeocodeLoading(false);
        }
      }

      // Handle delivery address
      if (deliveryAddressText) {
        setDeliveryGeocodeLoading(true);
        try {
          const geo = await geocodeAddress(deliveryAddressText);
          if (!geo) {
            throw new Error('Delivery address not found: ' + deliveryAddressText);
          }
          deliveryCoord = [geo.lat, geo.lon];
        } catch (e) {
          console.error(e);
          throw e;
        } finally {
          setDeliveryGeocodeLoading(false);
        }
      }

      // Create the request using the API in the hook: options keys expected are pickup_service_s/delivery_service_s
      const res = await createRequestFromCoords(pickupCoord, deliveryCoord, { pickup_service_s: pickupService, delivery_service_s: deliveryService });
      // update map points
      if (res && res.pickupNode && res.deliveryNode) {
        const createdId = String((res.created as any)?.id ?? Date.now());
        const pickupPos = [res.pickupNode.latitude, res.pickupNode.longitude] as [number, number];
        const deliveryPos = [res.deliveryNode.latitude, res.deliveryNode.longitude] as [number, number];
        addPickupDeliveryMarkers(createdId, pickupPos, deliveryPos);
        setSuccessAlert('New delivery request created from form');
        setTimeout(() => setSuccessAlert(null), 4000);
      }

      // reset and close
      setPickupAddr('');
      setDeliveryAddr('');
      setPickupAddressText('');
      setDeliveryAddressText('');
      setPickupService(300);
      setDeliveryService(300);
      setOpenNewReq(false);
      setSuccessAlert('New delivery request created');
      setTimeout(() => setSuccessAlert(null), 5000);
    } catch (err) {
      setPickupGeocodeLoading(false);
      setDeliveryGeocodeLoading(false);
      // error is handled globally via hook
    } finally {
      setOpenNewReq(false);
    }
  };

  // Helper: Rebuild markers and routes from state (map + tours)
  const rebuildFromState = (currentMap: any, currentTours: any[]) => {
    try {
      // Build points from deliveries
      const points: DeliveryPoint[] = [];
      const getCoords = (addr: any): [number, number] | null => {
        if (!addr) return null;
        if (typeof addr === 'string') {
          const inter = currentMap?.intersections?.find((i: any) => String(i.id) === String(addr));
          return inter ? [inter.latitude, inter.longitude] : null;
        }
        if (typeof addr.latitude === 'number' && typeof addr.longitude === 'number') {
          return [addr.latitude, addr.longitude];
        }
        return null;
      };
      (currentMap?.deliveries || []).forEach((d: any) => {
        const p1 = getCoords(d.pickup_addr);
        const p2 = getCoords(d.delivery_addr);
        if (p1) points.push({ id: `pickup-${d.id}`, position: p1, address: 'Pickup Location', type: 'pickup', status: 'pending' });
        if (p2) points.push({ id: `delivery-${d.id}`, position: p2, address: 'Delivery Location', type: 'delivery', status: 'pending' });
        const wh = d.warehouse;
        const pwh = getCoords(wh);
        if (pwh) {
          const cid = `courier-${String(wh.id)}`;
          if (!points.some((p) => p.id === cid)) {
            points.push({ id: cid, position: pwh, address: 'Courier start (warehouse)', type: 'courier', status: 'active' });
          }
        }
      });
      setDeliveryPoints(points);

      // Build routes from tours
      const colors = ['#10b981', '#3b82f6', '#ef4444', '#f59e0b', '#8b5cf6'];
      const builtRoutes = (currentTours || []).map((t: any, idx: number) => {
        const ids: string[] = Array.isArray(t.route_intersections) ? t.route_intersections : [];
        const positions: [number, number][] = ids
          .map((nodeId: string) => {
            const inter = currentMap?.intersections?.find((i: any) => String(i.id) === String(nodeId));
            return inter ? ([inter.latitude, inter.longitude] as [number, number]) : null;
          })
          .filter(Boolean) as [number, number][];
        const courierId = String(t.courier?.id ?? 'route');
        return { id: `${courierId}-${idx}`, courierId, color: colors[idx % colors.length], positions };
      }).filter((r: any) => r.positions && r.positions.length > 0);
      setRoutes(builtRoutes);

      // Drop courier markers at route starts
      setDeliveryPoints((prev) => {
        const base = prev ? [...prev] : [];
        builtRoutes.forEach((r) => {
          if (!r.positions || r.positions.length === 0) return;
          const startPos = r.positions[0];
          const cid = `courier-${String(r.id)}`;
          const idx = base.findIndex((p) => p.id === cid);
          const pt: DeliveryPoint = { id: cid, position: startPos, address: 'Courier start (warehouse)', type: 'courier', status: 'active' };
          if (idx >= 0) base[idx] = { ...base[idx], position: startPos, status: 'active' } as any;
          else base.push(pt);
        });
        return base;
      });

      // Center map
      const firstPoint = (builtRoutes[0]?.positions?.[0]) || (currentMap?.intersections?.[0] ? [currentMap.intersections[0].latitude, currentMap.intersections[0].longitude] : null);
      if (firstPoint) setMapCenter(firstPoint as [number, number]);
    } catch (e) {
      // ignore rebuild failures
    }
  };
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-cyan-50 dark:from-gray-950 ">
      {/* Hidden file input for map upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".xml"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />
      {/* Hidden file input for delivery requests upload */}
      <input
        ref={requestsInputRef}
        type="file"
        accept=".xml"
        style={{ display: 'none' }}
        onChange={handleRequestsFileChange}
      />

      {/* Header */}
      <div className="sticky top-0 z-50 w-full border-b border-blue-200/50 dark:border-gray-800/50 bg-white/80 dark:bg-gray-950/80 backdrop-blur-lg supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-gray-950/60">
        {/* Error display */}
        {error && (
          <div className="bg-red-100 dark:bg-red-900/30 border-b border-red-200 dark:border-red-800 px-6 py-2">
            <div className="flex items-center justify-between">
              <p className="text-red-700 dark:text-red-300 text-sm">{error}</p>
              <Button
                variant="ghost"
                size="sm"
                onClick={clearError}
                className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200"
              >
                ×
              </Button>
            </div>
          </div>
        )}

        <div className="container flex h-16 items-center justify-between px-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-r from-blue-500 to-purple-600 shadow-lg">
                <Route className="h-4 w-4 text-white" />
              </div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Opti'tour</h1>
            </div>
            <Separator orientation="vertical" className="h-6" />
            <Badge variant="outline" className="text-xs border-purple-200 text-purple-600 dark:border-purple-800 dark:text-purple-400">
              <Activity className="mr-1 h-3 w-3" />
              Bicycle Delivery Optimizer
            </Badge>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Button
              size="sm"
              variant="outline"
              className="gap-2 border-blue-200 text-blue-600 dark:border-blue-800 dark:text-blue-400"
              onClick={handleMapUpload}
              disabled={loading || map !== null}
            >
              <Upload className="h-4 w-4" />
              {loading ? 'Loading...' : 'Load Map (XML)'}
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="gap-2 border-cyan-200 text-cyan-600  dark:border-cyan-800 dark:text-cyan-400"
              onClick={() => setOpenSaveSheet(true)}
              disabled={loading || !map}
              title={!map ? 'Load a map and compute tours first' : undefined}
            >
              <Save className="h-4 w-4" />
              Save Tours
            </Button>
            <Button
              size="sm"
              className="gap-2 bg-gradient-to-r from-purple-500 to-blue-600 hover:from-purple-600 hover:to-blue-700 text-white shadow-lg"
              disabled={!map || loading}
              onClick={async () => {
                console.log('Optimize Tours button clicked');
                try {
                  const res = await computeTours?.();
                  console.log('Compute tours response:', res);
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
                      const overworked = (res as any[]).filter((t) => {
                        const travel = Number(t?.total_travel_time_s ?? 0);
                        const service = Number(t?.total_service_time_s ?? 0);
                        return (travel + service) > 25200;
                      });
                      if (overworked && overworked.length > 0) {
                        const parts = overworked.map((t: any, idx: number) => {
                          const id = t?.courier?.id ?? t?.courier ?? `#${idx + 1}`;
                          const travel = Number(t?.total_travel_time_s ?? 0);
                          const service = Number(t?.total_service_time_s ?? 0);
                          const total = travel + service;
                          const totalFmt = formatSec(total);
                          const travelFmt = formatSec(travel);
                          const serviceFmt = formatSec(service);
                          return `Courier ${String(id)} scheduled ${totalFmt} (${travelFmt} travel + ${serviceFmt} service)`;
                        });
                        setOverworkAlert(`Overwork warning: ${parts.join('; ')}. Please remove or reassign some delivery requests.`);
                      } else {
                        setOverworkAlert(null);
                      }
                    }
                  } catch (e) {
                    // ignore formatting errors
                  }
                  // clear any previous notices (deprecated)
                  if (res && Array.isArray(res)) {
                    const points: DeliveryPoint[] = [];
                    const deliveryIdCounter = { count: 0 }; // Counter for generating unique delivery IDs

                    res.forEach((t: any) => {
                      const { courier } = t;
                      // Find courier start position from the deliveries' warehouse field
                      // Many map uploads register the warehouse on each delivery (map.deliveries[].warehouse)
                      // We search the loaded map deliveries for a matching warehouse id === courier.id
                      const getCourierStartFromWarehouse = (c: any) => {
                        if (!c) return null;
                        try {
                          if (map && Array.isArray(map.deliveries)) {
                            const match = map.deliveries.find((d: any) => {
                              const whId = d?.warehouse;
                              return whId && String(whId) === String(c.id);
                            });
                            if (match && match.warehouse) {
                              const pwh = map?.intersections?.find((i: any) => String(i.id) === String(match.warehouse));
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
                        const cid = `courier-${courier.id}`;
                        points.push({ id: cid, position: startPos, address: 'Courier start (warehouse)', type: 'courier', status: 'active' });
                      }

                      // t.deliveries is an array of tuples: [[pickup_id, delivery_id], ...]
                      (t.deliveries || []).forEach((tuple: [string, string]) => {
                        deliveryIdCounter.count++;
                        const deliveryId = `D${deliveryIdCounter.count}`;

                        // tuple[0] is pickup intersection ID, tuple[1] is delivery intersection ID
                        const pickupId = tuple[0];
                        const deliveryAddrId = tuple[1];

                        const pickupInter = map?.intersections?.find((i: any) => String(i.id) === String(pickupId));
                        const deliveryInter = map?.intersections?.find((i: any) => String(i.id) === String(deliveryAddrId));

                        if (pickupInter) {
                          points.push({
                            id: `pickup-${deliveryId}`,
                            position: [pickupInter.latitude, pickupInter.longitude],
                            address: 'Pickup Location',
                            type: 'pickup',
                            status: 'pending'
                          });
                        }
                        if (deliveryInter) {
                          points.push({
                            id: `delivery-${deliveryId}`,
                            position: [deliveryInter.latitude, deliveryInter.longitude],
                            address: 'Delivery Location',
                            type: 'delivery',
                            status: 'pending'
                          });
                        }
                      });
                    });
                    if (points.length > 0) {
                      setDeliveryPoints(points);
                      // pan to first point if any
                      setMapCenter(points[0].position);
                    } else {
                      // do not clear existing points — keep markers unchanged
                      console.warn('Compute returned empty tour list; leaving existing markers unchanged.');
                    }
                    // build route polylines from returned tours
                    try {
                      if (res && Array.isArray(res) && res.length > 0 && map) {
                        const colors = ['#10b981', '#3b82f6', '#ef4444', '#f59e0b', '#8b5cf6'];
                        const builtRoutes = res.map((t: any, idx: number) => {
                          const ids: string[] = Array.isArray(t.route_intersections) ? t.route_intersections : [];
                          const positions: [number, number][] = ids.map((nodeId: string) => {
                            const inter = map.intersections.find((i: any) => String(i.id) === String(nodeId));
                            return inter ? [inter.latitude, inter.longitude] as [number, number] : null;
                          }).filter(Boolean) as [number, number][];
                          const courierId = String(t.courier?.id ?? `route`);
                          return { id: `${courierId}-${idx}`, courierId, color: colors[idx % colors.length], positions };
                        }).filter((r: any) => r.positions && r.positions.length > 0);
                        setRoutes(builtRoutes);

                        // Ensure courier markers are placed at the start of each built route
                        // The first node in `positions` is the courier's start (and last is the end)
                        try {
                          setDeliveryPoints((prev) => {
                            const base = prev ? [...prev] : [];
                            builtRoutes.forEach((route) => {
                              if (!route.positions || route.positions.length === 0) return;
                              const startPos = route.positions[0];
                              const cid = `courier-${String(route.id)}`;
                              const existingIndex = base.findIndex((p) => p.id === cid);
                              const courierPoint: DeliveryPoint = {
                                id: cid,
                                position: startPos,
                                address: 'Courier start (warehouse)',
                                type: 'courier',
                                status: 'active',
                              };
                              if (existingIndex >= 0) {
                                // update existing marker position
                                base[existingIndex] = { ...base[existingIndex], position: startPos, status: 'active' };
                              } else {
                                base.push(courierPoint);
                              }
                            });
                            return base;
                          });
                        } catch (e) {
                          console.error('Failed to place courier markers on map:', e);
                        }
                      } else {
                        setRoutes([]);
                      }
                    } catch (e) {
                      console.error('Failed to build route polylines:', e);
                    }
                  }
                } catch (err) {
                  console.error('Failed to compute tours:', err);
                }
              }}
            >
              <Route className="h-4 w-4" />
              Optimize Tours
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto p-6 space-y-6">
        {/* Quick Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-gradient-to-br from-blue-500 to-blue-600 text-white border-0 shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-blue-100">Active Couriers</CardTitle>
              <Truck className="h-4 w-4 text-blue-200" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{couriers?.length ?? 0}</div>
              <p className="text-xs text-blue-200">Bicycle couriers</p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-500 to-purple-600 text-white border-0 shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-purple-100">Deliveries</CardTitle>
              <Package className="h-4 w-4 text-purple-200" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.deliveryRequests ?? 0}</div>
              <p className="text-xs text-purple-200">Active deliveries</p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-cyan-500 to-cyan-600 text-white border-0 shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-cyan-100">Travel Speed</CardTitle>
              <Timer className="h-4 w-4 text-cyan-200" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">15</div>
              <p className="text-xs text-cyan-200">km/h (constant)</p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-emerald-500 to-emerald-600 text-white border-0 shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-emerald-100">Start Time</CardTitle>
              <Clock className="h-4 w-4 text-emerald-200" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">08:00</div>
              <p className="text-xs text-emerald-200">Daily warehouse start</p>
            </CardContent>
          </Card>
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Map Section */}
          <Card className="lg:col-span-2 border-blue-200 dark:border-blue-800 shadow-lg">
            <CardHeader className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950 dark:to-purple-950 mb-6">
              <div className="w-full">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                    <Map className="h-5 w-5 text-blue-600" />
                    <span className="text-lg font-medium">City Map & Delivery Tours</span>
                  </div>
                  <div>
                    <Button size="sm" variant="outline" onClick={() => setShowSegmentLabels((s) => !s)}>
                      {showSegmentLabels ? 'Hide numbers' : 'Show numbers'}
                    </Button>
                  </div>
                </div>
                <div className="mt-1">
                  <CardDescription className="text-blue-600 dark:text-blue-400">
                    Load XML city map and visualize optimized bicycle delivery routes
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {!map ? (
                <div className="h-[500px] rounded-lg bg-gradient-to-br from-blue-50/50 to-purple-50/50 dark:from-blue-950/30 dark:to-purple-950/30 border-2 border-dashed border-blue-200/50 dark:border-blue-800/50 flex items-center justify-center">
                  <div className="text-center space-y-3">
                    <Map className="h-10 w-10 text-blue-500 mx-auto" />
                    <p className="text-sm text-blue-600 dark:text-blue-400">No map loaded</p>
                    <p className="text-xs text-blue-500 dark:text-blue-500">Load an XML city map to visualize roads and compute tours</p>
                  </div>
                </div>
              ) : (
                <DeliveryMap
                  // filter out any points without valid numeric [lat, lng] positions
                  points={deliveryPoints.filter(p => Array.isArray(p.position) && p.position.length === 2 && typeof p.position[0] === 'number' && typeof p.position[1] === 'number')}
                  roadSegments={roadSegments}
                  center={mapCenter}
                  zoom={mapZoom}
                  height="500px"
                  showRoadNetwork={false}
                  showSegmentLabels={showSegmentLabels}
                  // filter out routes that have been hidden by the user
                  routes={routes.filter((r) => !hiddenRoutes[String((r as any).courierId ?? r.id)])}
                  onPointClick={handlePointClick}
                  onCreateRequestFromCoords={async (pickup, delivery, options) => {
                    if (!map) return;
                    try {
                      const res = await createRequestFromCoords?.(pickup, delivery, options);
                      // Update markers immediately using returned nearest nodes
                      if (res && res.pickupNode && res.deliveryNode) {
                        const createdId = String((res.created as any)?.id ?? Date.now());
                        const pickupPos = [res.pickupNode.latitude, res.pickupNode.longitude] as [number, number];
                        const deliveryPos = [res.deliveryNode.latitude, res.deliveryNode.longitude] as [number, number];
                        addPickupDeliveryMarkers(createdId, pickupPos, deliveryPos);
                        setSuccessAlert('New delivery request created from map');
                        setTimeout(() => setSuccessAlert(null), 4000);
                      }
                    } catch (e) {
                      // Error already handled in hook
                    }
                  }}
                />
              )}
            </CardContent>
          </Card>

          {/* Right Column */}
          <div className="space-y-6">
            {/* Couriers Management */}
            <Card className="border-purple-200 dark:border-purple-800 shadow-lg h-[100%]">
              <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-950 dark:to-pink-950 mb-6">
                <CardTitle className="flex items-center gap-2 text-purple-700 dark:text-purple-300">
                  <Truck className="h-5 w-5 text-purple-600" />
                  Courier Management
                </CardTitle>
                <CardDescription className="text-purple-600 dark:text-purple-400">
                  Manage bicycle courier count and assignments
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Number of Couriers:</span>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-8 w-8 p-0 border-purple-200 text-purple-600"
                        disabled={!map || loading}
                          onClick={async () => {
                          try {
                            // remove last courier if any
                            if (stats.activeCouriers > 0) {
                              const cs = await fetchCouriers();
                              const last = cs && cs.length ? cs[cs.length - 1] : null;
                              if (last) await deleteCourier(String(last));
                            }
                          } catch (e) {
                            // handled globally
                          }
                        }}
                      >
                        -
                      </Button>
                      <span className="text-lg font-semibold w-8 text-center text-purple-700 dark:text-purple-300">{stats.activeCouriers}</span>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-8 w-8 p-0 border-purple-200 text-purple-600"
                        disabled={!map || loading}
                            onClick={async () => {
                          try {
                            // create a simple unique courier id and register it on the server
                            const id = `C${Date.now()}`;
                            await addCourier(id);
                          } catch (e) {
                            // handled globally
                          }
                        }}
                      >
                        +
                      </Button>
                    </div>
                  </div>
                  <div className="text-xs text-purple-500 dark:text-purple-400">
                    Speed: 15 km/h • Start: 08:00 from warehouse
                  </div>
                </div>
                <Separator className="bg-purple-200 dark:bg-purple-800" />
                <div className="space-y-2 bg-purple-50 dark:bg-purple-950/50 p-3 rounded-lg">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-purple-700 dark:text-purple-300">Couriers</p>
                    <div className="flex gap-2">
                      <Button size="sm" variant="ghost" onClick={() => fetchCouriers()}>Refresh</Button>
                    </div>
                  </div>
                  <div className="text-xs text-purple-600 dark:text-purple-400">
                    <div className="space-y-2 max-h-[22rem] overflow-auto rounded-md border border-purple-200 dark:border-purple-800 divide-y divide-purple-100 dark:divide-purple-900 p-2">
                      {(couriers && couriers.length > 0) ? (
                          (() => {
                          // compute assigned counts per courier (couriers are simple id strings)
                          const counts: Record<string, number> = {};
                          (deliveries || []).forEach((d: any) => {
                            const cid = typeof d?.courier === 'string' ? d.courier : null;
                            if (cid) counts[String(cid)] = (counts[String(cid)] || 0) + 1;
                          });
                          return couriers.map((c: any) => (
                            <div key={String(c)} className="flex items-center justify-between px-2 py-2">
                              <div className="min-w-0">
                                <div className="text-sm font-medium text-purple-800 dark:text-purple-200 truncate">{String(c)}</div>
                                <div className="text-xs text-purple-600 dark:text-purple-400 truncate">Requests: {counts[String(c)] ?? 0}</div>
                              </div>
                              <div className="flex items-center gap-2">
                                {/* Toggle route visibility */}
                                <Button size="sm" variant="outline" onClick={() => toggleRouteVisibility(String(c))} title={hiddenRoutes[String(c)] ? 'Show route' : 'Hide route'}>
                                  {hiddenRoutes[String(c)] ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                                </Button>
                                <Button size="sm" variant="outline" onClick={async () => { try { await deleteCourier(String(c)); setHiddenRoutes((h) => { const copy = { ...h }; delete copy[String(c)]; return copy; }); } catch (e) { } }}>
                                  <Trash2 className="h-3.5 w-3.5" />
                                </Button>
                              </div>
                            </div>
                          ));
                        })()
                      ) : (
                        <div className="text-center text-xs text-purple-600">No couriers registered</div>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Deliveries Section */}
        <Card className="border-emerald-200 dark:border-emerald-800 shadow-lg">
          <CardHeader className="bg-gradient-to-r from-emerald-50 to-green-50 dark:from-emerald-950 dark:to-green-950 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                  <Package className="h-5 w-5 text-emerald-600" />
                  Deliveries
                </CardTitle>
                <CardDescription className="text-emerald-600 dark:text-emerald-400">
                  Add new deliveries with pickup and delivery locations
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => setOpenNewReq(true)}
                  className="gap-2 bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 text-white shadow-lg"
                  disabled={!map || loading}
                  title={!map ? 'Load a map first to add deliveries' : loading ? 'Please wait, loading...' : undefined}
                >
                  <Plus className="h-4 w-4" />
                  New Delivery
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {(stats?.deliveryRequests ?? 0) === 0 ? (
              <div className="h-48 rounded-lg bg-gradient-to-br from-emerald-100/50 to-green-100/50 dark:from-emerald-900/30 dark:to-green-900/30 border-2 border-dashed border-emerald-300/50 dark:border-emerald-700/50 flex items-center justify-center">
                <div className="text-center space-y-2">
                  <Package className="h-8 w-8 text-emerald-500 mx-auto animate-bounce" />
                  <p className="text-sm text-emerald-600 dark:text-emerald-400">No deliveries</p>
                  <p className="text-xs text-emerald-500 dark:text-emerald-500">Add a delivery to start planning tours</p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="text-xs text-emerald-700 dark:text-emerald-300">{stats.deliveryRequests} delivery(ies)</div>
                <div className="max-h-56 overflow-auto rounded-md border border-emerald-200 dark:border-emerald-800 divide-y divide-emerald-100 dark:divide-emerald-900">
                  {(deliveries || []).map((d: any, idx: number) => {
                    const pickupId = typeof d.pickup_addr === 'string' ? d.pickup_addr : d.pickup_addr?.id;
                    const deliveryId = typeof d.delivery_addr === 'string' ? d.delivery_addr : d.delivery_addr?.id;
                    // Ensure a stable, unique key even when backend hasn't assigned an id yet
                    const itemKey = d.id ?? `pending-${idx}`;
                    return (
                      <div key={itemKey} className="flex items-center justify-between px-3 py-2">
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-emerald-800 dark:text-emerald-200 truncate">Delivery {d.id}</div>
                          <div className="text-xs text-emerald-600 dark:text-emerald-400 truncate">
                            Pickup: {pickupId} • Drop: {deliveryId} • Service duration: {d.pickup_service_s + d.delivery_service_s}s
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Select
                            value={(d?.courier ?? 'none') || 'none'}
                            onValueChange={async (val: string) => {
                              const v = val === 'none' ? null : val;
                              // guard: if delivery has no id yet, avoid calling backend
                              if (d.id == null) {
                                // update local state only
                                // note: assignDeliveryToCourier expects an id; skip API call
                                // but update deliveries array locally to reflect selection
                                setDeliveryPoints((prev) => prev);
                                return;
                              }
                              try {
                                await assignDeliveryToCourier(d.id, v);
                              } catch (err) {
                                // handled globally
                              }
                            }}
                          >
                            <SelectTrigger size="sm">
                              <SelectValue placeholder="Unassigned" />
                            </SelectTrigger>
                            <SelectContent className='max-h-64 overflow-auto'>
                              <SelectItem value={"none"} key="none">Unassigned</SelectItem>
                              {(couriers || []).map((c: any) => (
                                <SelectItem key={String(c)} value={String(c)}>{String(c)}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-8 gap-1 border-emerald-200 text-emerald-700 dark:border-emerald-800 dark:text-emerald-300"
                            onClick={async () => {
                              try {
                                if (d.id != null) await deleteRequest(d.id);
                                // remove markers if present
                                setDeliveryPoints((prev) => prev?.filter((p) => p.id !== `pickup-${d.id}` && p.id !== `delivery-${d.id}`));
                              } catch (e) {
                                // handled globally
                              }
                            }}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Delete
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

          </CardContent>
        </Card>

        {/* New Delivery Request Sheet */}
        <Sheet open={openNewReq} onOpenChange={setOpenNewReq}>
          <SheetContent side="right" className="sm:max-w-md">
            <SheetHeader>
              <SheetTitle>New Delivery Request</SheetTitle>
              <SheetDescription>Provide pickup and delivery addresses, and service durations.
                The nearest delivery points will be suggested based on the provided addresses.</SheetDescription>
            </SheetHeader>
            <form onSubmit={submitNewRequest} className="mt-6 space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Pickup address</label>
                <Input
                  placeholder="e.g. 10 rue de la République, 69001 Lyon"
                  value={pickupAddressText}
                  onChange={(e) => setPickupAddressText(e.target.value)}
                  disabled={!!pickupAddr}
                  required
                />
                {pickupGeocodeLoading && <span className="text-xs text-blue-500">Recherche de l'adresse...</span>}
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Delivery address</label>
                <Input
                  placeholder="e.g. 20 avenue Jean Jaurès, 69007 Lyon"
                  value={deliveryAddressText}
                  onChange={(e) => setDeliveryAddressText(e.target.value)}
                  disabled={!!deliveryAddr}
                  required
                />
                {deliveryGeocodeLoading && <span className="text-xs text-blue-500">Recherche de l'adresse...</span>}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Pickup service (s)</label>
                  <Input
                    type="number"
                    min={0}
                    value={pickupService}
                    onChange={(e) => setPickupService(parseInt(e.target.value || '0', 10))}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Delivery service (s)</label>
                  <Input
                    type="number"
                    min={0}
                    value={deliveryService}
                    onChange={(e) => setDeliveryService(parseInt(e.target.value || '0', 10))}
                    required
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Separator className="flex-1 bg-emerald-200 dark:bg-emerald-800" />
                <span className="text-xs text-emerald-600 dark:text-emerald-400 px-2">Or</span>
                <Separator className="flex-1 bg-emerald-200 dark:bg-emerald-800" />
              </div>
              {/* Import via XML */}
              <div>
                <Button
                  type="button"
                  variant="outline"
                  className="w-full gap-2 border-emerald-200 text-emerald-600 dark:border-emerald-800 dark:text-emerald-400"
                  onClick={handleRequestUpload}
                  disabled={loading}
                >
                  <Upload className="h-4 w-4" />
                  {loading ? 'Loading...' : 'Import from XML'}
                </Button>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setOpenNewReq(false)}>Cancel</Button>
                <Button type="submit" disabled={loading} className="bg-gradient-to-r from-emerald-500 to-green-600 text-white">
                  {loading ? 'Saving...' : 'Create request'}
                </Button>
              </div>
            </form>
          </SheetContent>
        </Sheet>

        {/* Saved Tours Section */}
        <Card className="border-indigo-200 dark:border-indigo-800 shadow-lg">
          <CardHeader className="bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950 dark:to-purple-950 mb-6">
            <CardTitle className="flex items-center gap-2 text-indigo-700 dark:text-indigo-300">
              <Route className="h-5 w-5 text-indigo-600" />
              Saved Tours
            </CardTitle>
            <CardDescription className="text-indigo-600 dark:text-indigo-400">
              Save and load full sessions (map, deliveries, couriers, and tours)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm text-indigo-700 dark:text-indigo-300">{savedTours.length} saved snapshot(s)</div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={refreshSavedTours}>
                  <RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh
                </Button>
              </div>
            </div>
            {savedTours.length === 0 ? (
              <div className="h-32 rounded-lg bg-gradient-to-br from-indigo-100/50 to-purple-100/50 dark:from-indigo-900/30 dark:to-purple-900/30 border-2 border-dashed border-indigo-300/50 dark:border-indigo-700/50 flex items-center justify-center">
                <div className="text-center space-y-2">
                  <Route className="h-8 w-8 text-indigo-500 mx-auto" />
                  <p className="text-sm text-indigo-600 dark:text-indigo-400">No saved tours yet</p>
                  <p className="text-xs text-indigo-500 dark:text-indigo-500">Click "Save Tours" to create a snapshot</p>
                </div>
              </div>
            ) : (
              <div className="space-y-2 max-h-56 overflow-auto rounded-md border border-indigo-200 dark:border-indigo-800 divide-y divide-indigo-100 dark:divide-indigo-900">
                {savedTours.map((s) => (
                  <div key={s.name} className="flex items-center justify-between px-3 py-2">
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-indigo-800 dark:text-indigo-200 truncate">{s.name}</div>
                      <div className="text-xs text-indigo-600 dark:text-indigo-400 truncate">{s.saved_at ? new Date(s.saved_at).toLocaleString() : ''}</div>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" className="gap-1" onClick={async () => {
                        try {
                          const st = await loadNamedTour?.(s.name);
                          if (st?.map) {
                            rebuildFromState(st.map, st.tours || []);
                            setSuccessAlert(`Loaded \"${s.name}\"`);
                            setTimeout(() => setSuccessAlert(null), 4000);
                          }
                        } catch (e) { }
                      }}>
                        <Download className="h-3.5 w-3.5" /> Load
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Save Tours Sheet */}
      <Sheet open={openSaveSheet} onOpenChange={setOpenSaveSheet}>
        <SheetContent side="right" className="sm:max-w-md">
          <SheetHeader>
            <SheetTitle>Save Current Tours</SheetTitle>
            <SheetDescription>Give your snapshot a name. It will include the map, deliveries, couriers, and tours.</SheetDescription>
          </SheetHeader>
          <div className="mt-6 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Save name</label>
              <Input placeholder="e.g. run-2025-10-23" value={saveName} onChange={(e) => setSaveName(e.target.value)} />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setOpenSaveSheet(false)}>Cancel</Button>
              <Button
                type="button"
                disabled={!saveName || loading || !map}
                onClick={async () => {
                  try {
                    await saveNamedTour?.(saveName);
                    setOpenSaveSheet(false);
                    setSaveName('');
                    await refreshSavedTours();
                    setSuccessAlert('Tours saved successfully');
                    setTimeout(() => setSuccessAlert(null), 3000);
                  } catch (e) { }
                }}
                className="bg-gradient-to-r from-cyan-500 to-blue-600 text-white"
              >
                <Save className="h-4 w-4 mr-1" /> Save
              </Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>
      {successAlert && (
        <div className="fixed right-6 bottom-6 z-50 w-80">
          <Alert>
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            <div>
              <AlertTitle>Success</AlertTitle>
              <AlertDescription>{successAlert}</AlertDescription>
            </div>
          </Alert>
        </div>
      )}
      {overworkAlert && (
        <div className="fixed right-6 bottom-24 z-50 w-96">
          <Alert variant="destructive" className="border-red-600 bg-red-100 dark:bg-red-900/70">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2 text-red-700" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12A9 9 0 113 12a9 9 0 0118 0z" />
            </svg>
            <div>
              <AlertTitle className="text-red-700 dark:text-red-200">Overwork alert</AlertTitle>
              <AlertDescription className="text-sm text-red-700 dark:text-red-200">{overworkAlert}</AlertDescription>
            </div>
          </Alert>
        </div>
      )}
    </div>
  )
}