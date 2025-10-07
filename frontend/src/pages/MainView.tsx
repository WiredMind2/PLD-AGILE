import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Map, Truck, Clock, Save, Plus, Route, Upload, MapPin, Timer, Package, Activity } from 'lucide-react'
import { ThemeToggle } from '@/components/ui/theme-toggle'

export default function MainView(): JSX.Element {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-cyan-50 dark:from-gray-950 dark:via-blue-950 dark:to-purple-950">
      {/* Header */}
      <div className="sticky top-0 z-50 w-full border-b border-blue-200/50 dark:border-gray-800/50 bg-white/80 dark:bg-gray-950/80 backdrop-blur-lg supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-gray-950/60">
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
            <Button size="sm" variant="outline" className="gap-2 border-blue-200 text-blue-600 hover:bg-blue-50 dark:border-blue-800 dark:text-blue-400">
              <Upload className="h-4 w-4" />
              Load Map (XML)
            </Button>
            <Button size="sm" variant="outline" className="gap-2 border-cyan-200 text-cyan-600 hover:bg-cyan-50 dark:border-cyan-800 dark:text-cyan-400">
              <Save className="h-4 w-4" />
              Save Tours
            </Button>
            <Button size="sm" className="gap-2 bg-gradient-to-r from-purple-500 to-blue-600 hover:from-purple-600 hover:to-blue-700 text-white shadow-lg">
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
              <CardTitle className="text-sm font-medium text-purple-100">Delivery Requests</CardTitle>
              <Package className="h-4 w-4 text-purple-200" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">0</div>
              <p className="text-xs text-purple-200">Active requests</p>
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
              <CardTitle className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                <Map className="h-5 w-5 text-blue-600" />
                City Map & Delivery Tours
              </CardTitle>
              <CardDescription className="text-blue-600 dark:text-blue-400">
                Load XML city map and visualize optimized bicycle delivery routes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[60vh] w-full bg-gradient-to-br from-blue-100/50 via-purple-100/50 to-cyan-100/50 dark:from-blue-900/30 dark:via-purple-900/30 dark:to-cyan-900/30 rounded-lg border-2 border-dashed border-blue-300/50 dark:border-blue-700/50 flex items-center justify-center">
                <div className="text-center space-y-2">
                  <div className="relative">
                    <MapPin className="h-12 w-12 text-blue-500 mx-auto animate-pulse" />
                  </div>
                  <p className="text-lg font-medium text-blue-600 dark:text-blue-400">No Map Loaded</p>
                  <p className="text-sm text-blue-500 dark:text-blue-500">Load an XML file to display the city map</p>
                  <Button variant="outline" className="mt-2 border-blue-200 text-blue-600 hover:bg-blue-50 dark:border-blue-800 dark:text-blue-400">
                    <Upload className="mr-2 h-4 w-4" />
                    Load XML Map
                  </Button>
                </div>
              </div>
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
                      <Button size="sm" variant="outline" className="h-8 w-8 p-0 border-purple-200 text-purple-600 hover:bg-purple-50">-</Button>
                      <span className="text-lg font-semibold w-8 text-center text-purple-700 dark:text-purple-300">1</span>
                      <Button size="sm" variant="outline" className="h-8 w-8 p-0 border-purple-200 text-purple-600 hover:bg-purple-50">+</Button>
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

        {/* Delivery Requests Section */}
        <Card className="border-emerald-200 dark:border-emerald-800 shadow-lg">
          <CardHeader className="bg-gradient-to-r from-emerald-50 to-green-50 dark:from-emerald-950 dark:to-green-950 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                  <Package className="h-5 w-5 text-emerald-600" />
                  Delivery Requests
                </CardTitle>
                <CardDescription className="text-emerald-600 dark:text-emerald-400">
                  Add new delivery requests with pickup and delivery locations
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button size="sm" className="gap-2 bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 text-white shadow-lg">
                  <Plus className="h-4 w-4" />
                  New Delivery Request
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-48 rounded-lg bg-gradient-to-br from-emerald-100/50 to-green-100/50 dark:from-emerald-900/30 dark:to-green-900/30 border-2 border-dashed border-emerald-300/50 dark:border-emerald-700/50 flex items-center justify-center">
              <div className="text-center space-y-2">
                <Package className="h-8 w-8 text-emerald-500 mx-auto animate-bounce" />
                <p className="text-sm text-emerald-600 dark:text-emerald-400">No delivery requests</p>
                <p className="text-xs text-emerald-500 dark:text-emerald-500">Add a request to start planning tours</p>
              </div>
            </div>
          </CardContent>
        </Card>

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
            <div className="h-32 rounded-lg bg-gradient-to-br from-indigo-100/50 to-purple-100/50 dark:from-indigo-900/30 dark:to-purple-900/30 border-2 border-dashed border-indigo-300/50 dark:border-indigo-700/50 flex items-center justify-center">
              <div className="text-center space-y-2">
                <Route className="h-8 w-8 text-indigo-500 mx-auto" />
                <p className="text-sm text-indigo-600 dark:text-indigo-400">No optimized tours</p>
                <p className="text-xs text-indigo-500 dark:text-indigo-500">Add requests and optimize to see results</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
