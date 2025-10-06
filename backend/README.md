# PLD-AGILE Backend

A modular FastAPI backend built for easy extensibility and scalability.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip or pipenv

### Installation (PowerShell on Windows)

1. **Navigate to backend directory:**
   ```powershell
   cd backend
   ```

2. **Create virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```powershell
   Copy-Item .env.example .env
   ```

5. **Run the server:**
   ```powershell
   python main.py
   ```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc

## 📁 Project Structure

```
backend/
├── main.py                    # FastAPI app entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py         # App configuration and settings
│   ├── api/
│   │   ├── __init__.py
│   │   └── api_v1/
│   │       ├── __init__.py
│   │       ├── api.py        # API router aggregation
│   │       └── endpoints/    # Individual endpoint modules
│   │           ├── __init__.py
│   │           ├── items.py  # Items CRUD endpoints
│   │           └── users.py  # Users CRUD endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py        # Pydantic models
│   └── services/
│       └── __init__.py       # Business logic layer
```

## 🔧 Available Endpoints

### Core
- `GET /` - Welcome message
- `GET /health` - Health check

### Items API (`/api/v1/items`)
- `GET /` - List all items (with pagination)
- `GET /{item_id}` - Get specific item
- `POST /` - Create new item
- `PUT /{item_id}` - Update item
- `DELETE /{item_id}` - Delete item

### Users API (`/api/v1/users`)
- `GET /` - List all users (with pagination)
- `GET /{user_id}` - Get specific user
- `POST /` - Create new user
- `PUT /{user_id}` - Update user
- `DELETE /{user_id}` - Delete user

## 🔨 Development

### Running in development mode
```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing the API
Visit http://localhost:8000/docs for interactive API documentation.

Example API calls:
```bash
# Get all items
curl http://localhost:8000/api/v1/items

# Create new item
curl -X POST http://localhost:8000/api/v1/items \
  -H "Content-Type: application/json" \
  -d '{"name": "New Item", "description": "Test item", "price": 19.99}'
```

## 🏗️ Extending the API

### Adding New Endpoints

1. **Create endpoint module** in `app/api/api_v1/endpoints/`:
   ```python
   # app/api/api_v1/endpoints/my_new_endpoint.py
   from fastapi import APIRouter
   
   router = APIRouter()
   
   @router.get("/")
   async def get_my_data():
       return {"message": "Hello from new endpoint"}
   ```

2. **Add to main router** in `app/api/api_v1/api.py`:
   ```python
   from app.api.api_v1.endpoints import my_new_endpoint
   
   api_router.include_router(
       my_new_endpoint.router, 
       prefix="/my-endpoint", 
       tags=["my-endpoint"]
   )
   ```

### Adding Models
Add Pydantic models in `app/models/schemas.py`:
```python
class MyModel(BaseModel):
    name: str
    value: int
```

### Adding Services
Create business logic in `app/services/`:
```python
# app/services/my_service.py
class MyService:
    def process_data(self, data):
        # Business logic here
        return processed_data
```

### Database Integration
To add a database:
1. Install database dependencies (e.g., `sqlalchemy`, `alembic`)
2. Create database models in `app/models/database.py`
3. Add database connection in `app/core/database.py`
4. Use dependency injection in endpoints

## 🔒 Configuration

Edit `.env` file or environment variables:
- `PROJECT_NAME` - API name
- `VERSION` - API version
- `ENVIRONMENT` - development/production
- `DEBUG` - Enable debug mode
- `DATABASE_URL` - Database connection string

## 📝 Next Steps

- [ ] Add database integration (SQLAlchemy + Alembic)
- [ ] Add authentication and authorization
- [ ] Add logging and monitoring
- [ ] Add input validation and error handling
- [ ] Add unit and integration tests
- [ ] Add Docker containerization
- [ ] Add CI/CD pipeline

## 🤝 Contributing

This backend is designed to be modular and extensible. Follow the existing patterns when adding new features.