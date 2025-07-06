#!/usr/bin/env python3
"""
Video RAG MCP Server - Creative Diagnostics
Advanced video analysis system for creative performance, brand compliance, and content intelligence
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
import uvicorn
import cv2
import numpy as np
from PIL import Image
import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import speech_recognition as sr
import moviepy.editor as mp
from transformers import BlipProcessor, BlipForConditionalGeneration
import torch
import base64
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

app = FastAPI(title="Video RAG MCP Server")

from fastapi import APIRouter

# Create versioned router
api_v1 = APIRouter(prefix="/api/v1")

# Data directories
DATA_DIR = Path(__file__).parent.parent / "data"
VIDEOS_DIR = DATA_DIR / "videos"
PROCESSED_DIR = DATA_DIR / "processed"
FRAMES_DIR = DATA_DIR / "frames"
AUDIO_DIR = DATA_DIR / "audio"
LOGS_DIR = Path(__file__).parent.parent / "logs"

for dir_path in [DATA_DIR, VIDEOS_DIR, PROCESSED_DIR, FRAMES_DIR, AUDIO_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True)

# Initialize models and clients
text_encoder = SentenceTransformer('all-MiniLM-L6-v2')
qdrant_client = QdrantClient(":memory:")

# Initialize image captioning model
try:
    blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    logger.info("Image captioning model loaded")
except Exception as e:
    logger.warning(f"Could not load image model: {e}")
    blip_processor = None
    blip_model = None

# Pydantic models
class VideoAnalysisRequest(BaseModel):
    video_path: str
    analysis_type: str = "comprehensive"  # comprehensive, brand_compliance, performance_analysis
    extract_audio: bool = True
    frame_sampling_rate: int = 30  # Extract frame every N frames
    metadata: Optional[Dict[str, Any]] = {}

class CreativeAnalysisRequest(BaseModel):
    video_id: str
    brand_guidelines: Optional[Dict[str, Any]] = {}
    performance_metrics: Optional[Dict[str, Any]] = {}

class VideoSearchRequest(BaseModel):
    query: str
    search_type: str = "semantic"  # semantic, visual, audio, metadata
    filters: Optional[Dict[str, Any]] = {}
    limit: int = 10

class ComplianceCheckRequest(BaseModel):
    video_id: str
    brand_guidelines: Dict[str, Any]
    check_areas: List[str] = ["logo_placement", "color_compliance", "messaging", "audio_quality"]

# Video processing utilities
class VideoProcessor:
    @staticmethod
    def extract_frames(video_path: str, output_dir: str, frame_rate: int = 30) -> List[str]:
        """Extract frames from video at specified intervals"""
        try:
            cap = cv2.VideoCapture(video_path)
            frame_paths = []
            frame_count = 0
            saved_count = 0
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Save frame at specified intervals
                if frame_count % frame_rate == 0:
                    timestamp = frame_count / fps
                    frame_filename = f"frame_{saved_count:06d}_{timestamp:.2f}s.jpg"
                    frame_path = os.path.join(output_dir, frame_filename)
                    
                    cv2.imwrite(frame_path, frame)
                    frame_paths.append(frame_path)
                    saved_count += 1
                
                frame_count += 1
            
            cap.release()
            logger.info(f"Extracted {len(frame_paths)} frames from {video_path}")
            return frame_paths
            
        except Exception as e:
            logger.error(f"Error extracting frames: {e}")
            return []
    
    @staticmethod
    def extract_audio(video_path: str, output_path: str) -> str:
        """Extract audio from video"""
        try:
            video = mp.VideoFileClip(video_path)
            if video.audio:
                video.audio.write_audiofile(output_path, verbose=False, logger=None)
                video.close()
                return output_path
            else:
                logger.warning(f"No audio track found in {video_path}")
                return ""
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            return ""
    
    @staticmethod
    def get_video_metadata(video_path: str) -> Dict[str, Any]:
        """Extract video metadata"""
        try:
            cap = cv2.VideoCapture(video_path)
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            file_size = os.path.getsize(video_path)
            
            metadata = {
                "duration_seconds": duration,
                "fps": fps,
                "frame_count": frame_count,
                "width": width,
                "height": height,
                "aspect_ratio": width / height if height > 0 else 0,
                "file_size_bytes": file_size,
                "file_size_mb": file_size / (1024 * 1024)
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting video metadata: {e}")
            return {}

class AudioProcessor:
    @staticmethod
    def transcribe_audio(audio_path: str) -> Dict[str, Any]:
        """Transcribe audio to text"""
        try:
            recognizer = sr.Recognizer()
            
            # Convert to WAV if needed
            if not audio_path.endswith('.wav'):
                audio = mp.AudioFileClip(audio_path)
                wav_path = audio_path.replace(Path(audio_path).suffix, '.wav')
                audio.write_audiofile(wav_path, verbose=False, logger=None)
                audio.close()
                audio_path = wav_path
            
            with sr.AudioFile(audio_path) as source:
                audio_data = recognizer.record(source)
                
            # Transcribe using Google Speech Recognition
            try:
                transcript = recognizer.recognize_google(audio_data)
            except sr.UnknownValueError:
                transcript = ""
            except sr.RequestError:
                # Fallback to basic transcription
                transcript = "Audio transcription unavailable"
            
            result = {
                "transcript": transcript,
                "audio_duration": AudioProcessor._get_audio_duration(audio_path),
                "language": "en",  # Could be detected dynamically
                "confidence": 0.8  # Placeholder confidence score
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return {"transcript": "", "error": str(e)}
    
    @staticmethod
    def _get_audio_duration(audio_path: str) -> float:
        """Get audio duration in seconds"""
        try:
            audio = mp.AudioFileClip(audio_path)
            duration = audio.duration
            audio.close()
            return duration
        except:
            return 0.0

class VisualAnalyzer:
    @staticmethod
    def analyze_frame(frame_path: str) -> Dict[str, Any]:
        """Analyze individual frame for visual elements"""
        try:
            # Load image
            image = Image.open(frame_path)
            
            analysis = {
                "frame_path": frame_path,
                "dimensions": image.size,
                "mode": image.mode
            }
            
            # Generate caption if model is available
            if blip_processor and blip_model:
                inputs = blip_processor(image, return_tensors="pt")
                out = blip_model.generate(**inputs, max_length=50)
                caption = blip_processor.decode(out[0], skip_special_tokens=True)
                analysis["caption"] = caption
            
            # Color analysis
            colors = VisualAnalyzer._analyze_colors(image)
            analysis["color_analysis"] = colors
            
            # Basic composition analysis
            composition = VisualAnalyzer._analyze_composition(image)
            analysis["composition"] = composition
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing frame {frame_path}: {e}")
            return {"frame_path": frame_path, "error": str(e)}
    
    @staticmethod
    def _analyze_colors(image: Image.Image) -> Dict[str, Any]:
        """Analyze color palette and distribution"""
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Get dominant colors (simplified)
            colors = image.getcolors(maxcolors=256*256*256)
            if colors:
                dominant_color = max(colors, key=lambda item: item[0])
                rgb = dominant_color[1]
                
                return {
                    "dominant_color": {
                        "rgb": rgb,
                        "hex": f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}",
                        "percentage": dominant_color[0] / (image.width * image.height)
                    },
                    "total_unique_colors": len(colors)
                }
            
            return {"dominant_color": None, "total_unique_colors": 0}
            
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def _analyze_composition(image: Image.Image) -> Dict[str, Any]:
        """Analyze image composition"""
        try:
            width, height = image.size
            
            # Basic composition metrics
            composition = {
                "aspect_ratio": width / height,
                "orientation": "landscape" if width > height else "portrait" if height > width else "square",
                "resolution_category": "high" if width * height > 1920 * 1080 else "medium" if width * height > 1280 * 720 else "low"
            }
            
            return composition
            
        except Exception as e:
            return {"error": str(e)}

class CreativeAnalyzer:
    @staticmethod
    def analyze_brand_compliance(video_data: Dict, brand_guidelines: Dict) -> Dict[str, Any]:
        """Analyze video for brand compliance"""
        
        compliance_report = {
            "overall_score": 0.0,
            "checks_performed": [],
            "violations": [],
            "recommendations": []
        }
        
        # Check logo placement (simplified)
        if "logo_placement" in brand_guidelines:
            logo_check = CreativeAnalyzer._check_logo_placement(video_data, brand_guidelines["logo_placement"])
            compliance_report["checks_performed"].append("logo_placement")
            if not logo_check["compliant"]:
                compliance_report["violations"].append(logo_check)
        
        # Check color compliance
        if "brand_colors" in brand_guidelines:
            color_check = CreativeAnalyzer._check_color_compliance(video_data, brand_guidelines["brand_colors"])
            compliance_report["checks_performed"].append("color_compliance")
            if not color_check["compliant"]:
                compliance_report["violations"].append(color_check)
        
        # Check messaging compliance
        if "messaging_guidelines" in brand_guidelines and "transcript" in video_data:
            message_check = CreativeAnalyzer._check_messaging(video_data["transcript"], brand_guidelines["messaging_guidelines"])
            compliance_report["checks_performed"].append("messaging")
            if not message_check["compliant"]:
                compliance_report["violations"].append(message_check)
        
        # Calculate overall score
        total_checks = len(compliance_report["checks_performed"])
        violations = len(compliance_report["violations"])
        compliance_report["overall_score"] = (total_checks - violations) / total_checks if total_checks > 0 else 1.0
        
        return compliance_report
    
    @staticmethod
    def _check_logo_placement(video_data: Dict, logo_guidelines: Dict) -> Dict[str, Any]:
        """Check logo placement compliance"""
        # Simplified logo placement check
        return {
            "check_type": "logo_placement",
            "compliant": True,  # Placeholder - would implement actual logo detection
            "details": "Logo placement analysis requires computer vision implementation",
            "confidence": 0.5
        }
    
    @staticmethod
    def _check_color_compliance(video_data: Dict, brand_colors: Dict) -> Dict[str, Any]:
        """Check brand color compliance"""
        # Simplified color compliance check
        compliant = True
        details = []
        
        if "frames_analysis" in video_data:
            for frame_data in video_data["frames_analysis"][:5]:  # Check first 5 frames
                if "color_analysis" in frame_data:
                    dominant_color = frame_data["color_analysis"].get("dominant_color", {})
                    if dominant_color.get("hex"):
                        # Check if dominant color matches brand colors
                        if dominant_color["hex"] not in brand_colors.get("approved_colors", []):
                            details.append(f"Non-brand color detected: {dominant_color['hex']}")
        
        return {
            "check_type": "color_compliance",
            "compliant": len(details) == 0,
            "details": details,
            "confidence": 0.7
        }
    
    @staticmethod
    def _check_messaging(transcript: str, messaging_guidelines: Dict) -> Dict[str, Any]:
        """Check messaging compliance"""
        violations = []
        
        # Check for required phrases
        required_phrases = messaging_guidelines.get("required_phrases", [])
        for phrase in required_phrases:
            if phrase.lower() not in transcript.lower():
                violations.append(f"Missing required phrase: {phrase}")
        
        # Check for prohibited phrases
        prohibited_phrases = messaging_guidelines.get("prohibited_phrases", [])
        for phrase in prohibited_phrases:
            if phrase.lower() in transcript.lower():
                violations.append(f"Contains prohibited phrase: {phrase}")
        
        return {
            "check_type": "messaging",
            "compliant": len(violations) == 0,
            "details": violations,
            "confidence": 0.9
        }

# Setup Qdrant collection
def setup_qdrant():
    """Initialize Qdrant collection for video data"""
    try:
        collections = qdrant_client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if "video_intelligence" not in collection_names:
            qdrant_client.create_collection(
                collection_name="video_intelligence",
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            logger.info("Created video intelligence collection in Qdrant")
        else:
            logger.info("Video intelligence collection already exists")
            
    except Exception as e:
        logger.error(f"Error setting up Qdrant: {e}")

# MCP Tools
class MCPTools:
    @staticmethod
    async def analyze_video(request: VideoAnalysisRequest) -> Dict[str, Any]:
        """Analyze video for content, compliance, and performance insights"""
        try:
            video_path = Path(request.video_path)
            if not video_path.exists():
                return {"success": False, "error": f"Video file not found: {video_path}"}
            
            video_id = hashlib.md5(f"{video_path.name}{datetime.now().isoformat()}".encode()).hexdigest()
            logger.info(f"Starting video analysis {video_id} for: {video_path.name}")
            
            # Create analysis directory
            analysis_dir = PROCESSED_DIR / video_id
            analysis_dir.mkdir(exist_ok=True)
            
            frames_dir = analysis_dir / "frames"
            frames_dir.mkdir(exist_ok=True)
            
            analysis_result = {
                "video_id": video_id,
                "video_path": str(video_path),
                "analysis_type": request.analysis_type,
                "started_at": datetime.now().isoformat(),
                "metadata": {},
                "frames_analysis": [],
                "audio_analysis": {},
                "creative_insights": {}
            }
            
            # Extract video metadata
            metadata = VideoProcessor.get_video_metadata(str(video_path))
            analysis_result["metadata"] = {**metadata, **request.metadata}
            
            # Extract and analyze frames
            frame_paths = VideoProcessor.extract_frames(
                str(video_path), 
                str(frames_dir), 
                request.frame_sampling_rate
            )
            
            for frame_path in frame_paths[:10]:  # Analyze first 10 frames
                frame_analysis = VisualAnalyzer.analyze_frame(frame_path)
                analysis_result["frames_analysis"].append(frame_analysis)
            
            # Extract and analyze audio
            if request.extract_audio:
                audio_path = analysis_dir / f"{video_id}_audio.wav"
                extracted_audio = VideoProcessor.extract_audio(str(video_path), str(audio_path))
                
                if extracted_audio:
                    audio_analysis = AudioProcessor.transcribe_audio(extracted_audio)
                    analysis_result["audio_analysis"] = audio_analysis
            
            # Generate creative insights
            insights = {
                "visual_themes": [],
                "dominant_colors": [],
                "pacing_analysis": {
                    "total_frames": len(frame_paths),
                    "duration": metadata.get("duration_seconds", 0),
                    "estimated_scenes": max(1, len(frame_paths) // 10)
                },
                "content_summary": analysis_result["audio_analysis"].get("transcript", "No audio transcript available")[:200]
            }
            
            # Extract visual themes from frame captions
            for frame_data in analysis_result["frames_analysis"]:
                if "caption" in frame_data:
                    insights["visual_themes"].append(frame_data["caption"])
                if "color_analysis" in frame_data and frame_data["color_analysis"].get("dominant_color"):
                    insights["dominant_colors"].append(frame_data["color_analysis"]["dominant_color"])
            
            analysis_result["creative_insights"] = insights
            
            # Store in vector database
            content_text = f"{analysis_result['audio_analysis'].get('transcript', '')} {' '.join(insights['visual_themes'][:5])}"
            if content_text.strip():
                embedding = text_encoder.encode(content_text).tolist()
                
                point = PointStruct(
                    id=video_id,
                    vector=embedding,
                    payload={
                        "video_id": video_id,
                        "video_name": video_path.name,
                        "analysis_type": request.analysis_type,
                        "duration": metadata.get("duration_seconds", 0),
                        "created_at": datetime.now().isoformat(),
                        "content_summary": content_text[:500]
                    }
                )
                
                qdrant_client.upsert(
                    collection_name="video_intelligence",
                    points=[point]
                )
            
            # Save analysis results
            analysis_file = analysis_dir / "analysis.json"
            with open(analysis_file, 'w') as f:
                json.dump(analysis_result, f, indent=2, default=str)
            
            analysis_result["completed_at"] = datetime.now().isoformat()
            analysis_result["analysis_file"] = str(analysis_file)
            
            return {
                "success": True,
                "video_id": video_id,
                "analysis": analysis_result
            }
            
        except Exception as e:
            logger.error(f"Error analyzing video: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def check_brand_compliance(request: ComplianceCheckRequest) -> Dict[str, Any]:
        """Check video for brand compliance"""
        try:
            # Load video analysis
            analysis_file = PROCESSED_DIR / request.video_id / "analysis.json"
            if not analysis_file.exists():
                return {"success": False, "error": f"Video analysis not found for ID: {request.video_id}"}
            
            with open(analysis_file, 'r') as f:
                video_data = json.load(f)
            
            # Perform compliance check
            compliance_report = CreativeAnalyzer.analyze_brand_compliance(
                video_data, 
                request.brand_guidelines
            )
            
            compliance_report["video_id"] = request.video_id
            compliance_report["checked_at"] = datetime.now().isoformat()
            compliance_report["check_areas"] = request.check_areas
            
            return {
                "success": True,
                "video_id": request.video_id,
                "compliance_report": compliance_report
            }
            
        except Exception as e:
            logger.error(f"Error checking compliance: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def search_videos(request: VideoSearchRequest) -> Dict[str, Any]:
        """Search through analyzed videos"""
        try:
            if request.search_type == "semantic":
                # Generate query embedding
                query_embedding = text_encoder.encode(request.query).tolist()
                
                # Search in Qdrant
                search_results = qdrant_client.search(
                    collection_name="video_intelligence",
                    query_vector=query_embedding,
                    limit=request.limit,
                    with_payload=True
                )
                
                results = []
                for result in search_results:
                    result_data = {
                        "video_id": result.payload.get("video_id"),
                        "video_name": result.payload.get("video_name"),
                        "score": result.score,
                        "duration": result.payload.get("duration"),
                        "created_at": result.payload.get("created_at"),
                        "content_summary": result.payload.get("content_summary", "")[:200]
                    }
                    results.append(result_data)
                
                return {
                    "success": True,
                    "query": request.query,
                    "search_type": request.search_type,
                    "results": results
                }
            
            else:
                return {"success": False, "error": f"Search type {request.search_type} not yet implemented"}
            
        except Exception as e:
            logger.error(f"Error searching videos: {e}")
            return {"success": False, "error": str(e)}

# API Endpoints
@app.get("/")
async def root():
    return {
        "service": "Video RAG MCP Server",
        "version": "1.0.0",
        "status": "running",
        "capabilities": [
            "Video content analysis and indexing",
            "Frame extraction and visual analysis",
            "Audio transcription and analysis",
            "Brand compliance checking",
            "Creative performance insights",
            "Multi-modal video search"
        ]
    }


@app.post("/auth/token")
async def login(username: str, password: str):
    """Authenticate and get access token"""
    # In production, verify against secure user store
    if username == os.getenv("MCP_ADMIN_USER", "admin") and password == os.getenv("MCP_ADMIN_PASS", "change-this"):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

@app.get("/health")
async def health():
    try:
        collections = qdrant_client.get_collections()
        
        # Count video records
        video_info = qdrant_client.get_collection("video_intelligence")
        video_count = video_info.points_count
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "videos_analyzed": video_count,
            "models_loaded": {
                "text_encoder": text_encoder is not None,
                "image_model": blip_model is not None
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@api_v1.post("/mcp/tools/analyze_video")
async def analyze_video(request: VideoAnalysisRequest, current_user: str = Depends(verify_token)):
    """Analyze video for content and insights"""
    return await MCPTools.analyze_video(request)

@api_v1.post("/mcp/tools/check_compliance")
async def check_compliance(request: ComplianceCheckRequest, current_user: str = Depends(verify_token)):
    """Check video for brand compliance"""
    return await MCPTools.check_brand_compliance(request)

@api_v1.post("/mcp/tools/search_videos")
async def search_videos(request: VideoSearchRequest, current_user: str = Depends(verify_token)):
    """Search through analyzed videos"""
    return await MCPTools.search_videos(request)

@api_v1.post("/mcp/tools/upload_video")
async def upload_video(
    file: UploadFile = File(...),
    analysis_type: str = "comprehensive",
    metadata: str = "{}"
, current_user: str = Depends(verify_token)):
    """Upload and analyze video"""
    try:
        # Save uploaded video
        video_path = VIDEOS_DIR / file.filename
        with open(video_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Analyze the video
        request = VideoAnalysisRequest(
            video_path=str(video_path),
            analysis_type=analysis_type,
            metadata=json.loads(metadata) if metadata != "{}" else {}
        )
        
        result = await MCPTools.analyze_video(request)
        
        return result
        
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        return {"success": False, "error": str(e)}


# Include API v1 router
app.include_router(api_v1)

if __name__ == "__main__":
    logger.info("Starting Video RAG MCP Server...")
    
    # Setup Qdrant
    setup_qdrant()
    
    logger.info(f"Data directory: {DATA_DIR}")
    logger.info(f"Videos directory: {VIDEOS_DIR}")
    logger.info("Server running at http://localhost:8008")
    
    uvicorn.run(app, host="0.0.0.0", port=8008)