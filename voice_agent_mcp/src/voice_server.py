#!/usr/bin/env python3
"""
Voice Agent MCP Server - Real-time voice interactions for Arkie Auto-SDR
Powered by LiveKit, AssemblyAI, and Supabase
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from fastapi import FastAPI, HTTPException, Depends, WebSocket, UploadFile, File
from pydantic import BaseModel
import uvicorn
from livekit import api, rtc
import assemblyai as aai
from supabase import create_client, Client
import httpx
import uuid
import wave
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
RECORDINGS_DIR = Path(__file__).parent.parent / "recordings"
RECORDINGS_DIR.mkdir(exist_ok=True)

# FastAPI app

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os

# JWT Configuration
SECRET_KEY = os.getenv("PULSER_JWT_SECRET", "change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = ["/", "/health", "/auth/token"]

app = FastAPI(title="Voice Agent MCP Server")

from fastapi import APIRouter

# Create versioned router
api_v1 = APIRouter(prefix="/api/v1")

# Initialize clients
supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY

# Pydantic models
class VoiceSessionRequest(BaseModel):
    session_id: Optional[str] = None
    participant_name: str
    context: Dict[str, Any] = {}
    language: str = "en"
    
class TranscriptionRequest(BaseModel):
    audio_url: Optional[str] = None
    session_id: Optional[str] = None
    speaker_labels: bool = True
    
class CallAnalysisRequest(BaseModel):
    session_id: str
    analysis_type: str = "sentiment"  # sentiment, summary, action_items
    
class WebCrawlRequest(BaseModel):
    url: str
    extract_contacts: bool = True
    max_depth: int = 2

# Voice Session Manager
class VoiceSessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.livekit_client = None
        
    async def init_livekit(self):
        """Initialize LiveKit client"""
        try:
            self.livekit_client = api.LiveKitAPI(
                LIVEKIT_URL,
                LIVEKIT_API_KEY,
                LIVEKIT_API_SECRET
            )
            logger.info("LiveKit client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize LiveKit: {e}")
    
    async def create_session(self, request: VoiceSessionRequest) -> Dict[str, Any]:
        """Create a new voice session"""
        session_id = request.session_id or str(uuid.uuid4())
        
        # Create LiveKit room
        room_name = f"arkie_{session_id}"
        
        # Generate participant token
        token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token.with_identity(request.participant_name)\
             .with_name(request.participant_name)\
             .with_grants(api.VideoGrants(
                 room_join=True,
                 room=room_name,
                 can_publish=True,
                 can_subscribe=True
             ))
        
        # Store session info
        self.sessions[session_id] = {
            "id": session_id,
            "room_name": room_name,
            "participant": request.participant_name,
            "context": request.context,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "recordings": []
        }
        
        # Save to Supabase if available
        if supabase:
            try:
                supabase.table("voice_sessions").insert({
                    "session_id": session_id,
                    "participant_name": request.participant_name,
                    "context": request.context,
                    "status": "active"
                }).execute()
            except Exception as e:
                logger.error(f"Failed to save session to Supabase: {e}")
        
        return {
            "session_id": session_id,
            "room_name": room_name,
            "token": token.to_jwt(),
            "livekit_url": LIVEKIT_URL
        }
    
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a voice session"""
        if session_id not in self.sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.sessions[session_id]
        session["status"] = "completed"
        session["ended_at"] = datetime.now().isoformat()
        
        # Update in Supabase
        if supabase:
            try:
                supabase.table("voice_sessions").update({
                    "status": "completed",
                    "ended_at": session["ended_at"]
                }).eq("session_id", session_id).execute()
            except Exception as e:
                logger.error(f"Failed to update session in Supabase: {e}")
        
        return {
            "success": True,
            "session_id": session_id,
            "duration": "calculated_duration"
        }

