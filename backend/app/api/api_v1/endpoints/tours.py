from typing import List, Optional
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import Item, ItemCreate, ItemUpdate, Message, Map

router = APIRouter(prefix="/tours")

@router.post("/compute/{courier_id}")
def compute_tour(courier_id: int):
    """calcule le meilleur itinéraire pour le courier donné"""

@router.get("/")
def list_tours():
    """renvoie la liste des tours déjà calculés"""

@router.get("/{courier_id}")
def get_tour(courier_id: int):
    """renvoie la liste des tours déjà calculés pour le courier donné"""