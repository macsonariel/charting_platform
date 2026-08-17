"""
Trading Buddy Backend API
FastAPI backend for serving market analysis data
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone
import sys
import os

# Add project root to path (parent of backend directory)
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now import from backend package
from backend.api import chart_data, core_api, indicators_api, narrative_api


app = FastAPI(
    title="Trading Buddy API",
    description="Market analysis API for Trading Buddy",
    version="1.0.0"
)

# The deployed UI and API share an origin, so production does not require CORS
# by default. Explicit origins can be supplied for separately hosted clients.
def _allowed_origins() -> list[str]:
    configured = os.getenv("ALLOWED_ORIGINS", "")
    if configured.strip():
        return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]

    if os.getenv("APP_ENV", "development").lower() == "production":
        return []

    return [
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8001",
        "http://localhost:8000",
        "http://localhost:8001",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directories for HTML, CSS, and JavaScript (from app/ folder)
app_root = os.path.join(project_root, "app")
app.mount("/app/html", StaticFiles(directory=os.path.join(app_root, "html")), name="app_html")
app.mount("/app/css", StaticFiles(directory=os.path.join(app_root, "css")), name="app_css")
app.mount("/app/js", StaticFiles(directory=os.path.join(app_root, "js")), name="app_js")
app.mount("/html", StaticFiles(directory=os.path.join(app_root, "html")), name="html")
app.mount("/css", StaticFiles(directory=os.path.join(app_root, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(app_root, "js")), name="js")
app.mount("/script", StaticFiles(directory=os.path.join(app_root, "js")), name="script")  # Alias for backwards compatibility
app.mount("/img", StaticFiles(directory=os.path.join(app_root, "img")), name="img")

# Include routers
app.include_router(chart_data.router)
app.include_router(core_api.router)
app.include_router(narrative_api.router)
app.include_router(indicators_api.router)

@app.get("/")
async def root():
    """Root endpoint - redirect to the dashboard"""
    return RedirectResponse(url="/html/dashboard/index.html")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
