import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Truck, Eye, EyeOff, Trash2 } from "lucide-react";
import type { Delivery, Map } from "@/types/api";

interface CourierManagementPanelProps {
  couriers: string[];
  deliveries: Delivery[];
  stats: { activeCouriers: number };
  map: Map | null;
  loading: boolean;
  hiddenRoutes: Record<string, boolean>;
  fetchCouriers: () => Promise<string[]>;
  deleteCourier: (courierId: string) => Promise<void>;
  createNewCourier: () => Promise<string | null>;
  toggleRouteVisibility: (courierId: string) => void;
  onCourierDelete: (courierId: string) => void;
}

export default function CourierManagementPanel({
  couriers,
  deliveries,
  stats,
  map,
  loading,
  hiddenRoutes,
  fetchCouriers,
  deleteCourier,
  createNewCourier,
  toggleRouteVisibility,
  onCourierDelete,
}: CourierManagementPanelProps) {

  return (
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
            <span className="text-sm font-medium">
              Number of Couriers:
            </span>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                className="h-8 w-8 p-0 border-purple-200 text-purple-600"
                disabled={!map || loading}
                onClick={async () => {
                  try {
                    // remove last courier if any
                    if (couriers && couriers.length > 0) {
                      const last = couriers[couriers.length - 1];
                      if (last) await deleteCourier(last);
                    }
                  } catch (e) {
                    // handled globally
                  }
                }}
              >
                -
              </Button>
              <span className="text-lg font-semibold w-8 text-center text-purple-700 dark:text-purple-300">
                {stats.activeCouriers}
              </span>
              <Button
                size="sm"
                variant="outline"
                className="h-8 w-8 p-0 border-purple-200 text-purple-600"
                disabled={!map || loading}
                onClick={async () => {
                  try {
                    await createNewCourier();
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
            <p className="text-sm font-medium text-purple-700 dark:text-purple-300">
              Couriers
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => fetchCouriers()}
              >
                Refresh
              </Button>
            </div>
          </div>
          <div className="text-xs text-purple-600 dark:text-purple-400">
            <div className="space-y-2 max-h-[22rem] overflow-auto rounded-md border border-purple-200 dark:border-purple-800 divide-y divide-purple-100 dark:divide-purple-900 p-2">
              {couriers && couriers.length > 0 ? (
                (() => {
                  // compute assigned counts per courier
                  const counts: Record<string, number> = {};
                  (deliveries || []).forEach((d) => {
                    const cid = d.courier;
                    if (cid) counts[cid] = (counts[cid] || 0) + 1;
                  });
                  return couriers.map((c) => (
                    <div
                      key={c}
                      className="flex items-center justify-between px-2 py-2"
                    >
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-purple-800 dark:text-purple-200 truncate">
                          Courier {c}
                        </div>
                        <div className="text-xs text-purple-600 dark:text-purple-400 truncate">
                          Requests: {counts[c] ?? 0}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {/* Toggle route visibility */}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => toggleRouteVisibility(c)}
                          title={
                            hiddenRoutes[c]
                              ? "Show route"
                              : "Hide route"
                          }
                        >
                          {hiddenRoutes[c] ? (
                            <EyeOff className="h-3.5 w-3.5" />
                          ) : (
                            <Eye className="h-3.5 w-3.5" />
                          )}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={async () => {
                            try {
                              await deleteCourier(c);
                              onCourierDelete(c);
                            } catch (e) {}
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  ));
                })()
              ) : (
                <div className="text-center text-xs text-purple-600">
                  No couriers registered
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}