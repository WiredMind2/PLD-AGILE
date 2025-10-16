from typing import List
from fastapi import APIRouter, HTTPException, status, UploadFile

from app.models.schemas import Delivery
from app.core import state
from app.services import XMLParser

router = APIRouter(prefix="/requests")


@router.get("/", response_model=List[Delivery], tags=["Requests"], summary="List delivery requests", description="Return the list of active delivery requests stored in the server state.")
def list_requests():
    """Return the list of delivery requests."""
    return state.list_deliveries()


@router.post("/", response_model=Delivery, tags=["Requests"], summary="Create a delivery (JSON)", description="Create a single delivery by supplying pickup/delivery node ids and service durations in JSON.")
def add_request(request: Delivery):
    """Add a new delivery request."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail='No map loaded')

    # Allow pickup_addr and delivery_addr to be either string ids or Intersection objects
    def as_id(value):
        try:
            return getattr(value, 'id', value)
        except Exception:
            return value

    pickup_id = as_id(request.pickup_addr)
    delivery_id = as_id(request.delivery_addr)

    # create delivery via XMLParser helper to ensure ID and normalization
    deliveries = XMLParser.parse_deliveries(
        f'<root><livraison adresseEnlevement="{pickup_id}" adresseLivraison="{delivery_id}" dureeEnlevement="{request.pickup_service_s}" dureeLivraison="{request.delivery_service_s}"/></root>'
    )
    if not deliveries:
        raise HTTPException(status_code=400, detail='Could not parse delivery')
    delivery = deliveries[0]
    # Use the central state helper so the global map state is updated in one place
    state.add_delivery(delivery)
    # debug aid: print added delivery id
    try:
        print(f"[requests.add_request] added delivery id={delivery.id}")
    except Exception:
        pass
    return delivery


@router.delete("/{delivery_id}", tags=["Requests"], summary="Delete delivery request", description="Delete a delivery request by its id.")
def delete_request(delivery_id: str):
    ok = state.remove_delivery(delivery_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Delivery not found')
    return {"detail": "deleted"}


@router.post('/upload', response_model=List[Delivery], tags=["Requests"], summary="Upload delivery requests (XML)", description="Upload an XML file containing <livraison> elements. Each parsed delivery is added to the server state.")
async def upload_requests_file(file: UploadFile):
    """Upload an XML file containing one or more <livraison> entries and add them to state."""
    try:
        data = await file.read()
        text = data.decode('utf-8')
        deliveries = XMLParser.parse_deliveries(text)
        if not deliveries:
            raise HTTPException(status_code=400, detail='No deliveries parsed from file')
        for d in deliveries:
            state.add_delivery(d)
        try:
            print(f"[requests.upload_requests_file] added {len(deliveries)} deliveries from {file.filename}")
        except Exception:
            pass
        return deliveries
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
