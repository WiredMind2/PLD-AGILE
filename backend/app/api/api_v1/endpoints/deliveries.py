from typing import List
from fastapi import APIRouter, HTTPException, UploadFile

from app.models.schemas import Delivery
from app.core import state
from app.services import XMLParser

router = APIRouter(prefix="/deliveries")


@router.get("/", response_model=List[Delivery], tags=["Deliveries"], summary="List deliveries")
def list_deliveries():
    """Return the list of deliveries currently on the map."""
    return state.list_deliveries()


@router.post("/", response_model=List[Delivery], tags=["Deliveries"], summary="Upload deliveries (XML)")
async def upload_deliveries_file(file: UploadFile):
    """Upload an XML file containing deliveries. Parsed deliveries are added to server state."""
    try:
        data = await file.read()
        text = data.decode('utf-8')
        deliveries = XMLParser.parse_deliveries(text)

        if not deliveries:
            raise HTTPException(status_code=400, detail='No deliveries parsed from file')

        for d in deliveries:
            state.add_delivery(d)

        print(f"[deliveries.upload_deliveries_file] added {len(deliveries)} deliveries from {file.filename}")
        return deliveries
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
