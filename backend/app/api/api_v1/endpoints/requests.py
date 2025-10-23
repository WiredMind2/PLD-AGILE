from typing import List
from fastapi import APIRouter, HTTPException, status, UploadFile

from app.models.schemas import Delivery
from app.core import state
from app.services.XMLParser import XMLParser
from pydantic import BaseModel


class AssignCourierPayload(BaseModel):
    courier_id: str | None


router = APIRouter(prefix="/requests")


@router.get(
    "/",
    response_model=List[Delivery],
    tags=["Requests"],
    summary="List delivery requests",
    description="Return the list of active delivery requests stored in the server state.",
)
def list_requests():
    """Return the list of delivery requests."""
    return state.list_deliveries()


@router.post(
    "/",
    response_model=Delivery,
    tags=["Requests"],
    summary="Create a delivery (JSON)",
    description="Create a single delivery by supplying pickup/delivery node ids and service durations in JSON.",
)
def add_request(request: Delivery):
    """Add a new delivery request."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail="No map loaded")

    # Allow pickup_addr and delivery_addr to be either string ids or Intersection objects
    def as_id(value):
        try:
            return getattr(value, "id", value)
        except Exception:
            return value

    pickup_id = as_id(request.pickup_addr)
    delivery_id = as_id(request.delivery_addr)

    delivery = Delivery(
        id=XMLParser.generate_id(),  # Generate a unique ID for the delivery
        pickup_addr=pickup_id,
        delivery_addr=delivery_id,
        pickup_service_s=request.pickup_service_s,
        delivery_service_s=request.delivery_service_s,
    )

    # Use the central state helper so the global map state is updated in one place
    state.add_delivery(delivery)

    print(f"[requests.add_request] added delivery id={delivery.id}")

    return delivery


@router.delete(
    "/{delivery_id}",
    tags=["Requests"],
    summary="Delete delivery request",
    description="Delete a delivery request by its id.",
)
def delete_request(delivery_id: str):
    ok = state.remove_delivery(delivery_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return {"detail": "deleted"}


@router.post(
    "/upload",
    response_model=List[Delivery],
    tags=["Requests"],
    summary="Upload delivery requests (XML)",
    description="Upload an XML file containing <livraison> elements. Each parsed delivery is added to the server state.",
)
async def upload_requests_file(file: UploadFile):
    """Upload an XML file containing one or more <livraison> entries and add them to state."""
    try:
        data = await file.read()
        text = data.decode("utf-8")
        deliveries = XMLParser.parse_deliveries(text)
        if not deliveries:
            raise HTTPException(
                status_code=400, detail="No deliveries parsed from file"
            )
        for d in deliveries:
            state.add_delivery(d)
        try:
            print(
                f"[requests.upload_requests_file] added {len(deliveries)} deliveries from {file.filename}"
            )
        except Exception:
            pass
        return deliveries
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/{delivery_id}/assign",
    tags=["Requests"],
    summary="Assign courier to delivery",
    description="Assign or unassign a courier to a delivery request.",
)
def assign_courier(delivery_id: str, payload: AssignCourierPayload):
    """Assign a courier to an existing delivery. Use courier_id = null to unassign."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail="No map loaded")

    # If courier_id is provided, ensure courier exists
    courier_obj = None
    if payload.courier_id is not None:
        # resolve the courier id to the actual Courrier object stored in the map
        courier_obj = next(
            (c for c in mp.couriers if getattr(c, "id", None) == payload.courier_id),
            None,
        )
        if courier_obj is None:
            raise HTTPException(status_code=404, detail="Courier not found")

    # Store the courier object (or None) on the delivery so frontend sees a consistent object shape
    ok = state.update_delivery(delivery_id, courier=courier_obj)
    if not ok:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return {"detail": "assigned"}
