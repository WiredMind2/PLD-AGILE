import { DeliveryPoint } from "@/components/ui/delivery-map-types";
import { apiClient } from "@/lib/api";
import React from "react";

interface UseUnreachableNodesParams {
  map: any | null;
  setUnreachableNodes: React.Dispatch<React.SetStateAction<DeliveryPoint[]>>;
  setShowUnreachableMarkers: (v: boolean) => void;
  setSuccessAlert: (s: string | null) => void;
  setWarningAlert: (s: string | null) => void;
}

export function useUnreachableNodes({
  map,
  setUnreachableNodes,
  setShowUnreachableMarkers,
  setSuccessAlert,
  setWarningAlert,
}: UseUnreachableNodesParams) {
  const loadUnreachableNodes = async (targetNodeId?: string) => {
    if (!map) {
      setWarningAlert("Please load a map first before computing unreachable nodes.");
      setTimeout(() => setWarningAlert(null), 5000);
      return;
    }

    try {
      const data = await apiClient.getUnreachableNodes(targetNodeId);
      const unreachableNodeIds: string[] = data.unreachable_nodes || [];

      const nodes: DeliveryPoint[] = [];
      unreachableNodeIds.forEach((nodeId) => {
        const intersection = map?.intersections?.find((i: any) => String(i.id) === nodeId);
        if (intersection) {
          nodes.push({
            id: `unreachable-${nodeId}`,
            position: [intersection.latitude, intersection.longitude] as [number, number],
            address: `Unreachable Node: ${nodeId}`,
            type: "unreachable",
            status: "inactive",
          });
        }
      });

      setUnreachableNodes(nodes);
      if (nodes.length > 0) {
        setShowUnreachableMarkers(true);
        setSuccessAlert(`Found ${nodes.length} unreachable nodes for target ${data.target_node_id}`);
        setTimeout(() => setSuccessAlert(null), 3000);
      } else {
        setSuccessAlert(`No unreachable nodes found for target ${data.target_node_id}`);
        setTimeout(() => setSuccessAlert(null), 3000);
      }
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error("Failed to load unreachable nodes:", error);
      setWarningAlert("Failed to compute unreachable nodes. Make sure a map is loaded.");
      setTimeout(() => setWarningAlert(null), 5000);
    }
  };

  return { loadUnreachableNodes };
}
