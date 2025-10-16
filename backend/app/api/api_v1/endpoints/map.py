from fastapi import APIRouter, HTTPException, status, UploadFile

from app.models.schemas import Map
from app.core.env import map

from app.services.XMLParser import XMLParser
from app.core import state

router = APIRouter(prefix="/map")


@router.post("/", response_model=Map, tags=["Map"], summary="Upload city map (XML)", description="Upload a city map XML (nodes and road segments). The server parses the file and stores the map in memory.")
async def upload_map(file: UploadFile):
    """Load an XML file, parse it, save it and return the parsed Map object."""
    global map
    try:
        data = await file.read()
        text = data.decode("utf-8")
        mp = XMLParser.parse_map(text)
        # build adjacency if the Map has the method
        try:
            mp.build_adjacency()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        finally:
            state.set_map(mp)
        return mp
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=Map, tags=["Map"], summary="Get loaded map", description="Return the currently loaded map. Returns 404 if no map has been uploaded yet.")
def get_map():
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No map loaded')
    return mp