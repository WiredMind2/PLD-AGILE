from typing import Optional
from pydantic import BaseModel


class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    is_active: bool = True


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    is_active: Optional[bool] = None


class Item(ItemBase):
    id: int
    
    class Config:
        from_attributes = True


class UserBase(BaseModel):
    email: str
    name: str
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: int
    
    class Config:
        from_attributes = True


# Response models
class Message(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None