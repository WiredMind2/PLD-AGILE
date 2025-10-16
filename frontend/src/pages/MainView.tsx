import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Map, Truck, Clock, Save, Plus, Route, Upload, Timer, Package, Activity, Trash2 } from 'lucide-react'
import { ThemeToggle } from '@/components/ui/theme-toggle'
import DeliveryMap, { DeliveryPoint } from '@/components/ui/delivery-map'
import { useState, useRef } from 'react'
import { useDeliveryApp } from '@/hooks/useDeliveryApp'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Input } from '@/components/ui/input'

export default function MainView(): JSX.Element {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const requestsInputRef = useRef<HTMLInputElement>(null);
  const [mapCenter, setMapCenter] = useState<[number, number]>([45.764043, 4.835659]); // Default Lyon center
  const [roadSegments, setRoadSegments] = useState<any[]>([]);
  
  const { 
    loading, 
    error, 
    uploadMap,
    clearError,
  addRequest,
  uploadRequestsFile,
    deleteRequest,
    stats,
  map,
  deliveries,
  computeTours,
  } = useDeliveryApp();

  const [deliveryPoints, setDeliveryPoints] = useState<DeliveryPoint[]>();
  const [computeNotice, setComputeNotice] = useState<string | null>(null);
  const [successAlert, setSuccessAlert] = useState<string | null>(null);
  const [routes, setRoutes] = useState<{ id: string; color?: string; positions: [number, number][] }[]>([]);
  const [showSegmentLabels, setShowSegmentLabels] = useState<boolean>(true);

  const handlePointClick = (point: any) => {
    console.log('Clicked delivery point:', point);
  };

  const handleMapUpload = () => {
    fileInputRef.current?.click();
  };

  const handleRequestUpload = () => {
    requestsInputRef.current?.click();
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
          if (wh && typeof wh.latitude === 'number' && typeof wh.longitude === 'number') {
            const courierId = `courier-${String(wh.id)}`;
            if (!points.some((p) => p.id === courierId)) {
              points.push({
                id: courierId,
                position: [wh.latitude, wh.longitude],
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
            const pickup = map.intersections.find((i) => String(i.id) === String(d.pickup_addr?.id ?? d.pickup_addr));
            const drop = map.intersections.find((i) => String(i.id) === String(d.delivery_addr?.id ?? d.delivery_addr));
            if (pickup) {
              base.push({ id: `pickup-${d.id}`, position: [pickup.latitude, pickup.longitude], address: 'Pickup Location', type: 'pickup', status: 'pending' });
            }
            if (drop) {
              base.push({ id: `delivery-${d.id}`, position: [drop.latitude, drop.longitude], address: 'Delivery Location', type: 'delivery', status: 'pending' });
            }
            // Add courier marker at warehouse (entrepot) if available
            const wh = d.warehouse;
            if (wh && typeof wh.latitude === 'number' && typeof wh.longitude === 'number') {
              const courierId = `courier-${String(wh.id)}`;
              if (!base.some((p) => p.id === courierId)) {
                base.push({
                  id: courierId,
                  position: [wh.latitude, wh.longitude],
                  address: 'Courier start (warehouse)',
                  type: 'courier',
                  status: 'active',
                });
              }
            }
          });
          return base;
        });
        setSuccessAlert('Delivery requests imported successfully');
        setTimeout(() => setSuccessAlert(null), 5000);
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
  const [pickupService, setPickupService] = useState(300); // default 5 min
  const [deliveryService, setDeliveryService] = useState(300); // default 5 min

  const submitNewRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await addRequest({
        pickup_addr: pickupAddr,
        delivery_addr: deliveryAddr,
        pickup_service_s: Number(pickupService),
        delivery_service_s: Number(deliveryService)
      } as any);
      // If we have a map, add points on the fly for visualization
      if (map) {
        const findInter = (id: string) => map.intersections.find((i) => String(i.id) === String(id));
        const pickupInter = findInter(pickupAddr);
        const deliveryInter = findInter(deliveryAddr);
        setDeliveryPoints((prev) => {
          const base = prev ? [...prev] : [];
          if (pickupInter) {
            base.push({
              id: `pickup-${created?.id ?? pickupAddr}`,
              position: [pickupInter.latitude, pickupInter.longitude],
              address: 'Pickup Location',
              type: 'pickup',
              status: 'pending'
            });
          }
          if (deliveryInter) {
            base.push({
              id: `delivery-${created?.id ?? deliveryAddr}`,
              position: [deliveryInter.latitude, deliveryInter.longitude],
              address: 'Delivery Location',
              type: 'delivery',
              status: 'pending'
            });
          }
          return base;
        });
      }
      // reset and close
      setPickupAddr('');
      setDeliveryAddr('');
      setPickupService(300);
      setDeliveryService(300);
      setOpenNewReq(false);
      setSuccessAlert('New delivery request created');
      setTimeout(() => setSuccessAlert(null), 5000);
    } catch (err) {
      // error is handled globally via hook
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
              disabled={loading}
            >
              <Upload className="h-4 w-4" />
              {loading ? 'Loading...' : 'Load Map (XML)'}
            </Button>
            <Button size="sm" variant="outline" className="gap-2 border-cyan-200 text-cyan-600  dark:border-cyan-800 dark:text-cyan-400">
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
                  setComputeNotice(null);
                  if (res && Array.isArray(res)) {
                    const points: DeliveryPoint[] = [];
                    // prefer courier starts first
                    res.forEach((t: any) => {
                      const courier = t.courier;
                      if (courier && courier.current_location) {
                        const cid = `courier-${courier.id}`;
                        points.push({ id: cid, position: [courier.current_location.latitude, courier.current_location.longitude], address: 'Courier start (warehouse)', type: 'courier', status: 'active' });
                      }
                      (t.deliveries || []).forEach((d: any) => {
                        const findInter = (addr: any) => {
                          if (!addr) return null;
                          if (typeof addr === 'string') return map?.intersections?.find((i: any) => String(i.id) === String(addr));
                          return addr;
                        };
                        const p1 = findInter(d.pickup_addr);
                        const p2 = findInter(d.delivery_addr);
                        if (p1) points.push({ id: `pickup-${d.id}`, position: [p1.latitude, p1.longitude], address: 'Pickup Location', type: 'pickup', status: 'pending' });
                        if (p2) points.push({ id: `delivery-${d.id}`, position: [p2.latitude, p2.longitude], address: 'Delivery Location', type: 'delivery', status: 'pending' });
                      });
                    });
                    if (points.length > 0) {
                      setDeliveryPoints(points);
                      // pan to first point if any
                      setMapCenter(points[0].position);
                    } else {
                      // do not clear existing points — show a notice so user knows nothing was computed
                      setComputeNotice('No tours were computed (no couriers or no assignable deliveries). Make sure the map includes couriers/warehouses and deliveries.');
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
                          return { id: t.courier?.id ?? `route-${idx}`, color: colors[idx % colors.length], positions };
                        }).filter((r: any) => r.positions && r.positions.length > 0);
                        setRoutes(builtRoutes);
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
              <div className="text-2xl font-bold">1</div>
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
              <DeliveryMap
                points={deliveryPoints}
                roadSegments={roadSegments}
                center={mapCenter}
                zoom={14}
                height="500px"
                showRoadNetwork={false}
                showSegmentLabels={showSegmentLabels}
                routes={routes}
                onPointClick={handlePointClick}
              />
            </CardContent>
          </Card>

          {/* Right Column */}
          <div className="space-y-6">
            {/* Couriers Management */}
            <Card className="border-purple-200 dark:border-purple-800 shadow-lg">
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
                      <Button size="sm" variant="outline" className="h-8 w-8 p-0 border-purple-200 text-purple-600">-</Button>
                      <span className="text-lg font-semibold w-8 text-center text-purple-700 dark:text-purple-300">1</span>
                      <Button size="sm" variant="outline" className="h-8 w-8 p-0 border-purple-200 text-purple-600">+</Button>
                    </div>
                  </div>
                  <div className="text-xs text-purple-500 dark:text-purple-400">
                    Speed: 15 km/h • Start: 08:00 from warehouse
                  </div>
                </div>
                <Separator className="bg-purple-200 dark:bg-purple-800" />
                <div className="space-y-2 bg-purple-50 dark:bg-purple-950/50 p-3 rounded-lg">
                  <p className="text-sm font-medium text-purple-700 dark:text-purple-300">Courier 1</p>
                  <div className="text-xs text-purple-600 dark:text-purple-400">
                    Status: <span className="text-emerald-600 font-medium">Available</span> • Requests: 0
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Timeline */}
            <Card className="border-cyan-200 dark:border-cyan-800 shadow-lg">
              <CardHeader className="bg-gradient-to-r from-cyan-50 to-blue-50 dark:from-cyan-950 dark:to-blue-950 mb-6">
                <CardTitle className="flex items-center gap-2 text-cyan-700 dark:text-cyan-300">
                  <Clock className="h-5 w-5 text-cyan-600" />
                  Tour Schedule
                </CardTitle>
                <CardDescription className="text-cyan-600 dark:text-cyan-400">
                  Pickup and delivery times for each courier
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-32 rounded-lg bg-gradient-to-br from-cyan-100/50 to-blue-100/50 dark:from-cyan-900/30 dark:to-blue-900/30 border-2 border-dashed border-cyan-300/50 dark:border-cyan-700/50 flex items-center justify-center">
                  <div className="text-center">
                    <Timer className="h-8 w-8 text-cyan-500 mx-auto mb-1 animate-pulse" />
                    <p className="text-sm text-cyan-600 dark:text-cyan-400">No active tours</p>
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
                  {(deliveries || []).map((d: any) => {
                    const pickupId = typeof d.pickup_addr === 'string' ? d.pickup_addr : d.pickup_addr?.id;
                    const deliveryId = typeof d.delivery_addr === 'string' ? d.delivery_addr : d.delivery_addr?.id;
                    return (
                      <div key={d.id} className="flex items-center justify-between px-3 py-2">
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-emerald-800 dark:text-emerald-200 truncate">Delivery {d.id}</div>
                          <div className="text-xs text-emerald-600 dark:text-emerald-400 truncate">
                            Pickup: {pickupId} • Drop: {deliveryId} • svc: {d.pickup_service_s + d.delivery_service_s}s
                          </div>
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-8 gap-1 border-emerald-200 text-emerald-700 dark:border-emerald-800 dark:text-emerald-300"
                          onClick={async () => {
                            try {
                              await deleteRequest(d.id);
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
              <SheetDescription>Provide node IDs and service durations in seconds.</SheetDescription>
            </SheetHeader>
            <form onSubmit={submitNewRequest} className="mt-6 space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Pickup node id</label>
                <Input
                  placeholder="e.g. 25175791"
                  value={pickupAddr}
                  onChange={(e) => setPickupAddr(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Delivery node id</label>
                <Input
                  placeholder="e.g. 25175792"
                  value={deliveryAddr}
                  onChange={(e) => setDeliveryAddr(e.target.value)}
                  required
                />
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

        {/* Tour Results Section */}
        <Card className="border-indigo-200 dark:border-indigo-800 shadow-lg">
          <CardHeader className="bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950 dark:to-purple-950 mb-6">
            <CardTitle className="flex items-center gap-2 text-indigo-700 dark:text-indigo-300">
              <Route className="h-5 w-5 text-indigo-600" />
              Optimized Tours
            </CardTitle>
            <CardDescription className="text-indigo-600 dark:text-indigo-400">
              Computed delivery tours with addresses, arrival and departure times
            </CardDescription>
          </CardHeader>
          <CardContent>
            {computeNotice ? (
              <div className="p-4 bg-yellow-50 rounded-md border border-yellow-200 text-yellow-800">{computeNotice}</div>
            ) : (
              <div className="h-32 rounded-lg bg-gradient-to-br from-indigo-100/50 to-purple-100/50 dark:from-indigo-900/30 dark:to-purple-900/30 border-2 border-dashed border-indigo-300/50 dark:border-indigo-700/50 flex items-center justify-center">
                <div className="text-center space-y-2">
                  <Route className="h-8 w-8 text-indigo-500 mx-auto" />
                  <p className="text-sm text-indigo-600 dark:text-indigo-400">No optimized tours</p>
                  <p className="text-xs text-indigo-500 dark:text-indigo-500">Add requests and optimize to see results</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
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
    </div>
  )
}