"""
RoboAdvisor AI — FastAPI Backend
REST + WebSocket endpoints for the React frontend.
"""

import os
import json
import asyncio
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from graph import run_advisor, get_last_response
from db.memory import Memory


# ── App Setup ──

app = FastAPI(
    title="RoboAdvisor AI",
    description="AI-powered robo-advisor with Black-Litterman optimization",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    app.state.memory = Memory()
    print("🚀 RoboAdvisor AI backend started")

# Allow React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── In-memory session store (maps session_id → agent state) ──
# In production, you'd reconstruct from Supabase
active_sessions: dict[str, dict] = {}


# ── REST Endpoints ──

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    profile_complete: bool
    strategy: dict | None = None
    research: list[dict] | None = None


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Simple REST endpoint — send a message, get a response.
    Good for testing. For real-time streaming, use the WebSocket.
    """
    mem = app.state.memory
    
    # Get or create session
    if req.session_id and req.session_id in active_sessions:
        state = active_sessions[req.session_id]
        session_id = req.session_id
    else:
        session_id = mem.create_session()
        state = None
    
    # Save user message to Supabase
    mem.save_message(session_id, "user", req.message)
    
    # Run the agent graph (blocking — no streaming)
    state = run_advisor(req.message, state)
    active_sessions[session_id] = state
    
    # Get the assistant response
    response = get_last_response(state)
    
    # Save assistant response to Supabase
    mem.save_message(session_id, "assistant", response, 
                     metadata={"agent": state.get("current_agent", "unknown")})
    
    # Save profile if complete
    if state.get("profile_complete") and state.get("investment_profile"):
        try:
            mem.save_profile(session_id, state["investment_profile"])
        except Exception:
            pass  # Already saved
    
    # Save strategy if generated
    if state.get("strategy"):
        try:
            mem.save_strategy(session_id, state["strategy"])
        except Exception:
            pass
    
    return ChatResponse(
        session_id=session_id,
        response=response,
        profile_complete=state.get("profile_complete", False),
        strategy=state.get("strategy"),
        research=state.get("research_results"),
    )


@app.get("/sessions")
async def list_sessions():
    """List recent sessions."""
    mem = app.state.memory
    sessions = mem.list_sessions(limit=20)
    return {"sessions": sessions}


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get full session history."""
    mem = app.state.memory
    data = mem.load_full_session(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


# ── WebSocket Endpoint (real-time streaming) ──

@app.websocket("/ws/{session_id}")
async def websocket_chat(ws: WebSocket, session_id: str = "new"):
    """
    WebSocket for real-time chat.
    
    Client sends: {"message": "I have $50K to invest..."}
    Server streams: 
        {"type": "status", "message": "Parsing your profile..."}
        {"type": "status", "message": "Researching AAPL..."}
        {"type": "response", "content": "Here's your portfolio..."}
        {"type": "strategy", "data": {...}}
    """
    await ws.accept()
    mem = app.state.memory
    
    # Create or load session
    if session_id == "new":
        session_id = mem.create_session()
        state = None
    elif session_id in active_sessions:
        state = active_sessions[session_id]
    else:
        state = None
    
    # Send session ID to client
    await ws.send_json({"type": "session", "session_id": session_id})
    
    try:
        while True:
            # Wait for client message
            data = await ws.receive_json()
            user_message = data.get("message", "")
            
            if not user_message:
                continue
            
            # Save user message
            mem.save_message(session_id, "user", user_message)
            
            # Send status updates while processing
            await ws.send_json({"type": "status", "message": "Processing your request..."})
            
            # Run agent graph in a thread (it's blocking/CPU-bound)
            state = await asyncio.to_thread(run_advisor, user_message, state)
            active_sessions[session_id] = state
            
            # Get response
            response = get_last_response(state)
            
            # Save to Supabase
            mem.save_message(session_id, "assistant", response,
                           metadata={"agent": state.get("current_agent", "unknown")})
            
            # Save profile if complete
            if state.get("profile_complete") and state.get("investment_profile"):
                try:
                    mem.save_profile(session_id, state["investment_profile"])
                    await ws.send_json({"type": "status", "message": "Profile saved ✓"})
                except Exception:
                    pass
            
            # Send research results if available
            if state.get("research_results"):
                await ws.send_json({
                    "type": "research",
                    "data": state["research_results"],
                })
            
            # Send strategy if generated
            if state.get("strategy"):
                try:
                    mem.save_strategy(session_id, state["strategy"])
                except Exception:
                    pass
                
                await ws.send_json({
                    "type": "strategy",
                    "data": state["strategy"],
                })
            
            # Send the main response
            await ws.send_json({
                "type": "response",
                "content": response,
                "profile_complete": state.get("profile_complete", False),
            })
    
    except WebSocketDisconnect:
        print(f"Client disconnected: {session_id}")
        # Keep state in memory for reconnection
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
