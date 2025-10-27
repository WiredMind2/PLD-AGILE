import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "./dropdown-menu";
import { Package, Building2, Clipboard, X } from "lucide-react";

interface DeliveryMapContextMenuProps {
  ctxMenu: {
    open: boolean;
    x: number;
    y: number;
    latlng?: [number, number];
  };
  setCtxMenu: React.Dispatch<
    React.SetStateAction<{
      open: boolean;
      x: number;
      y: number;
      latlng?: [number, number];
    }>
  >;
  pendingPickup: [number, number] | null;
  setPendingPickup: React.Dispatch<React.SetStateAction<[number, number] | null>>;
  pickupDurationSec: number;
  setPickupDurationSec: React.Dispatch<React.SetStateAction<number>>;
  deliveryDurationSec: number;
  setDeliveryDurationSec: React.Dispatch<React.SetStateAction<number>>;
  onCreateRequestFromCoords?: (
    pickup: [number, number],
    delivery: [number, number],
    options?: { pickup_service_s?: number; delivery_service_s?: number }
  ) => Promise<void> | void;
}

export default function DeliveryMapContextMenu({
  ctxMenu,
  setCtxMenu,
  pendingPickup,
  setPendingPickup,
  pickupDurationSec,
  setPickupDurationSec,
  deliveryDurationSec,
  setDeliveryDurationSec,
  onCreateRequestFromCoords,
}: DeliveryMapContextMenuProps) {
  return (
    <DropdownMenu
      open={ctxMenu.open}
      onOpenChange={(o) => setCtxMenu((s) => ({ ...s, open: o }))}
    >
      <DropdownMenuContent
        align="start"
        sideOffset={4}
        // Position absolutely at the cursor using a fixed portal
        style={{
          position: "fixed",
          left: ctxMenu.x,
          top: ctxMenu.y,
          zIndex: 1000,
        }}
        className="min-w-[14rem] p-2 rounded-md border shadow-md bg-white text-neutral-900 border-neutral-200 dark:bg-neutral-900 dark:text-neutral-100 dark:border-neutral-700"
        onCloseAutoFocus={(e) => e.preventDefault()}
      >
        <DropdownMenuLabel className="text-xs opacity-70">
          {pendingPickup
            ? `Pickup fixé: ${pendingPickup[0].toFixed(
                5
              )}, ${pendingPickup[1].toFixed(5)}`
            : ctxMenu.latlng
            ? `Lat: ${ctxMenu.latlng[0].toFixed(
                5
              )}  Lng: ${ctxMenu.latlng[1].toFixed(5)}`
            : "Position inconnue"}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {/* Step-specific duration editor (seconds) */}
        {pendingPickup === null ? (
          <div className="mb-2 text-sm">
            <label className="flex items-center justify-between gap-3">
              <span className="text-neutral-700 dark:text-neutral-200">
                Durée pickup (sec)
              </span>
              <input
                type="number"
                min={0}
                step={5}
                value={pickupDurationSec}
                onChange={(e) =>
                  setPickupDurationSec(Math.max(0, Number(e.target.value)))
                }
                onClick={(e) => e.stopPropagation()}
                onKeyDown={(e) => e.stopPropagation()}
                className="w-24 rounded border px-2 py-1 text-right bg-white text-neutral-900 border-neutral-300 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-neutral-800 dark:text-neutral-100 dark:border-neutral-600 dark:placeholder:text-neutral-500 dark:focus:ring-blue-400"
              />
            </label>
          </div>
        ) : (
          <div className="mb-2 text-sm">
            <label className="flex items-center justify-between gap-3">
              <span className="text-neutral-700 dark:text-neutral-200">
                Durée delivery (sec)
              </span>
              <input
                type="number"
                min={0}
                step={5}
                value={deliveryDurationSec}
                onChange={(e) =>
                  setDeliveryDurationSec(Math.max(0, Number(e.target.value)))
                }
                onClick={(e) => e.stopPropagation()}
                onKeyDown={(e) => e.stopPropagation()}
                className="w-24 rounded border px-2 py-1 text-right bg-white text-neutral-900 border-neutral-300 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-neutral-800 dark:text-neutral-100 dark:border-neutral-600 dark:placeholder:text-neutral-500 dark:focus:ring-blue-400"
              />
            </label>
          </div>
        )}

        <DropdownMenuSeparator />
        {pendingPickup === null ? (
          <DropdownMenuItem
            onClick={() => {
              if (ctxMenu.latlng) {
                setPendingPickup(ctxMenu.latlng);
              }
              setCtxMenu((s) => ({ ...s, open: false }));
            }}
          >
            <Package />
            Commencer une demande: fixer le pickup ici
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem
            onClick={async () => {
              if (ctxMenu.latlng && pendingPickup) {
                try {
                  await onCreateRequestFromCoords?.(
                    pendingPickup,
                    ctxMenu.latlng,
                    {
                      pickup_service_s: pickupDurationSec,
                      delivery_service_s: deliveryDurationSec,
                    }
                  );
                } catch (err) {
                  console.error("Create request from coords failed", err);
                } finally {
                  setPendingPickup(null);
                }
              }
              setCtxMenu((s) => ({ ...s, open: false }));
            }}
          >
            <Building2 />
            Terminer la demande: fixer la livraison ici
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={async () => {
            if (ctxMenu.latlng) {
              try {
                await navigator.clipboard.writeText(
                  `${ctxMenu.latlng[0]}, ${ctxMenu.latlng[1]}`
                );
              } catch (err) {
                console.error("Clipboard error", err);
              }
            }
            setCtxMenu((s) => ({ ...s, open: false }));
          }}
        >
          <Clipboard />
          Copier les coordonnées
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {pendingPickup !== null && (
          <DropdownMenuItem
            onClick={() => {
              setPendingPickup(null);
              setCtxMenu((s) => ({ ...s, open: false }));
            }}
          >
            <X />
            Annuler la demande en cours
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}