import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Save,
  Route,
  Trash2,
  Download,
  RefreshCw,
} from "lucide-react";
import { useEffect } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import type { SavedTourInfo, Map, Tour, Delivery } from "@/types/api";

interface SavedToursPanelProps {
  savedTours: SavedTourInfo[];
  setSavedTours: (tours: SavedTourInfo[]) => void;
  openSaveSheet: boolean;
  setOpenSaveSheet: (open: boolean) => void;
  saveName: string;
  setSaveName: (name: string) => void;
  listSavedTours?: () => Promise<SavedTourInfo[]>;
  saveNamedTour?: (name: string) => Promise<SavedTourInfo>;
  loadNamedTour?: (name: string) => Promise<{ map: Map | null; couriers: string[]; deliveries: Delivery[]; tours: Tour[] }>;
  deleteNamedTour?: (name: string) => Promise<{ detail: string }>;
  map: Map | null;
  onLoadTour: (map: Map | null, tours: Tour[]) => void;
  setSuccessAlert: (alert: string | null) => void;
  loading: boolean;
}

export default function SavedToursPanel({
  savedTours,
  setSavedTours,
  openSaveSheet,
  setOpenSaveSheet,
  saveName,
  setSaveName,
  listSavedTours,
  saveNamedTour,
  loadNamedTour,
  deleteNamedTour,
  map,
  onLoadTour,
  setSuccessAlert,
  loading,
}: SavedToursPanelProps) {
  const refreshSavedTours = async () => {
    try {
      const lst = await listSavedTours?.();
      if (Array.isArray(lst)) setSavedTours(lst);
    } catch (e) { }
  };

  useEffect(() => {
    refreshSavedTours();
  }, []);

  return (
    <>
      {/* Saved Tours Section */}
      <Card className="border-indigo-200 dark:border-indigo-800 shadow-lg">
        <CardHeader className="bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950 dark:to-purple-950 mb-6">
          <CardTitle className="flex items-center gap-2 text-indigo-700 dark:text-indigo-300">
            <Route className="h-5 w-5 text-indigo-600" />
            Saved Tours
          </CardTitle>
          <CardDescription className="text-indigo-600 dark:text-indigo-400">
            Save and load full sessions (map, deliveries, couriers, and tours)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm text-indigo-700 dark:text-indigo-300">
              {savedTours.length} saved snapshot(s)
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={refreshSavedTours}>
                <RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh
              </Button>
            </div>
          </div>
          {savedTours.length === 0 ? (
            <div className="h-32 rounded-lg bg-gradient-to-br from-indigo-100/50 to-purple-100/50 dark:from-indigo-900/30 dark:to-purple-900/30 border-2 border-dashed border-indigo-300/50 dark:border-indigo-700/50 flex items-center justify-center">
              <div className="text-center space-y-2">
                <Route className="h-8 w-8 text-indigo-500 mx-auto" />
                <p className="text-sm text-indigo-600 dark:text-indigo-400">
                  No saved tours yet
                </p>
                <p className="text-xs text-indigo-500 dark:text-indigo-500">
                  Click "Save Tours" to create a snapshot
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-2 max-h-56 overflow-auto rounded-md border border-indigo-200 dark:border-indigo-800 divide-y divide-indigo-100 dark:divide-indigo-900">
              {savedTours.map((s) => (
                <div
                  key={s.name}
                  className="flex items-center justify-between px-3 py-2"
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-indigo-800 dark:text-indigo-200 truncate">
                      {s.name}
                    </div>
                    <div className="text-xs text-indigo-600 dark:text-indigo-400 truncate">
                      {s.saved_at
                        ? new Date(s.saved_at).toLocaleString()
                        : ""}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="gap-1"
                      onClick={async () => {
                        try {
                          await deleteNamedTour?.(s.name);
                          await refreshSavedTours();
                          setSuccessAlert(`Deleted "${s.name}"`);
                          setTimeout(() => setSuccessAlert(null), 4000);
                        } catch (e) {}
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" /> Delete
                    </Button>
                    <Button
                      size="sm"
                      className="gap-1"
                      onClick={async () => {
                        try {
                          const st = await loadNamedTour?.(s.name);
                          if (st?.map) {
                            onLoadTour(st.map, st.tours || []);
                            setSuccessAlert(`Loaded "${s.name}"`);
                            setTimeout(() => setSuccessAlert(null), 4000);
                          }
                        } catch (e) {}
                      }}
                    >
                      <Download className="h-3.5 w-3.5" /> Load
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Save Tours Sheet */}
      <Sheet open={openSaveSheet} onOpenChange={setOpenSaveSheet}>
        <SheetContent side="right" className="sm:max-w-md">
          <SheetHeader>
            <SheetTitle>Save Current Tours</SheetTitle>
            <SheetDescription>
              Give your snapshot a name. It will include the map, deliveries,
              couriers, and tours.
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Save name</label>
              <Input
                placeholder="e.g. run-2025-10-23"
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setOpenSaveSheet(false)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                disabled={!saveName || loading || !map}
                onClick={async () => {
                  try {
                    await saveNamedTour?.(saveName);
                    setOpenSaveSheet(false);
                    setSaveName("");
                    await refreshSavedTours();
                    setSuccessAlert("Tours saved successfully");
                    setTimeout(() => setSuccessAlert(null), 3000);
                  } catch (e) { }
                }}
                className="bg-gradient-to-r from-cyan-500 to-blue-600 text-white"
              >
                <Save className="h-4 w-4 mr-1" /> Save
              </Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
