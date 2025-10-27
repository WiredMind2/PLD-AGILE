import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Upload } from "lucide-react";
import { useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { DeliveryPoint } from "@/components/ui/delivery-map-types";
import { Delivery, Intersection } from "@/types/api";

interface NewDeliverySheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  loading: boolean;
  geocodeAddress: (address: string) => Promise<{ lat: number; lon: number } | null>;
  createRequestFromCoords: (pickup: [number, number], delivery: [number, number], options?: { pickup_service_s?: number; delivery_service_s?: number }) => Promise<{ created: Delivery; pickupNode: Intersection; deliveryNode: Intersection }>;
  setDeliveryPoints: React.Dispatch<React.SetStateAction<DeliveryPoint[]>>;
  setSuccessAlert: (message: string | null) => void;
  onRequestUpload: () => void;
}

export default function NewDeliverySheet({
  open,
  onOpenChange,
  loading,
  geocodeAddress,
  createRequestFromCoords,
  setDeliveryPoints,
  setSuccessAlert,
  onRequestUpload,
}: NewDeliverySheetProps) {
  const [pickupAddr, setPickupAddr] = useState("");
  const [deliveryAddr, setDeliveryAddr] = useState("");
  const [pickupAddressText, setPickupAddressText] = useState("");
  const [deliveryAddressText, setDeliveryAddressText] = useState("");
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
            throw new Error("Pickup address not found: " + pickupAddressText);
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
            throw new Error(
              "Delivery address not found: " + deliveryAddressText
            );
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
      const res = await createRequestFromCoords(pickupCoord, deliveryCoord, {
        pickup_service_s: pickupService,
        delivery_service_s: deliveryService,
      });
      // update map points
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
        // Add pickup/delivery markers for a manually created delivery id
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
        setSuccessAlert("New delivery request created from form");
        setTimeout(() => setSuccessAlert(null), 4000);
      }

      // reset and close
      setPickupAddr("");
      setDeliveryAddr("");
      setPickupAddressText("");
      setDeliveryAddressText("");
      setPickupService(300);
      setDeliveryService(300);
      onOpenChange(false);
      setSuccessAlert("New delivery request created");
      setTimeout(() => setSuccessAlert(null), 5000);
    } catch (err) {
      setPickupGeocodeLoading(false);
      setDeliveryGeocodeLoading(false);
      // error is handled globally via hook
    } finally {
      onOpenChange(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="sm:max-w-md">
        <SheetHeader>
          <SheetTitle>New Delivery Request</SheetTitle>
          <SheetDescription>
            Provide pickup and delivery addresses, and service durations.
            The nearest delivery points will be suggested based on the
            provided addresses.
          </SheetDescription>
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
            {pickupGeocodeLoading && (
              <span className="text-xs text-blue-500">
                Recherche de l'adresse...
              </span>
            )}
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
            {deliveryGeocodeLoading && (
              <span className="text-xs text-blue-500">
                Recherche de l'adresse...
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Pickup service (s)
              </label>
              <Input
                type="number"
                min={0}
                value={pickupService}
                onChange={(e) =>
                  setPickupService(parseInt(e.target.value || "0", 10))
                }
                required
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Delivery service (s)
              </label>
              <Input
                type="number"
                min={0}
                value={deliveryService}
                onChange={(e) =>
                  setDeliveryService(parseInt(e.target.value || "0", 10))
                }
                required
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Separator className="flex-1 bg-emerald-200 dark:bg-emerald-800" />
            <span className="text-xs text-emerald-600 dark:text-emerald-400 px-2">
              Or
            </span>
            <Separator className="flex-1 bg-emerald-200 dark:bg-emerald-800" />
          </div>
          {/* Import via XML */}
          <div>
            <Button
              type="button"
              variant="outline"
              className="w-full gap-2 border-emerald-200 text-emerald-600 dark:border-emerald-800 dark:text-emerald-400"
              onClick={onRequestUpload}
              disabled={loading}
            >
              <Upload className="h-4 w-4" />
              {loading ? "Loading..." : "Import from XML"}
            </Button>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={loading}
              className="bg-gradient-to-r from-emerald-500 to-green-600 text-white"
            >
              {loading ? "Saving..." : "Create request"}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}