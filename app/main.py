from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth_example import router as auth_router
from app.api.voice import router as voice_router
from app.api.webrtc import router as webrtc_router
from app.api.websocket import router as websocket_router
from app.realtime.session_manager import voice_session_manager
from app.models.config import get_settings
from app.models.session import create_all_tables

# Initialize settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    create_all_tables()
    await voice_session_manager.start_cleanup_loop()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks on shutdown"""
    await voice_session_manager.stop_cleanup_loop()



app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Auth"]
)

app.include_router(
    voice_router,
    tags=["Voice"]
)

app.include_router(
    websocket_router,
    tags=["Voice Chat"]
)

app.include_router(
    webrtc_router,
    tags=["WebRTC"]
)
