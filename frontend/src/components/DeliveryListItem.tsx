import { Button } from "@/components/ui/button";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Trash2 } from "lucide-react";
import { DeliveryPoint } from "@/components/ui/delivery-map-types";
import { Delivery } from "@/types/api";

interface DeliveryListItemProps {
  delivery: Delivery;
  couriers: string[];
  assignDeliveryToCourier: (deliveryId: string, courierId: string | null) => Promise<void>;
  deleteRequest: (id: string) => Promise<void>;
  setDeliveryPoints: React.Dispatch<React.SetStateAction<DeliveryPoint[]>>;
}

export default function DeliveryListItem({
  delivery,
  couriers,
  assignDeliveryToCourier,
  deleteRequest,
  setDeliveryPoints,
}: DeliveryListItemProps) {
  const pickupId = delivery.pickup_addr;
  const deliveryId = delivery.delivery_addr;

  return (
    <div className="flex items-center justify-between px-3 py-2">
      <div className="min-w-0">
        <div className="text-sm font-medium text-emerald-800 dark:text-emerald-200 truncate">
          Delivery {delivery.id}
        </div>
        <div className="text-xs text-emerald-600 dark:text-emerald-400 truncate">
          Pickup: {pickupId} • Drop: {deliveryId} • Service
          duration:{" "}
          {delivery.pickup_service_s + delivery.delivery_service_s}s
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Select
          value={(delivery?.courier ?? 'none') || 'none'}
          onValueChange={async (val: string) => {
            const v = val === "none" ? null : val;
            try {
              await assignDeliveryToCourier(delivery.id, v);
            } catch (err) {
              // handled globally
            }
          }}
        >
          <SelectTrigger size="sm">
            <SelectValue placeholder="Unassigned" />
          </SelectTrigger>
          <SelectContent className="max-h-64 overflow-auto">
            <SelectItem value={"none"} key="none">
              Unassigned
            </SelectItem>
            {(couriers || []).map((c: string) => (
              <SelectItem key={String(c)} value={String(c)}>{`Courier ${String(c)}`}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          size="sm"
          variant="outline"
          className="h-8 gap-1 border-emerald-200 text-emerald-700 dark:border-emerald-800 dark:text-emerald-300"
          onClick={async () => {
            try {
              if (delivery.id != null) await deleteRequest(delivery.id);
              // remove markers if present
              setDeliveryPoints((prev) =>
                prev?.filter(
                  (p) =>
                    p.id !== `pickup-${delivery.id}` &&
                    p.id !== `delivery-${delivery.id}`
                )
              );
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
}