# MCP Tools
class MCPTools:
    @staticmethod
    async def start_voice_session(request: VoiceSessionRequest) -> Dict[str, Any]:
        """Start a new voice interaction session"""
        try:
            session_manager = app.state.session_manager
            result = await session_manager.create_session(request)
            
            return {
                "success": True,
                **result
            }
        except Exception as e:
            logger.error(f"Error starting voice session: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def transcribe_audio(request: TranscriptionRequest) -> Dict[str, Any]:
        """Transcribe audio using AssemblyAI"""
        try:
            if not ASSEMBLYAI_API_KEY:
                return {"success": False, "error": "AssemblyAI API key not configured"}
            
            transcriber = aai.Transcriber()
            
            # Configure transcription
            config = aai.TranscriptionConfig(
                speaker_labels=request.speaker_labels,
                language_detection=True,
                entity_detection=True,
                sentiment_analysis=True,
                auto_chapters=True,
                content_safety=True
            )
            
            # Transcribe
            if request.audio_url:
                transcript = transcriber.transcribe(request.audio_url, config=config)
            else:
                return {"success": False, "error": "Audio URL required"}
            
            # Process results
            result = {
                "success": True,
                "transcript_id": transcript.id,
                "text": transcript.text,
                "confidence": transcript.confidence,
                "duration": transcript.audio_duration,
                "words": len(transcript.words) if transcript.words else 0
            }
            
            # Add speaker labels if available
            if transcript.utterances:
                result["utterances"] = [
                    {
                        "speaker": utt.speaker,
                        "text": utt.text,
                        "start": utt.start,
                        "end": utt.end,
                        "confidence": utt.confidence
                    }
                    for utt in transcript.utterances
                ]
            
            # Add sentiment analysis
            if transcript.sentiment_analysis_results:
                result["sentiment"] = [
                    {
                        "text": s.text,
                        "sentiment": s.sentiment,
                        "confidence": s.confidence
                    }
                    for s in transcript.sentiment_analysis_results
                ]
            
            # Add entities
            if transcript.entities:
                result["entities"] = [
                    {
                        "text": e.text,
                        "type": e.entity_type,
                        "start": e.start,
                        "end": e.end
                    }
                    for e in transcript.entities
                ]
            
            # Save to Supabase
            if supabase and request.session_id:
                try:
                    supabase.table("transcriptions").insert({
                        "session_id": request.session_id,
                        "transcript_id": transcript.id,
                        "text": transcript.text,
                        "metadata": result
                    }).execute()
                except Exception as e:
                    logger.error(f"Failed to save transcription: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def analyze_call(request: CallAnalysisRequest) -> Dict[str, Any]:
        """Analyze call transcripts for insights"""
        try:
            # Fetch transcripts from Supabase
            if not supabase:
                return {"success": False, "error": "Supabase not configured"}
            
            response = supabase.table("transcriptions")\
                .select("*")\
                .eq("session_id", request.session_id)\
                .execute()
            
            if not response.data:
                return {"success": False, "error": "No transcripts found"}
            
            transcripts = response.data
            combined_text = " ".join([t["text"] for t in transcripts])
            
            analysis = {
                "session_id": request.session_id,
                "total_transcripts": len(transcripts),
                "total_words": sum(len(t["text"].split()) for t in transcripts)
            }
            
            if request.analysis_type == "summary":
                # Generate summary (mock for now)
                analysis["summary"] = f"Call discussed {len(transcripts)} topics with positive engagement"
                analysis["key_points"] = [
                    "Customer showed interest in product features",
                    "Pricing concerns were addressed",
                    "Follow-up meeting scheduled"
                ]
                
            elif request.analysis_type == "sentiment":
                # Aggregate sentiment from transcripts
                sentiments = []
                for t in transcripts:
                    if "sentiment" in t.get("metadata", {}):
                        sentiments.extend(t["metadata"]["sentiment"])
                
                if sentiments:
                    positive = sum(1 for s in sentiments if s["sentiment"] == "POSITIVE")
                    negative = sum(1 for s in sentiments if s["sentiment"] == "NEGATIVE")
                    neutral = sum(1 for s in sentiments if s["sentiment"] == "NEUTRAL")
                    
                    analysis["sentiment_breakdown"] = {
                        "positive": positive,
                        "negative": negative,
                        "neutral": neutral,
                        "overall": "POSITIVE" if positive > negative else "NEUTRAL"
                    }
                    
            elif request.analysis_type == "action_items":
                # Extract action items (mock for now)
                analysis["action_items"] = [
                    {
                        "task": "Send product documentation",
                        "assignee": "Sales Rep",
                        "due_date": "2024-01-15"
                    },
                    {
                        "task": "Schedule follow-up demo",
                        "assignee": "Sales Rep",
                        "due_date": "2024-01-20"
                    }
                ]
            
            return {
                "success": True,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"Error analyzing call: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def crawl_for_contacts(request: WebCrawlRequest) -> Dict[str, Any]:
        """Crawl website for contact information"""
        try:
            # Mock implementation - in production use Firecrawl
            contacts = []
            
            # Simulate crawling
            async with httpx.AsyncClient() as client:
                response = await client.get(request.url)
                
                if response.status_code == 200:
                    # Mock contact extraction
                    contacts = [
                        {
                            "name": "John Doe",
                            "title": "Sales Director",
                            "email": "john.doe@example.com",
                            "phone": "+1-555-0123",
                            "source": request.url
                        },
                        {
                            "name": "Jane Smith",
                            "title": "Marketing Manager",
                            "email": "jane.smith@example.com",
                            "linkedin": "linkedin.com/in/janesmith",
                            "source": request.url
                        }
                    ]
            
            # Save to Supabase
            if supabase and contacts:
                try:
                    for contact in contacts:
                        supabase.table("crawled_contacts").insert({
                            **contact,
                            "crawled_at": datetime.now().isoformat()
                        }).execute()
                except Exception as e:
                    logger.error(f"Failed to save contacts: {e}")
            
            return {
                "success": True,
                "url": request.url,
                "contacts_found": len(contacts),
                "contacts": contacts
            }
            
        except Exception as e:
            logger.error(f"Error crawling for contacts: {e}")
            return {"success": False, "error": str(e)}

# WebSocket endpoint for real-time voice
@app.websocket("/ws/voice/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time voice streaming"""
    await websocket.accept()
    
    try:
        while True:
            # Receive audio chunks
            data = await websocket.receive_bytes()
            
            # Process audio (mock processing)
            # In production, forward to LiveKit or process directly
            
            # Send back transcription updates
            await websocket.send_json({
                "type": "transcription",
                "text": "Mock real-time transcription",
                "is_final": False
            })
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    app.state.session_manager = VoiceSessionManager()
    await app.state.session_manager.init_livekit()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "active", "service": "Voice Agent MCP Server"}

@api_v1.post("/mcp/tools/start_voice_session")
async def start_voice_session(request: VoiceSessionRequest, current_user: str = Depends(verify_token)):
    """Start a voice session"""
    result = await MCPTools.start_voice_session(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/transcribe_audio")
async def transcribe_audio(request: TranscriptionRequest, current_user: str = Depends(verify_token)):
    """Transcribe audio file"""
    result = await MCPTools.transcribe_audio(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/analyze_call")
async def analyze_call(request: CallAnalysisRequest, current_user: str = Depends(verify_token)):
    """Analyze call transcripts"""
    result = await MCPTools.analyze_call(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/crawl_for_contacts")
async def crawl_for_contacts(request: WebCrawlRequest, current_user: str = Depends(verify_token)):
    """Crawl website for contacts"""
    result = await MCPTools.crawl_for_contacts(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/upload_audio")
async def upload_audio(
    session_id: str,
    file: UploadFile = File(...)
, current_user: str = Depends(verify_token)):
    """Upload audio file for processing"""
    try:
        # Save file
        file_path = RECORDINGS_DIR / f"{session_id}_{file.filename}"
        contents = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Process with AssemblyAI
        # In production, upload to cloud storage first
        
        return {
            "success": True,
            "file_path": str(file_path),
            "size": len(contents),
            "ready_for_transcription": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# MCP metadata endpoint
@api_v1.get("/mcp/metadata")
async def get_metadata(current_user: str = Depends(verify_token)):
    """Return MCP server metadata"""
    return {
        "name": "voice-agent-mcp",
        "version": "1.0.0",
        "description": "Real-time voice interactions for Arkie Auto-SDR",
        "tools": [
            {
                "name": "start_voice_session",
                "description": "Start a new voice interaction session",
                "parameters": {
                    "session_id": "string (optional)",
                    "participant_name": "string",
                    "context": "object",
                    "language": "string (default: en)"
                }
            },
            {
                "name": "transcribe_audio",
                "description": "Transcribe audio with speaker labels",
                "parameters": {
                    "audio_url": "string",
                    "session_id": "string (optional)",
                    "speaker_labels": "boolean (default: true)"
                }
            },
            {
                "name": "analyze_call",
                "description": "Analyze call transcripts for insights",
                "parameters": {
                    "session_id": "string",
                    "analysis_type": "string (sentiment, summary, action_items)"
                }
            },
            {
                "name": "crawl_for_contacts",
                "description": "Extract contact information from websites",
                "parameters": {
                    "url": "string",
                    "extract_contacts": "boolean (default: true)",
                    "max_depth": "integer (default: 2)"
                }
            }
        ]
    }


# Include API v1 router
app.include_router(api_v1)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)