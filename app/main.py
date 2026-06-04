from fastapi import FastAPI
from fastapi import WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.websocket import handle_voice
from app.api.auth_example import router as auth_router
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



@app.websocket("/voice-chat/{token}")
async def voice_chat(websocket: WebSocket):

    await handle_voice(websocket)


app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Auth"]
)