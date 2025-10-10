from typing import List, Optional
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import Item, ItemCreate, ItemUpdate, Message, Map

router = APIRouter(prefix="/couriers")

@router.get("/")
def list_couriers():
    """renvoie la liste des couriers"""

@router.post("/")
def add_courier(courier: Courier):
    """crée un nouveau courier"""
