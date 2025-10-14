from typing import List, Optional
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import Item, ItemCreate, ItemUpdate, Message, Map

router = APIRouter(prefix="/requests")

@router.get("/")
def list_requests():
    """Renvoie la liste des requetes de livraison"""

@router.post("/")
def add_request(request: DeliveryRequest):
    """ajoute une nouvelle requete de livraison"""
