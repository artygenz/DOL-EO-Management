"""
Chat routes for handling chat interactions.

This module provides endpoints for both streaming and non-streaming chat responses,
following LLD principles with proper separation of concerns.
"""

from typing import Dict, Any, Optional, Iterator, Union, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
import time
import logging

from src.core.client_hub import get_database_session_maker

def get_db():
    """Get database session generator for FastAPI dependency injection."""
    db = get_database_session_maker()()
    try:
        yield db
    finally:
        db.close()
from src.models.user import User
from src.core.dependencies import get_current_active_user
from src.app.chat.brain.pre_router import classify
from src.app.chat.brain.selector import select_tools
from src.app.chat.brain.query_runner import run_query_with_tools

router = APIRouter(prefix="/chat", tags=["chat"])

# Set up logging for streaming metrics
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    """Request model for chat interactions."""
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Response model for non-streaming chat."""
    response: str
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    data: Optional[Union[Dict[str, Any], List[Any]]] = None
    processing: Optional[list[str]] = None


# Authentication is handled by get_current_active_user from core.dependencies


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> ChatResponse:
    """
    Non-streaming chat endpoint.
    
    Processes a chat message and returns a complete response.
    """
    try:
        # Build context
        ctx = {
            "role": current_user.role,
            "user_id": str(current_user.id)
        }
        if request.context:
            ctx.update(request.context)

        # Classify the message
        route = classify(request.message)
        entity = route.get("entity")
        intents = route.get("intents", ["search"]) or ["search"]
        hints = route.get("hints", {})

        # Select appropriate tools
        tool_fns, tool_specs, selected_entity = select_tools(db, current_user, entity, intents)

        # Execute query
        result = run_query_with_tools(
            request.message,
            tool_fns,
            tool_specs,
            context=ctx,
            hints=hints,
            entity=selected_entity
        )

        return ChatResponse(
            response=result.get("final", "No response generated"),
            tool=result.get("tool"),
            args=result.get("args"),
            data=result.get("data"),
            processing=result.get("processing", [])
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat request: {str(e)}"
        )

@router.get("/health")
async def chat_health() -> Dict[str, str]:
    """Health check endpoint for chat service."""
    return {"status": "healthy", "service": "chat"}
