from fastapi import APIRouter, HTTPException, status, UploadFile, Query
from fastapi.responses import PlainTextResponse

from app.models.schemas import Map, Intersection

from app.services.XMLParser import XMLParser
from app.services.MapService import MapService
from app.core import state

router = APIRouter(prefix="/map")


@router.post("/", response_model=Map, tags=["Map"], summary="Upload city map (XML)")
async def upload_map(file: UploadFile):
    """Upload a city map XML (nodes and road segments). The server parses the file and stores the map in memory."""
    global map
    try:
        data = await file.read()
        text = data.decode("utf-8")
        mp = XMLParser.parse_map(text)

        # build adjacency if the Map has the method
        try:
            mp.build_adjacency()
            if len(mp.intersections) == 0 and len(mp.road_segments) == 0:
                raise ValueError("Parsed map is empty")
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        finally:
            state.set_map(mp)

        return mp

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=Map, tags=["Map"], summary="Get loaded map")
def get_map():
    """Return the currently loaded map. Returns 404 if no map has been uploaded yet."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No map loaded')

    return mp


@router.get("/ack_pair", tags=["Map"], summary="Nearest nodes for pickup and delivery")
def ack_pair(pickup_lat: float, pickup_lng: float, delivery_lat: float, delivery_lng: float):
    """Return the nearest intersections (from loaded map) for given pickup and given delivery coordinates."""
    p_node, d_node = MapService().ack_pair((pickup_lat, pickup_lng), (delivery_lat, delivery_lng))
    return {
        "pickup": p_node,
        "delivery": d_node,
    }


@router.get("/unreachable_nodes", tags=["Map"], summary="Compute unreachable nodes")
def get_unreachable_nodes(target_node_id: str | None = Query(None, description="Optional ID of the target node. If omitted, server will pick a node automatically.")):
    """Return a list of node IDs that cannot reach the specified target node.

    If `target_node_id` is omitted the server will pick a node automatically
    (heuristic + sampling) that maximizes how many nodes can reach it. This
    is useful when the vast majority of nodes are reachable from a good hub.
    """
    map_service = MapService()

    # If no target supplied, pick one automatically
    chosen_target = target_node_id
    if not chosen_target:
        chosen_target = map_service.find_best_target_node()
        if chosen_target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No map loaded or map has no intersections")

    unreachable_nodes = map_service.compute_unreachable_nodes(chosen_target)

    return {
        "target_node_id": chosen_target,
        "chosen_automatically": target_node_id is None,
        "unreachable_count": len(unreachable_nodes),
        "unreachable_nodes": unreachable_nodes,
    }

