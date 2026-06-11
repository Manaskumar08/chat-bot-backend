"""
Backward-compatible websocket entrypoint.

New code should import from app.realtime.handler or app.api.websocket.
"""

from app.realtime.handler import handle_voice_connection as handle_voice

