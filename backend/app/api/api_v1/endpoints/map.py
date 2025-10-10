from fastapi import APIRouter, HTTPException, status, UploadFile

from app.models.schemas import Map

from app.services import XMLParser

router = APIRouter(prefix="/map")

@router.post("/", response_model=Map)
async def upload_map(file: UploadFile):
    """Load an XML file, parse it, save it and returns it"""
    try:
        data = await file.read()
        text = data.decode("utf-8")
        map = XMLParser.parse_map(map)
        return map
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))