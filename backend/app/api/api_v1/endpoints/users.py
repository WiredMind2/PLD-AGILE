from typing import List
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import User, UserCreate, UserUpdate, Message

router = APIRouter()

# Mock database - in real app, this would be a database
fake_users_db: List[User] = [
    User(id=1, email="admin@example.com", name="Admin User", is_active=True),
    User(id=2, email="user@example.com", name="Regular User", is_active=True),
]


@router.get("/", response_model=List[User])
async def get_users(skip: int = 0, limit: int = 100):
    """Get all users with pagination"""
    return fake_users_db[skip : skip + limit]


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: int):
    """Get a specific user by ID"""
    for user in fake_users_db:
        if user.id == user_id:
            return user
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """Create a new user"""
    # Check if email already exists
    for existing_user in fake_users_db:
        if existing_user.email == user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Generate new ID
    new_id = max([user.id for user in fake_users_db], default=0) + 1
    
    # Create user (excluding password from response)
    user_data = user.dict()
    user_data.pop("password")  # Don't store password in plain text
    new_user = User(id=new_id, **user_data)
    fake_users_db.append(new_user)
    return new_user


@router.put("/{user_id}", response_model=User)
async def update_user(user_id: int, user_update: UserUpdate):
    """Update an existing user"""
    for idx, user in enumerate(fake_users_db):
        if user.id == user_id:
            # Update only provided fields
            update_data = user_update.dict(exclude_unset=True)
            updated_user = user.copy(update=update_data)
            fake_users_db[idx] = updated_user
            return updated_user
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


@router.delete("/{user_id}", response_model=Message)
async def delete_user(user_id: int):
    """Delete a user"""
    for idx, user in enumerate(fake_users_db):
        if user.id == user_id:
            fake_users_db.pop(idx)
            return Message(message=f"User {user_id} deleted successfully")
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )