from typing import List
from fastapi import APIRouter, HTTPException, status, UploadFile

from app.models.schemas import Delivery
from app.core import state
from app.services.XMLParser import XMLParser
from pydantic import BaseModel


class AssignCourierPayload(BaseModel):
    courier_id: str | None


router = APIRouter(prefix="/requests")


import contextlib
@router.get(
    "/",
    response_model=List[Delivery],
    tags=["Requests"],
    summary="List delivery requests",
)
def list_requests():
    """Return the list of active delivery requests stored in the server state."""
    return state.list_deliveries()


@router.post(
    "/",
    response_model=Delivery,
    tags=["Requests"],
    summary="Create a delivery (JSON)"
)
def add_request(request: Delivery):
    """Create a single delivery by supplying pickup/delivery node ids and service durations in JSON."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail='No map loaded')
    
    # Validate that pickup and delivery node ids exist on the loaded map
    inter_ids = {i.id for i in mp.intersections}
    if request.pickup_addr not in inter_ids:
        raise HTTPException(status_code=400, detail=f'Pickup node id {request.pickup_addr} not found on map')
    if request.delivery_addr not in inter_ids:
        raise HTTPException(status_code=400, detail=f'Delivery node id {request.delivery_addr} not found on map')

    # create delivery id via XMLParser helper (reuse existing parser to build a Delivery instance)
    try:
        delivery = Delivery(
            id=XMLParser.generate_id(),
            pickup_addr=request.pickup_addr,
            delivery_addr=request.delivery_addr,
            pickup_service_s=request.pickup_service_s,
            delivery_service_s=request.delivery_service_s
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Failed to parse delivery: {e}') from e
    if not delivery:
        raise HTTPException(status_code=400, detail='Could not parse delivery')
    
    # Use the central state helper so the global map state is updated in one place
    state.add_delivery(delivery)

    print(f"[requests.add_request] added delivery id={delivery.id}")

    return delivery


@router.delete(
    "/{delivery_id}",
    tags=["Requests"],
    summary="Delete delivery request"
)
def delete_request(delivery_id: str):
    """Delete a delivery request by its id."""
    if ok := state.remove_delivery(delivery_id):
        return {"detail": "deleted"}
    else:
        raise HTTPException(status_code=404, detail="Delivery not found")


@router.post(
    "/upload",
    response_model=List[Delivery],
    tags=["Requests"],
    summary="Upload delivery requests (XML)"
)
async def upload_requests_file(file: UploadFile):
    """Upload an XML file containing one or more <livraison> elements. Each parsed delivery is added to the server state."""
    try:
        data = await file.read()
        text = data.decode("utf-8")
        deliveries = XMLParser.parse_deliveries(text)
        if not deliveries:
            raise HTTPException(status_code=400, detail='No deliveries parsed from file')

        # validate that each delivery references existing nodes
        mp = state.get_map()
        inter_ids = {i.id for i in mp.intersections} if mp else set()

        for d in deliveries:
            if inter_ids and (d.pickup_addr not in inter_ids or  d.delivery_addr not in inter_ids):
                raise HTTPException(status_code=400, detail=f'Delivery references unknown node id (pickup={d.pickup_addr}, delivery={d.delivery_addr})')
            state.add_delivery(d)
        with contextlib.suppress(Exception):
            print(
                f"[requests.upload_requests_file] added {len(deliveries)} deliveries from {file.filename}"
            )
        return deliveries
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch(
    "/{delivery_id}/assign",
    tags=["Requests"],
    summary="Assign courier to delivery"
)
def assign_courier(delivery_id: str, payload: AssignCourierPayload):
    """Assign or unassign a courier to a delivery request."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail="No map loaded")

    if payload.courier_id and payload.courier_id not in state.list_couriers():
        raise HTTPException(status_code=404, detail="Courier not found")

    if state.update_delivery(delivery_id, courier=payload.courier_id):
        return {"detail": "assigned"}
    else:
        raise HTTPException(status_code=404, detail="Delivery not found")
