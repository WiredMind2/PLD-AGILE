import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Truck, Package, Timer, Clock } from "lucide-react";

interface StatsCardsProps {
  couriers: string[];
  stats: { deliveryRequests: number; };
}

export default function StatsCards({ couriers, stats }: StatsCardsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card className="bg-gradient-to-br from-blue-500 to-blue-600 text-white border-0 shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-blue-100">
            Active Couriers
          </CardTitle>
          <Truck className="h-4 w-4 text-blue-200" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{couriers?.length ?? 0}</div>
          <p className="text-xs text-blue-200">Bicycle couriers</p>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-purple-500 to-purple-600 text-white border-0 shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-purple-100">
            Deliveries
          </CardTitle>
          <Package className="h-4 w-4 text-purple-200" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {stats?.deliveryRequests ?? 0}
          </div>
          <p className="text-xs text-purple-200">Active deliveries</p>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-cyan-500 to-cyan-600 text-white border-0 shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-cyan-100">
            Travel Speed
          </CardTitle>
          <Timer className="h-4 w-4 text-cyan-200" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">15</div>
          <p className="text-xs text-cyan-200">km/h (constant)</p>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-emerald-500 to-emerald-600 text-white border-0 shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-emerald-100">
            Start Time
          </CardTitle>
          <Clock className="h-4 w-4 text-emerald-200" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">08:00</div>
          <p className="text-xs text-emerald-200">Daily warehouse start</p>
        </CardContent>
      </Card>
    </div>
  );
}