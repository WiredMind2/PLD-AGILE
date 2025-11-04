import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Map } from "lucide-react";
import DeliveryMap from "@/components/ui/delivery-map";
import { DeliveryPoint } from "@/components/ui/delivery-map-types";
import type { DisplayRoadSegment } from "@/hooks/useMapAndDeliveries";

interface MapPanelProps {
  deliveryPoints: DeliveryPoint[];
  roadSegments: DisplayRoadSegment[];
  mapCenter: [number, number];
  mapZoom: number;
  showSegmentLabels: boolean;
  setShowSegmentLabels: (show: boolean) => void;
  routes: {
    id: string;
    courierId?: string;
    color?: string;
    positions: [number, number][];
  }[];
  hiddenRoutes: Record<string, boolean>;
  onPointClick: (point: DeliveryPoint) => void;
  onCreateRequestFromCoords: (
    pickup: [number, number],
    delivery: [number, number],
    options?: { pickup_service_s?: number; delivery_service_s?: number }
  ) => Promise<void>;
  showUnreachableMarkers?: boolean;
  onToggleUnreachableMarkers?: () => void;
  
}

export default function MapPanel({
  deliveryPoints,
  roadSegments,
  mapCenter,
  mapZoom,
  showSegmentLabels,
  setShowSegmentLabels,
  routes,
  hiddenRoutes,
  onPointClick,
  onCreateRequestFromCoords,
  showUnreachableMarkers,
  onToggleUnreachableMarkers,
}: MapPanelProps) {
  return (
    <Card className="lg:col-span-2 border-blue-200 dark:border-blue-800 shadow-lg">
      <CardHeader className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950 dark:to-purple-950 mb-6">
        <div className="w-full">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
              <Map className="h-5 w-5 text-blue-600" />
              City Map & Delivery Tours
            </CardTitle>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowSegmentLabels(!showSegmentLabels)}
              >
                {showSegmentLabels ? "Hide numbers" : "Show numbers"}
              </Button>
              <Button
                size="sm"
                variant={showUnreachableMarkers ? "default" : "outline"}
                onClick={onToggleUnreachableMarkers}
                title="Toggle unreachable nodes visibility"
              >
                {showUnreachableMarkers ? "Hide Unreachable" : "Show Unreachable"}
              </Button>
            </div>
          </div>
          <div className="mt-4">
            <CardDescription className="text-blue-600 dark:text-blue-400">
              Load XML city map and visualize optimized bicycle delivery routes
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {!roadSegments.length ? (
          <div className="h-[500px] rounded-lg bg-gradient-to-br from-blue-50/50 to-purple-50/50 dark:from-blue-950/30 dark:to-purple-950/30 border-2 border-dashed border-blue-200/50 dark:border-blue-800/50 flex items-center justify-center">
            <div className="text-center space-y-3">
              <Map className="h-10 w-10 text-blue-500 mx-auto" />
              <p className="text-sm text-blue-600 dark:text-blue-400">
                No map loaded
              </p>
              <p className="text-xs text-blue-500 dark:text-blue-500">
                Load an XML city map to visualize roads and compute tours
              </p>
            </div>
          </div>
        ) : (
          <DeliveryMap
            // filter out any points without valid numeric [lat, lng] positions
            points={deliveryPoints.filter(p => {
              return Array.isArray(p.position) && p.position.length === 2 && typeof p.position[0] === 'number' && typeof p.position[1] === 'number';
            })}
            roadSegments={roadSegments}
            center={mapCenter}
            zoom={mapZoom}
            height="500px"
            showRoadNetwork={false}
            showSegmentLabels={showSegmentLabels}
            // filter out routes that have been hidden by the user
            routes={routes.filter(
              (r) => !hiddenRoutes[String(r.courierId ?? r.id)]
            )}
            onPointClick={onPointClick}
            onCreateRequestFromCoords={onCreateRequestFromCoords}
          />
        )}
      </CardContent>
    </Card>
  );
}