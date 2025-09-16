"""
Chat routes for handling chat interactions.

This module provides endpoints for both streaming and non-streaming chat responses,
following LLD principles with proper separation of concerns.
"""

from typing import Dict, Any, Optional, Iterator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
import time

from src.db.session import get_db
from src.models.user import User
from src.core.dependencies import get_current_active_user
from src.app.chat.brain.pre_router import classify
from src.app.chat.brain.selector import select_tools
from src.app.chat.brain.query_runner import run_query_with_tools, run_query_with_tools_streaming

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat interactions."""
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Response model for non-streaming chat."""
    response: str
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
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


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> StreamingResponse:
    """
    Streaming chat endpoint.
    
    Processes a chat message and returns a streaming response.
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

        def generate_stream() -> Iterator[str]:
            """Generate streaming response."""
            try:
                # Send initial metadata
                metadata = {
                    "type": "metadata",
                    "tool": None,
                    "args": None,
                    "processing": []
                }
                yield f"data: {json.dumps(metadata)}\n\n"

                # Process streaming query
                for result in run_query_with_tools_streaming(
                    request.message,
                    tool_fns,
                    tool_specs,
                    context=ctx,
                    hints=hints,
                    entity=selected_entity
                ):
                    # Send tool metadata
                    if "tool" in result:
                        metadata = {
                            "type": "metadata",
                            "tool": result.get("tool"),
                            "args": result.get("args"),
                            "processing": result.get("processing", [])
                        }
                        yield f"data: {json.dumps(metadata)}\n\n"

                    # Stream the response chunks
                    if "final_stream" in result:
                        for chunk in result["final_stream"]:
                            # Add artificial delay to make streaming visible
                            time.sleep(0.05)  # 50ms delay between chunks
                            
                            chunk_data = {
                                "type": "chunk",
                                "content": chunk
                            }
                            yield f"data: {json.dumps(chunk_data)}\n\n"

                # Send completion signal
                completion = {
                    "type": "complete",
                    "message": "Stream completed"
                }
                yield f"data: {json.dumps(completion)}\n\n"

            except Exception as e:
                error_data = {
                    "type": "error",
                    "message": f"Streaming error: {str(e)}"
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing streaming chat request: {str(e)}"
        )


@router.get("/health")
async def chat_health() -> Dict[str, str]:
    """Health check endpoint for chat service."""
    return {"status": "healthy", "service": "chat"}
