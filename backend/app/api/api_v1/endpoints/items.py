from typing import List, Optional
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import Item, ItemCreate, ItemUpdate, Message

router = APIRouter()

# Mock database - in real app, this would be a database
fake_items_db: List[Item] = [
    Item(id=1, name="Laptop", description="High-performance laptop", price=999.99, is_active=True),
    Item(id=2, name="Mouse", description="Wireless mouse", price=29.99, is_active=True),
]


@router.get("/", response_model=List[Item])
async def get_items(skip: int = 0, limit: int = 100):
    """Get all items with pagination"""
    return fake_items_db[skip : skip + limit]


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: int):
    """Get a specific item by ID"""
    for item in fake_items_db:
        if item.id == item_id:
            return item
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Item not found"
    )


@router.post("/", response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate):
    """Create a new item"""
    # Generate new ID
    new_id = max([item.id for item in fake_items_db], default=0) + 1
    
    new_item = Item(id=new_id, **item.dict())
    fake_items_db.append(new_item)
    return new_item


@router.put("/{item_id}", response_model=Item)
async def update_item(item_id: int, item_update: ItemUpdate):
    """Update an existing item"""
    for idx, item in enumerate(fake_items_db):
        if item.id == item_id:
            # Update only provided fields
            update_data = item_update.dict(exclude_unset=True)
            updated_item = item.copy(update=update_data)
            fake_items_db[idx] = updated_item
            return updated_item
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Item not found"
    )


@router.delete("/{item_id}", response_model=Message)
async def delete_item(item_id: int):
    """Delete an item"""
    for idx, item in enumerate(fake_items_db):
        if item.id == item_id:
            fake_items_db.pop(idx)
            return Message(message=f"Item {item_id} deleted successfully")
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Item not found"
    )