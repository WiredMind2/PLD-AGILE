import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Plus,
  Package,
} from "lucide-react";
import { DeliveryPoint } from "@/components/ui/delivery-map-types";
import NewDeliverySheet from "./NewDeliverySheet";
import DeliveryListItem from "./DeliveryListItem";
import { Delivery, Intersection, Map } from "@/types/api";

interface DeliveriesPanelProps {
  stats: { deliveryRequests: number };
  deliveries: Delivery[];
  couriers: string[];
  map: Map | null;
  loading: boolean;
  assignDeliveryToCourier: (deliveryId: string, courierId: string | null) => Promise<void>;
  deleteRequest: (id: string) => Promise<void>;
  setDeliveryPoints: React.Dispatch<React.SetStateAction<DeliveryPoint[]>>;
  addPickupDeliveryMarkers?: (
    createdId: string,
    pickupPos: [number, number] | null,
    deliveryPos: [number, number] | null
  ) => void;
  geocodeAddress: (address: string) => Promise<{ lat: number; lon: number } | null>;
  createRequestFromCoords: (pickup: [number, number], delivery: [number, number], options?: { pickup_service_s?: number; delivery_service_s?: number }) => Promise<{ created: Delivery; pickupNode: Intersection; deliveryNode: Intersection }>;
  setSuccessAlert: (message: string | null) => void;
  onCreateRequestFromCoords: (
    pickup: [number, number],
    delivery: [number, number],
    options?: { pickup_service_s?: number; delivery_service_s?: number }
  ) => Promise<void>;
  onRequestUpload: () => void;
  openNewReq: boolean;
  setOpenNewReq: (open: boolean) => void;
}

export default function DeliveriesPanel({
  stats,
  deliveries,
  couriers,
  map,
  loading,
  assignDeliveryToCourier,
  deleteRequest,
  setDeliveryPoints,
  geocodeAddress,
  createRequestFromCoords,
  onCreateRequestFromCoords,
  addPickupDeliveryMarkers,
  setSuccessAlert,
  onRequestUpload,
  openNewReq,
  setOpenNewReq,
}: DeliveriesPanelProps) {

  return (
    <>
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
                title={
                  !map
                    ? "Load a map with road data first to add deliveries"
                    : loading
                    ? "Please wait, loading..."
                    : undefined
                }
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
                <p className="text-sm text-emerald-600 dark:text-emerald-400">
                  No deliveries
                </p>
                <p className="text-xs text-emerald-500 dark:text-emerald-500">
                  Add a delivery to start planning tours
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="text-xs text-emerald-700 dark:text-emerald-300">
                {stats.deliveryRequests} delivery(ies)
              </div>
              <div className="max-h-56 overflow-auto rounded-md border border-emerald-200 dark:border-emerald-800 divide-y divide-emerald-100 dark:divide-emerald-900">
                {(deliveries || []).map((d: Delivery, idx: number) => {
                  // Ensure a stable, unique key even when backend hasn't assigned an id yet
                  const itemKey = d.id ?? `pending-${idx}`;
                  return (
                    <DeliveryListItem
                      key={`${itemKey}-${d.courier || 'none'}`}
                      delivery={d}
                      couriers={couriers}
                      assignDeliveryToCourier={assignDeliveryToCourier}
                      deleteRequest={deleteRequest}
                      setDeliveryPoints={setDeliveryPoints}
                    />
                  );
                })}
              </div>
            </div>
          )}

        </CardContent>
      </Card>

      {/* New Delivery Request Sheet */}
      <NewDeliverySheet
        open={openNewReq}
        onOpenChange={setOpenNewReq}
        loading={loading}
        geocodeAddress={geocodeAddress}
        createRequestFromCoords={createRequestFromCoords}
        setDeliveryPoints={setDeliveryPoints}
        addPickupDeliveryMarkers={addPickupDeliveryMarkers}
        setSuccessAlert={setSuccessAlert}
        onRequestUpload={onRequestUpload}
        onCreateRequestFromCoords={onCreateRequestFromCoords}
      />
    </>
  );
}