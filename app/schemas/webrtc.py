from typing import Literal

from pydantic import BaseModel, Field


class WebRTCOfferRequest(BaseModel):
    token: str = Field(..., min_length=1)
    sdp: str = Field(..., min_length=1)
    type: Literal["offer"] = "offer"


class WebRTCOfferResponse(BaseModel):
    session_id: str
    sdp: str
    type: Literal["answer"] = "answer"

