# PLD-AGILE

A full-stack web application for agile project management, featuring a React + Tailwind CSS frontend and a FastAPI Python backend.

## 🏗️ Project Structure

```
PLD-AGILE/
├── backend/                 # FastAPI Python backend
│   ├── main.py             # Application entry point
│   ├── requirements.txt    # Python dependencies
│   ├── README.md          # Backend-specific documentation
│   └── app/               # Main application module
│       ├── api/           # API routing
│       │   └── api_v1/    # API version 1
│       │       ├── api.py # Main API router
│       │       └── endpoints/ # Individual endpoint modules
│       ├── core/          # Core configuration
│       ├── models/        # Pydantic models and schemas
│       └── services/      # Business logic services
├── frontend/               # React + Vite frontend
│   ├── src/               # Source files
│   │   ├── App.jsx        # Main React component
│   │   ├── main.jsx       # React entry point
│   │   └── styles.css     # Tailwind CSS styles
│   ├── package.json       # Node.js dependencies
│   ├── vite.config.js     # Vite configuration
│   ├── tailwind.config.cjs # Tailwind CSS configuration
│   └── README.md          # Frontend-specific documentation
└── fichiersXMLPickupDelivery/ # XML data files
    └── *.xml              # Various XML request/plan files
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (for backend)
- **Node.js 18+** (for frontend)
- **npm** or **yarn** (package manager)

### Backend Setup

1. Navigate to the backend directory:
   ```powershell
   cd backend
   ```

2. Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```

3. Install Python dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

4. Start the FastAPI development server:
   ```powershell
   uvicorn main:app --reload
   ```

   The API will be available at:
   - **API**: http://localhost:8000
   - **Interactive docs**: http://localhost:8000/docs
   - **OpenAPI schema**: http://localhost:8000/openapi.json

### Frontend Setup

1. Navigate to the frontend directory:
   ```powershell
   cd frontend
   ```

2. Install Node.js dependencies:
   ```powershell
   npm install
   ```

3. Start the Vite development server:
   ```powershell
   npm run dev
   ```

   The web application will be available at:
   - **Frontend**: http://localhost:5173

## 🛠️ Development

### Backend Development

The backend uses FastAPI with a modular architecture:

- **`main.py`**: Application entry point and configuration
- **`app/api/`**: API routing and endpoint definitions
- **`app/models/`**: Pydantic models for request/response schemas
- **`app/core/`**: Core configuration and settings
- **`app/services/`**: Business logic and service layer

#### Adding New Endpoints

1. Create endpoint module in `app/api/api_v1/endpoints/`
2. Define Pydantic models in `app/models/schemas.py`
3. Add router to `app/api/api_v1/api.py`

#### Environment Configuration

Create a `.env` file in the backend directory:
```env
APP_NAME=PLD-AGILE Backend
DEBUG=True
API_V1_STR=/api/v1
```

### Frontend Development

The frontend uses React with Vite and Tailwind CSS:

- **Hot reload**: Changes are reflected immediately
- **Tailwind CSS**: Utility-first CSS framework
- **Modern React**: Functional components with hooks

#### Available Scripts

```powershell
npm run dev      # Start development server
npm run build    # Build for production
npm run preview  # Preview production build
```

## 📦 Dependencies

### Backend Dependencies

- **FastAPI**: Modern, fast web framework for APIs
- **Uvicorn**: ASGI server for running FastAPI
- **Pydantic**: Data validation using Python type annotations
- **Pydantic-settings**: Settings management

### Frontend Dependencies

- **React**: UI library for building user interfaces
- **Vite**: Fast build tool and development server
- **Tailwind CSS**: Utility-first CSS framework
- **PostCSS**: CSS processing tool

## 🧪 Testing

### Backend Testing

```powershell
cd backend
pip install pytest pytest-asyncio httpx
pytest
```

### Frontend Testing

```powershell
cd frontend
npm install --save-dev vitest @testing-library/react
npm run test
```

## 📝 API Documentation

When the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Example API endpoints:
- `GET /api/v1/items/` - List all items
- `POST /api/v1/items/` - Create new item
- `GET /api/v1/users/me` - Get current user

## 🔧 Configuration

### Backend Configuration

Environment variables can be set in `.env` file or system environment:

- `APP_NAME`: Application name
- `DEBUG`: Enable debug mode
- `API_V1_STR`: API version prefix

### Frontend Configuration

Vite configuration in `vite.config.js`:
- Development server port: 5173
- Build output directory: `dist/`

## 🚀 Deployment

### Backend Deployment

1. Install production dependencies:
   ```bash
   pip install gunicorn
   ```

2. Run with Gunicorn:
   ```bash
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

### Frontend Deployment

1. Build the application:
   ```powershell
   npm run build
   ```

2. Serve the `dist/` directory with any static file server

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is part of the PLD-AGILE course at INSA.

## 🔗 Related Files

- XML data files are located in `fichiersXMLPickupDelivery/`
- Backend-specific README: `backend/README.md`
- Frontend-specific README: `frontend/README.md`
