from typing import List
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import DeliveryRequest, Delivery
from app.core import state
from app.services import XMLParser

router = APIRouter(prefix="/requests")


@router.get("/", response_model=List[Delivery])
def list_requests():
    """Return the list of delivery requests."""
    return state.list_deliveries()


@router.post("/", response_model=Delivery)
def add_request(request: DeliveryRequest):
    """Add a new delivery request."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail='No map loaded')

    # create delivery id via XMLParser helper
    deliveries = XMLParser.parse_deliveries(f'<root><livraison adresseEnlevement="{request.pickup_addr}" adresseLivraison="{request.delivery_addr}" dureeEnlevement="{request.pickup_service_s}" dureeLivraison="{request.delivery_service_s}"/></root>')
    if not deliveries:
        raise HTTPException(status_code=400, detail='Could not parse delivery')
    delivery = deliveries[0]
    mp.add_delivery(delivery)
    return delivery


@router.delete("/{delivery_id}")
def delete_request(delivery_id: str):
    ok = state.remove_delivery(delivery_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Delivery not found')
    return {"detail": "deleted"}
