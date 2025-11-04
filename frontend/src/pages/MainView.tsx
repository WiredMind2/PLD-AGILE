import { useEffect, useState } from "react";
import { useDeliveryApp } from "@/hooks/useDeliveryApp";
import { useMapAndDeliveries } from "@/hooks/useMapAndDeliveries";
import { useFileUploads } from "@/hooks/useFileUploads";
import { useTourManagement } from "@/hooks/useTourManagement";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import Header from "@/components/Header";
import { Button } from "@/components/ui/button";
import StatsCards from "@/components/StatsCards";
import CourierManagementPanel from "@/components/CourierManagementPanel";
import DeliveriesPanel from "@/components/DeliveriesPanel";
import SavedToursPanel from "@/components/SavedToursPanel";
import MapPanel from "@/components/MapPanel";
import { DeliveryPoint } from "@/components/ui/delivery-map-types";
import { useUnreachableNodes } from "@/hooks/useUnreachableNodes";

export default function MainView(): JSX.Element {
  const [openNewReq, setOpenNewReq] = useState(false);
  const {
    loading,
    error,
    clearError,
    stats,
    map,
    setMap,
    deliveries,
    setDeliveries,
    fetchCouriers,
    deleteCourier,
    createNewCourier,
    couriers,
    setCouriersState,
    clearServerState,
    assignDeliveryToCourier,
    geocodeAddress,
    createRequestFromCoords,
    listSavedTours,
    saveNamedTour,
    loadNamedTour,
    deleteNamedTour,
    deleteRequest,
    uploadMap,
    computeTours,
  } = useDeliveryApp();

  const {
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
  } = useMapAndDeliveries();

  const [unreachableNodes, setUnreachableNodes] = useState<DeliveryPoint[]>([]);
  const [showUnreachableMarkers, setShowUnreachableMarkers] = useState<boolean>(false);

  const { loadUnreachableNodes } = useUnreachableNodes({
    map,
    setUnreachableNodes,
    setShowUnreachableMarkers,
    setSuccessAlert,
    setWarningAlert,
  });

  // Combine delivery points and unreachable nodes if showUnreachableMarkers is true
  const allDeliveryPoints = showUnreachableMarkers 
    ? [...deliveryPoints, ...unreachableNodes]
    : deliveryPoints;

  const {
    fileInputRef,
    requestsInputRef,
    handleMapUpload,
    handleRequestUpload,
    handleFileChange,
    handleRequestsFileChange,
  } = useFileUploads({
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
    onRequestsUploaded: () => setOpenNewReq(false),
  });

  const { handleOptimizeTours, rebuildFromState } = useTourManagement({
    map,
    couriers,
    setDeliveryPoints,
    setRoutes,
    setMapCenter,
    setOverworkAlert,
    setWarningAlert,
    computeTours,
  });

  const onCreateRequestFromCoords = async (
    pickup: [number, number],
    delivery: [number, number],
    options?: { pickup_service_s?: number; delivery_service_s?: number }
  ) => {
    if (!map) return;
    try {
      const res = await createRequestFromCoords?.(
        pickup,
        delivery,
        options
      );
      // Update markers immediately using returned nearest nodes
      if (res && res.pickupNode && res.deliveryNode) {
        const createdId = String(res.created.id);
        const pickupPos = [
          res.pickupNode.latitude,
          res.pickupNode.longitude,
        ] as [number, number];
        const deliveryPos = [
          res.deliveryNode.latitude,
          res.deliveryNode.longitude,
        ] as [number, number];
        addPickupDeliveryMarkers(
          createdId,
          pickupPos,
          deliveryPos
        );
        setSuccessAlert(
          "New delivery request created from map"
        );
        setTimeout(() => setSuccessAlert(null), 4000);
      }
    } catch (e) {
      // Error already handled in hook
    }
  };

  useEffect(() => {
    clearServerState();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-cyan-50 dark:from-gray-950 ">
      {/* Hidden file input for map upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".xml"
        style={{ display: "none" }}
        onChange={handleFileChange}
      />
      {/* Hidden file input for delivery requests upload */}
      <input
        ref={requestsInputRef}
        type="file"
        accept=".xml"
        style={{ display: "none" }}
        onChange={handleRequestsFileChange}
      />

      {/* Header */}
      <Header
        error={error}
        clearError={clearError}
        loading={loading}
        map={map}
        handleMapUpload={handleMapUpload}
        setOpenSaveSheet={setOpenSaveSheet}
        onOptimizeTours={handleOptimizeTours}
      />

      {/* Main Content */}
      <div className="container mx-auto p-6 space-y-6">
        {/* Quick Stats Cards */}
        <StatsCards couriers={couriers} stats={stats} />

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Map Section */}
          <MapPanel
            deliveryPoints={allDeliveryPoints}
            roadSegments={roadSegments}
            mapCenter={mapCenter}
            mapZoom={mapZoom}
            showSegmentLabels={showSegmentLabels}
            setShowSegmentLabels={setShowSegmentLabels}
            routes={routes}
            hiddenRoutes={hiddenRoutes}
            onPointClick={handlePointClick}
            onCreateRequestFromCoords={onCreateRequestFromCoords}
            showUnreachableMarkers={showUnreachableMarkers}
            onToggleUnreachableMarkers={() => {
              if (!showUnreachableMarkers && unreachableNodes.length === 0) {
                // first time: compute unreachable nodes then show if any
                loadUnreachableNodes();
              } else {
                setShowUnreachableMarkers(!showUnreachableMarkers);
              }
            }}
          />

          {/* Right Column */}
          <div className="space-y-6">
            {/* Couriers Management */}
            <CourierManagementPanel
              key={couriers.length}
              couriers={couriers}
              deliveries={deliveries}
              stats={stats}
              map={map}
              loading={loading}
              hiddenRoutes={hiddenRoutes}
              fetchCouriers={fetchCouriers}
              deleteCourier={deleteCourier}
              createNewCourier={createNewCourier}
              toggleRouteVisibility={toggleRouteVisibility}
              onCourierDelete={(courierId: string) => {
                setHiddenRoutes((h) => {
                  const copy = { ...h };
                  delete copy[String(courierId)];
                  return copy;
                });
              }}
            />
          </div>
        </div>

        {/* Deliveries Section */}
        <DeliveriesPanel
          stats={stats}
          deliveries={deliveries}
          couriers={couriers}
          map={map}
          loading={loading}
          assignDeliveryToCourier={assignDeliveryToCourier}
          deleteRequest={deleteRequest}
          setDeliveryPoints={setDeliveryPoints}
          onCreateRequestFromCoords={onCreateRequestFromCoords}
          geocodeAddress={geocodeAddress}
          setSuccessAlert={setSuccessAlert}
          onRequestUpload={handleRequestUpload}
          openNewReq={openNewReq}
          setOpenNewReq={setOpenNewReq}
        />

        {/* Saved Tours Section */}
        <SavedToursPanel
          savedTours={savedTours}
          setSavedTours={setSavedTours}
          openSaveSheet={openSaveSheet}
          setOpenSaveSheet={setOpenSaveSheet}
          saveName={saveName}
          setSaveName={setSaveName}
          listSavedTours={listSavedTours}
          saveNamedTour={saveNamedTour}
          loadNamedTour={loadNamedTour}
          deleteNamedTour={deleteNamedTour}
          map={map}
          onLoadTour={rebuildFromState}
          setSuccessAlert={setSuccessAlert}
          loading={loading}
        />
      </div>


      {successAlert && (
        <div className="fixed right-6 bottom-6 z-50 w-80">
          <Alert>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4 mr-2"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 13l4 4L19 7"
              />
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
          <Alert
            variant="destructive"
            className="border-red-600 bg-red-100 dark:bg-red-900/70"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4 mr-2 text-red-700"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v2m0 4h.01M21 12A9 9 0 113 12a9 9 0 0118 0z"
              />
            </svg>
            <div>
              <AlertTitle className="text-red-700 dark:text-red-200">
                Overwork alert
              </AlertTitle>
              <AlertDescription className="text-sm text-red-700 dark:text-red-200">
                {overworkAlert}
              </AlertDescription>
            </div>
          </Alert>
        </div>
      )}
      {warningAlert && (
        <div className="fixed right-6 bottom-24 z-50 w-96">
          <Alert
            variant="destructive"
            className="border-yellow-600 bg-red-100 dark:bg-yellow-700/70"
          >
            <div className="flex items-start justify-between w-full">
              <div className="flex items-start">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-4 w-4 mr-2 text-yellow-700"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v2m0 4h.01M21 12A9 9 0 113 12a9 9 0 0118 0z"
                  />
                </svg>
                <div>
                  <AlertTitle className="text-orange-700 dark:text-red-200">
                    Warning
                  </AlertTitle>
                  <AlertDescription className="text-sm text-red-700 dark:text-red-200">
                    {warningAlert}
                  </AlertDescription>
                </div>
              </div>
              <div className="ml-4">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setWarningAlert(null)}
                  className="text-sm text-white"
                >
                  Close
                </Button>
              </div>
            </div>
          </Alert>
        </div>
      )}
    </div>
  );
}
