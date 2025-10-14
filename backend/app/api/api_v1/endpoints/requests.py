from typing import List
from fastapi import APIRouter, HTTPException, status, UploadFile

from app.models.schemas import DeliveryRequest, Delivery
from app.core import state
from app.services import XMLParser

router = APIRouter(prefix="/requests")


@router.get("/", response_model=List[Delivery], tags=["Requests"], summary="List delivery requests", description="Return the list of active delivery requests stored in the server state.")
def list_requests():
    """Return the list of delivery requests."""
    return state.list_deliveries()


@router.post("/", response_model=Delivery, tags=["Requests"], summary="Create a delivery request (JSON)", description="Create a single delivery request by supplying pickup/delivery node ids and service durations in JSON.")
def add_request(request: DeliveryRequest):
    """Add a new delivery request."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail='No map loaded')
    # Validate that pickup and delivery node ids exist on the loaded map
    inter_ids = {str(i.id) for i in mp.intersections}
    if str(request.pickup_addr) not in inter_ids:
        raise HTTPException(status_code=400, detail=f'Pickup node id {request.pickup_addr} not found on map')
    if str(request.delivery_addr) not in inter_ids:
        raise HTTPException(status_code=400, detail=f'Delivery node id {request.delivery_addr} not found on map')

    # create delivery id via XMLParser helper (reuse existing parser to build a Delivery instance)
    try:
        deliveries = XMLParser.parse_deliveries(f'<root><livraison adresseEnlevement="{request.pickup_addr}" adresseLivraison="{request.delivery_addr}" dureeEnlevement="{request.pickup_service_s}" dureeLivraison="{request.delivery_service_s}"/></root>')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Failed to parse delivery: {e}')
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
        # validate that each delivery references existing nodes
        mp = state.get_map()
        inter_ids = {str(i.id) for i in mp.intersections} if mp else set()
        for d in deliveries:
            pid = getattr(d.pickup_addr, 'id', d.pickup_addr)
            did = getattr(d.delivery_addr, 'id', d.delivery_addr)
            if inter_ids and (str(pid) not in inter_ids or str(did) not in inter_ids):
                raise HTTPException(status_code=400, detail=f'Delivery references unknown node id (pickup={pid}, delivery={did})')
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
