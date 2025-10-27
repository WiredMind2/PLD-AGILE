import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Route,
  Upload,
  Save,
  Activity,
} from "lucide-react";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import type { Map } from "@/types/api";

interface HeaderProps {
  error: string | null;
  clearError: () => void;
  loading: boolean;
  map: Map | null;
  handleMapUpload: () => void;
  setOpenSaveSheet: (open: boolean) => void;
  onOptimizeTours: () => void;
}

export default function Header({
  error,
  clearError,
  loading,
  map,
  handleMapUpload,
  setOpenSaveSheet,
  onOptimizeTours,
}: HeaderProps) {
  return (
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
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Opti'tour
            </h1>
          </div>
          <Separator orientation="vertical" className="h-6" />
          <Badge
            variant="outline"
            className="text-xs border-purple-200 text-purple-600 dark:border-purple-800 dark:text-purple-400"
          >
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
            disabled={loading || map !== null}
          >
            <Upload className="h-4 w-4" />
            {loading ? "Loading..." : "Load Map (XML)"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="gap-2 border-cyan-200 text-cyan-600  dark:border-cyan-800 dark:text-cyan-400"
            onClick={() => setOpenSaveSheet(true)}
            disabled={loading || !map}
            title={!map ? "Load a map and compute tours first" : undefined}
          >
            <Save className="h-4 w-4" />
            Save Tours
          </Button>
          <Button
            size="sm"
            className="gap-2 bg-gradient-to-r from-purple-500 to-blue-600 hover:from-purple-600 hover:to-blue-700 text-white shadow-lg"
            disabled={!map || loading}
            onClick={onOptimizeTours}
          >
            <Route className="h-4 w-4" />
            Optimize Tours
          </Button>
        </div>
      </div>
    </div>
  );
}
