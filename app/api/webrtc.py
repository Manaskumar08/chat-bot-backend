import logging

from fastapi import APIRouter, HTTPException, status

from app.models.config import get_settings
from app.realtime.webrtc import (
    WebRTCVoiceTransport,
    aiortc_available,
    session_registry,
)
from app.schemas.webrtc import WebRTCOfferRequest, WebRTCOfferResponse

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


@router.post("/webrtc/offer", response_model=WebRTCOfferResponse)
async def create_webrtc_offer(payload: WebRTCOfferRequest) -> WebRTCOfferResponse:
    if not aiortc_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="aiortc is not installed",
        )

    transport = None
    try:
        transport = WebRTCVoiceTransport(token=payload.token)
        session_registry.register(transport)
        answer_sdp = await transport.create_answer(payload.sdp)
    except ValueError as exc:
        if transport is not None:
            await transport.close()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        if transport is not None:
            await transport.close()
        logger.exception("Failed to create WebRTC offer")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Failed to create WebRTC answer: {exc!r}"
                if settings.DEBUG
                else "Failed to create WebRTC answer"
            ),
        ) from exc

    return WebRTCOfferResponse(
        session_id=transport.session_id,
        sdp=answer_sdp,
    )
