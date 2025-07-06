#!/usr/bin/env python3
"""
Audio Analysis MCP Server - Call Centre QA
Advanced audio analysis system for call quality assessment, sentiment analysis, and performance insights
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
import librosa
import numpy as np
from scipy import signal
import soundfile as sf
import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import speech_recognition as sr
from textblob import TextBlob
import re
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64

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

app = FastAPI(title="Audio Analysis MCP Server")

from fastapi import APIRouter

# Create versioned router
api_v1 = APIRouter(prefix="/api/v1")

# Data directories
DATA_DIR = Path(__file__).parent.parent / "data"
AUDIO_DIR = DATA_DIR / "audio"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = DATA_DIR / "reports"
MODELS_DIR = DATA_DIR / "models"
LOGS_DIR = Path(__file__).parent.parent / "logs"

for dir_path in [DATA_DIR, AUDIO_DIR, PROCESSED_DIR, REPORTS_DIR, MODELS_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True)

# Initialize models and clients
text_encoder = SentenceTransformer('all-MiniLM-L6-v2')
qdrant_client = QdrantClient(":memory:")

# Pydantic models
class AudioAnalysisRequest(BaseModel):
    audio_path: str
    analysis_type: str = "comprehensive"  # comprehensive, quality_only, sentiment_only, transcription_only
    speaker_detection: bool = True
    language: str = "en-US"
    metadata: Optional[Dict[str, Any]] = {}

class CallQualityRequest(BaseModel):
    audio_id: str
    quality_metrics: List[str] = ["clarity", "volume", "background_noise", "interruptions", "pace"]
    agent_guidelines: Optional[Dict[str, Any]] = {}

class SentimentAnalysisRequest(BaseModel):
    audio_id: str
    analysis_segments: bool = True
    customer_satisfaction_focus: bool = True

class BatchAnalysisRequest(BaseModel):
    audio_paths: List[str]
    analysis_type: str = "quality_only"
    parallel_processing: bool = True

class AudioSearchRequest(BaseModel):
    query: str
    search_type: str = "semantic"  # semantic, keyword, sentiment, quality_score
    filters: Optional[Dict[str, Any]] = {}
    limit: int = 10

# Audio processing utilities
class AudioProcessor:
    @staticmethod
    def load_audio(file_path: str, target_sr: int = 16000) -> tuple:
        """Load audio file and return audio data and sample rate"""
        try:
            audio_data, sr = librosa.load(file_path, sr=target_sr)
            duration = len(audio_data) / sr
            return audio_data, sr, duration
        except Exception as e:
            logger.error(f"Error loading audio file {file_path}: {e}")
            return None, None, None
    
    @staticmethod
    def extract_features(audio_data: np.ndarray, sr: int) -> Dict[str, Any]:
        """Extract comprehensive audio features"""
        try:
            features = {}
            
            # Basic features
            features["duration"] = len(audio_data) / sr
            features["sample_rate"] = sr
            features["rms_energy"] = float(np.sqrt(np.mean(audio_data**2)))
            features["zero_crossing_rate"] = float(np.mean(librosa.feature.zero_crossing_rate(audio_data)[0]))
            
            # Spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=audio_data, sr=sr)[0]
            features["spectral_centroid_mean"] = float(np.mean(spectral_centroids))
            features["spectral_centroid_std"] = float(np.std(spectral_centroids))
            
            spectral_rolloff = librosa.feature.spectral_rolloff(y=audio_data, sr=sr)[0]
            features["spectral_rolloff_mean"] = float(np.mean(spectral_rolloff))
            
            # MFCCs
            mfccs = librosa.feature.mfcc(y=audio_data, sr=sr, n_mfcc=13)
            for i in range(13):
                features[f"mfcc_{i}_mean"] = float(np.mean(mfccs[i]))
                features[f"mfcc_{i}_std"] = float(np.std(mfccs[i]))
            
            # Chroma features
            chroma = librosa.feature.chroma_stft(y=audio_data, sr=sr)
            features["chroma_mean"] = float(np.mean(chroma))
            features["chroma_std"] = float(np.std(chroma))
            
            # Tempo
            tempo, _ = librosa.beat.beat_track(y=audio_data, sr=sr)
            features["tempo"] = float(tempo)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting audio features: {e}")
            return {}
    
    @staticmethod
    def detect_silence(audio_data: np.ndarray, sr: int, threshold: float = 0.01) -> Dict[str, Any]:
        """Detect silence segments in audio"""
        try:
            # Frame the audio
            frame_length = int(0.025 * sr)  # 25ms frames
            hop_length = int(0.01 * sr)    # 10ms hop
            
            # Calculate energy for each frame
            frames = librosa.util.frame(audio_data, frame_length=frame_length, hop_length=hop_length)
            energy = np.sum(frames**2, axis=0)
            
            # Detect silence
            silence_mask = energy < threshold
            
            # Convert to time segments
            times = librosa.frames_to_time(np.arange(len(energy)), sr=sr, hop_length=hop_length)
            
            silence_segments = []
            in_silence = False
            start_time = None
            
            for i, is_silent in enumerate(silence_mask):
                if is_silent and not in_silence:
                    in_silence = True
                    start_time = times[i]
                elif not is_silent and in_silence:
                    in_silence = False
                    if start_time is not None:
                        silence_segments.append({
                            "start": float(start_time),
                            "end": float(times[i]),
                            "duration": float(times[i] - start_time)
                        })
            
            total_silence = sum([seg["duration"] for seg in silence_segments])
            silence_percentage = (total_silence / (len(audio_data) / sr)) * 100
            
            return {
                "silence_segments": silence_segments,
                "total_silence_duration": total_silence,
                "silence_percentage": silence_percentage,
                "silence_count": len(silence_segments)
            }
            
        except Exception as e:
            logger.error(f"Error detecting silence: {e}")
            return {}

class SpeechProcessor:
    @staticmethod
    def transcribe_audio(file_path: str, language: str = "en-US") -> Dict[str, Any]:
        """Transcribe audio to text with confidence scores"""
        try:
            recognizer = sr.Recognizer()
            
            # Convert to WAV if needed
            if not file_path.endswith('.wav'):
                audio_data, sr_rate = librosa.load(file_path, sr=16000)
                wav_path = file_path.replace(Path(file_path).suffix, '.wav')
                sf.write(wav_path, audio_data, sr_rate)
                file_path = wav_path
            
            with sr.AudioFile(file_path) as source:
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio_data = recognizer.record(source)
            
            # Transcribe using Google Speech Recognition
            try:
                transcript = recognizer.recognize_google(audio_data, language=language, show_all=True)
                
                if transcript and "alternative" in transcript:
                    best_transcript = transcript["alternative"][0]["transcript"]
                    confidence = transcript["alternative"][0].get("confidence", 0.8)
                    
                    return {
                        "transcript": best_transcript,
                        "confidence": confidence,
                        "alternatives": transcript["alternative"][1:5],  # Top 5 alternatives
                        "language": language,
                        "word_count": len(best_transcript.split()),
                        "character_count": len(best_transcript)
                    }
                else:
                    return {"transcript": "", "confidence": 0.0, "error": "No speech detected"}
                    
            except sr.UnknownValueError:
                return {"transcript": "", "confidence": 0.0, "error": "Speech not understood"}
            except sr.RequestError as e:
                return {"transcript": "", "confidence": 0.0, "error": f"API error: {e}"}
                
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return {"transcript": "", "confidence": 0.0, "error": str(e)}
    
    @staticmethod
    def analyze_speech_patterns(transcript: str) -> Dict[str, Any]:
        """Analyze speech patterns and characteristics"""
        try:
            if not transcript:
                return {}
            
            words = transcript.split()
            sentences = transcript.split('.')
            
            # Basic metrics
            word_count = len(words)
            sentence_count = len([s for s in sentences if s.strip()])
            avg_words_per_sentence = word_count / max(sentence_count, 1)
            
            # Filler words analysis
            filler_words = ['um', 'uh', 'er', 'like', 'you know', 'basically', 'actually', 'literally']
            filler_count = sum([transcript.lower().count(filler) for filler in filler_words])
            filler_percentage = (filler_count / word_count) * 100 if word_count > 0 else 0
            
            # Repetition analysis
            word_freq = {}
            for word in words:
                word_lower = word.lower().strip('.,!?')
                word_freq[word_lower] = word_freq.get(word_lower, 0) + 1
            
            repeated_words = {word: count for word, count in word_freq.items() 
                            if count > 2 and len(word) > 3}
            
            # Question analysis
            question_count = transcript.count('?')
            question_percentage = (question_count / sentence_count) * 100 if sentence_count > 0 else 0
            
            # Interruption detection (basic)
            interruption_indicators = ['--', '...', '[inaudible]', '[unclear]']
            interruption_count = sum([transcript.count(indicator) for indicator in interruption_indicators])
            
            return {
                "word_count": word_count,
                "sentence_count": sentence_count,
                "avg_words_per_sentence": avg_words_per_sentence,
                "filler_word_count": filler_count,
                "filler_percentage": filler_percentage,
                "repeated_words": repeated_words,
                "question_count": question_count,
                "question_percentage": question_percentage,
                "interruption_count": interruption_count,
                "speech_complexity": "high" if avg_words_per_sentence > 15 else "medium" if avg_words_per_sentence > 8 else "low"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing speech patterns: {e}")
            return {}

class QualityAnalyzer:
    @staticmethod
    def analyze_call_quality(audio_data: np.ndarray, sr: int, transcript_data: Dict) -> Dict[str, Any]:
        """Comprehensive call quality analysis"""
        try:
            quality_report = {}
            
            # Audio quality metrics
            rms_energy = np.sqrt(np.mean(audio_data**2))
            snr_estimate = QualityAnalyzer._estimate_snr(audio_data, sr)
            clarity_score = QualityAnalyzer._calculate_clarity_score(audio_data, sr)
            
            quality_report["audio_quality"] = {
                "rms_energy": float(rms_energy),
                "signal_to_noise_ratio": snr_estimate,
                "clarity_score": clarity_score,
                "volume_level": "good" if 0.01 < rms_energy < 0.3 else "low" if rms_energy <= 0.01 else "high"
            }
            
            # Speech quality metrics
            speech_patterns = transcript_data.get("speech_patterns", {})
            
            quality_report["speech_quality"] = {
                "filler_word_usage": speech_patterns.get("filler_percentage", 0),
                "speech_clarity": "good" if speech_patterns.get("filler_percentage", 0) < 5 else "moderate" if speech_patterns.get("filler_percentage", 0) < 10 else "poor",
                "interruption_frequency": speech_patterns.get("interruption_count", 0),
                "question_engagement": speech_patterns.get("question_percentage", 0)
            }
            
            # Overall quality score
            audio_score = min(100, (clarity_score * 0.4 + (snr_estimate / 30) * 0.3 + (rms_energy * 100) * 0.3))
            speech_score = max(0, 100 - (speech_patterns.get("filler_percentage", 0) * 2))
            overall_score = (audio_score * 0.6 + speech_score * 0.4)
            
            quality_report["overall_score"] = overall_score
            quality_report["grade"] = QualityAnalyzer._score_to_grade(overall_score)
            
            # Recommendations
            recommendations = []
            if clarity_score < 60:
                recommendations.append("Improve microphone quality or positioning")
            if snr_estimate < 15:
                recommendations.append("Reduce background noise")
            if speech_patterns.get("filler_percentage", 0) > 8:
                recommendations.append("Practice reducing filler words")
            if speech_patterns.get("interruption_count", 0) > 3:
                recommendations.append("Improve conversation flow and listening")
            
            quality_report["recommendations"] = recommendations
            
            return quality_report
            
        except Exception as e:
            logger.error(f"Error analyzing call quality: {e}")
            return {}
    
    @staticmethod
    def _estimate_snr(audio_data: np.ndarray, sr: int) -> float:
        """Estimate signal-to-noise ratio"""
        try:
            # Simple SNR estimation using spectral subtraction
            frame_length = int(0.025 * sr)
            hop_length = int(0.01 * sr)
            
            stft = librosa.stft(audio_data, n_fft=frame_length, hop_length=hop_length)
            magnitude = np.abs(stft)
            
            # Estimate noise from quieter frames
            frame_energy = np.sum(magnitude**2, axis=0)
            noise_threshold = np.percentile(frame_energy, 20)
            noise_frames = magnitude[:, frame_energy < noise_threshold]
            
            if noise_frames.shape[1] > 0:
                noise_estimate = np.mean(noise_frames)
                signal_estimate = np.mean(magnitude)
                snr = 20 * np.log10(signal_estimate / (noise_estimate + 1e-10))
                return float(max(0, min(50, snr)))  # Clamp between 0-50 dB
            else:
                return 25.0  # Default reasonable SNR
                
        except Exception as e:
            logger.error(f"Error estimating SNR: {e}")
            return 20.0
    
    @staticmethod
    def _calculate_clarity_score(audio_data: np.ndarray, sr: int) -> float:
        """Calculate audio clarity score based on spectral characteristics"""
        try:
            # Calculate spectral features that correlate with clarity
            spectral_centroid = librosa.feature.spectral_centroid(y=audio_data, sr=sr)[0]
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=audio_data, sr=sr)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=audio_data, sr=sr)[0]
            
            # Normalize and combine features
            centroid_score = np.clip((np.mean(spectral_centroid) - 1000) / 3000, 0, 1) * 100
            bandwidth_score = np.clip(np.mean(spectral_bandwidth) / 4000, 0, 1) * 100
            rolloff_score = np.clip((np.mean(spectral_rolloff) - 2000) / 6000, 0, 1) * 100
            
            clarity_score = (centroid_score * 0.4 + bandwidth_score * 0.3 + rolloff_score * 0.3)
            return float(clarity_score)
            
        except Exception as e:
            logger.error(f"Error calculating clarity score: {e}")
            return 70.0
    
    @staticmethod
    def _score_to_grade(score: float) -> str:
        """Convert numeric score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

class SentimentAnalyzer:
    @staticmethod
    def analyze_sentiment(transcript: str, segment_analysis: bool = True) -> Dict[str, Any]:
        """Analyze sentiment and emotional tone"""
        try:
            if not transcript:
                return {"error": "No transcript provided"}
            
            # Overall sentiment
            blob = TextBlob(transcript)
            overall_sentiment = {
                "polarity": float(blob.sentiment.polarity),  # -1 to 1
                "subjectivity": float(blob.sentiment.subjectivity),  # 0 to 1
                "classification": SentimentAnalyzer._classify_sentiment(blob.sentiment.polarity)
            }
            
            result = {"overall_sentiment": overall_sentiment}
            
            # Segment analysis
            if segment_analysis:
                sentences = transcript.split('.')
                segment_sentiments = []
                
                for i, sentence in enumerate(sentences):
                    if sentence.strip():
                        sent_blob = TextBlob(sentence)
                        segment_sentiments.append({
                            "segment": i + 1,
                            "text": sentence.strip(),
                            "polarity": float(sent_blob.sentiment.polarity),
                            "subjectivity": float(sent_blob.sentiment.subjectivity),
                            "classification": SentimentAnalyzer._classify_sentiment(sent_blob.sentiment.polarity)
                        })
                
                result["segment_analysis"] = segment_sentiments
                
                # Sentiment trend
                polarities = [seg["polarity"] for seg in segment_sentiments]
                if len(polarities) > 1:
                    trend = "improving" if polarities[-1] > polarities[0] else "declining" if polarities[-1] < polarities[0] else "stable"
                    result["sentiment_trend"] = trend
            
            # Customer satisfaction indicators
            satisfaction_keywords = {
                "positive": ["thank", "great", "excellent", "satisfied", "happy", "pleased", "good", "helpful"],
                "negative": ["terrible", "awful", "disappointed", "frustrated", "angry", "poor", "bad", "unsatisfied"]
            }
            
            text_lower = transcript.lower()
            positive_count = sum([text_lower.count(word) for word in satisfaction_keywords["positive"]])
            negative_count = sum([text_lower.count(word) for word in satisfaction_keywords["negative"]])
            
            result["satisfaction_indicators"] = {
                "positive_keywords": positive_count,
                "negative_keywords": negative_count,
                "satisfaction_score": max(0, min(100, 50 + (positive_count - negative_count) * 10))
            }
            
            # Emotional indicators
            result["emotional_analysis"] = SentimentAnalyzer._analyze_emotions(transcript)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _classify_sentiment(polarity: float) -> str:
        """Classify sentiment based on polarity score"""
        if polarity > 0.1:
            return "positive"
        elif polarity < -0.1:
            return "negative"
        else:
            return "neutral"
    
    @staticmethod
    def _analyze_emotions(text: str) -> Dict[str, Any]:
        """Analyze emotional content in text"""
        try:
            emotion_patterns = {
                "joy": ["happy", "joy", "excited", "delighted", "pleased", "cheerful"],
                "anger": ["angry", "furious", "mad", "irritated", "annoyed", "frustrated"],
                "sadness": ["sad", "unhappy", "disappointed", "depressed", "upset"],
                "fear": ["afraid", "scared", "worried", "anxious", "nervous", "concerned"],
                "surprise": ["surprised", "amazed", "shocked", "astonished", "stunned"],
                "trust": ["trust", "confident", "reliable", "depend", "believe"]
            }
            
            text_lower = text.lower()
            emotion_scores = {}
            
            for emotion, keywords in emotion_patterns.items():
                score = sum([text_lower.count(keyword) for keyword in keywords])
                emotion_scores[emotion] = score
            
            # Normalize scores
            total_score = sum(emotion_scores.values())
            if total_score > 0:
                emotion_percentages = {emotion: (score / total_score) * 100 
                                    for emotion, score in emotion_scores.items()}
                dominant_emotion = max(emotion_percentages, key=emotion_percentages.get)
            else:
                emotion_percentages = {emotion: 0 for emotion in emotion_patterns.keys()}
                dominant_emotion = "neutral"
            
            return {
                "emotion_scores": emotion_scores,
                "emotion_percentages": emotion_percentages,
                "dominant_emotion": dominant_emotion
            }
            
        except Exception as e:
            logger.error(f"Error analyzing emotions: {e}")
            return {}

# Setup Qdrant collection
def setup_qdrant():
    """Initialize Qdrant collection for audio data"""
    try:
        collections = qdrant_client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if "audio_analysis" not in collection_names:
            qdrant_client.create_collection(
                collection_name="audio_analysis",
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            logger.info("Created audio analysis collection in Qdrant")
        else:
            logger.info("Audio analysis collection already exists")
            
    except Exception as e:
        logger.error(f"Error setting up Qdrant: {e}")

# MCP Tools
class MCPTools:
    @staticmethod
    async def analyze_audio(request: AudioAnalysisRequest) -> Dict[str, Any]:
        """Comprehensive audio analysis for call centre QA"""
        try:
            audio_path = Path(request.audio_path)
            if not audio_path.exists():
                return {"success": False, "error": f"Audio file not found: {audio_path}"}
            
            audio_id = hashlib.md5(f"{audio_path.name}{datetime.now().isoformat()}".encode()).hexdigest()
            logger.info(f"Starting audio analysis {audio_id} for: {audio_path.name}")
            
            # Create analysis directory
            analysis_dir = PROCESSED_DIR / audio_id
            analysis_dir.mkdir(exist_ok=True)
            
            analysis_result = {
                "audio_id": audio_id,
                "audio_path": str(audio_path),
                "analysis_type": request.analysis_type,
                "started_at": datetime.now().isoformat(),
                "metadata": request.metadata
            }
            
            # Load and process audio
            audio_data, sr, duration = AudioProcessor.load_audio(str(audio_path))
            if audio_data is None:
                return {"success": False, "error": "Failed to load audio file"}
            
            analysis_result["duration_seconds"] = duration
            analysis_result["sample_rate"] = sr
            
            # Extract audio features
            if request.analysis_type in ["comprehensive", "quality_only"]:
                features = AudioProcessor.extract_features(audio_data, sr)
                analysis_result["audio_features"] = features
                
                # Silence detection
                silence_analysis = AudioProcessor.detect_silence(audio_data, sr)
                analysis_result["silence_analysis"] = silence_analysis
            
            # Speech transcription
            if request.analysis_type in ["comprehensive", "transcription_only", "sentiment_only"]:
                transcript_data = SpeechProcessor.transcribe_audio(str(audio_path), request.language)
                analysis_result["transcription"] = transcript_data
                
                if transcript_data.get("transcript"):
                    speech_patterns = SpeechProcessor.analyze_speech_patterns(transcript_data["transcript"])
                    analysis_result["speech_patterns"] = speech_patterns
            
            # Quality analysis
            if request.analysis_type in ["comprehensive", "quality_only"]:
                quality_report = QualityAnalyzer.analyze_call_quality(
                    audio_data, sr, analysis_result.get("transcription", {})
                )
                analysis_result["quality_analysis"] = quality_report
            
            # Sentiment analysis
            if request.analysis_type in ["comprehensive", "sentiment_only"]:
                transcript = analysis_result.get("transcription", {}).get("transcript", "")
                if transcript:
                    sentiment_analysis = SentimentAnalyzer.analyze_sentiment(transcript, True)
                    analysis_result["sentiment_analysis"] = sentiment_analysis
            
            # Store in vector database
            if analysis_result.get("transcription", {}).get("transcript"):
                content_text = analysis_result["transcription"]["transcript"]
                embedding = text_encoder.encode(content_text).tolist()
                
                point = PointStruct(
                    id=audio_id,
                    vector=embedding,
                    payload={
                        "audio_id": audio_id,
                        "audio_name": audio_path.name,
                        "analysis_type": request.analysis_type,
                        "duration": duration,
                        "quality_score": analysis_result.get("quality_analysis", {}).get("overall_score", 0),
                        "sentiment_score": analysis_result.get("sentiment_analysis", {}).get("overall_sentiment", {}).get("polarity", 0),
                        "created_at": datetime.now().isoformat(),
                        "transcript_preview": content_text[:200]
                    }
                )
                
                qdrant_client.upsert(
                    collection_name="audio_analysis",
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
                "audio_id": audio_id,
                "analysis": analysis_result
            }
            
        except Exception as e:
            logger.error(f"Error analyzing audio: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def assess_call_quality(request: CallQualityRequest) -> Dict[str, Any]:
        """Assess call quality against specific metrics"""
        try:
            # Load audio analysis
            analysis_file = PROCESSED_DIR / request.audio_id / "analysis.json"
            if not analysis_file.exists():
                return {"success": False, "error": f"Audio analysis not found for ID: {request.audio_id}"}
            
            with open(analysis_file, 'r') as f:
                audio_data = json.load(f)
            
            quality_assessment = {
                "audio_id": request.audio_id,
                "assessed_at": datetime.now().isoformat(),
                "metrics_assessed": request.quality_metrics,
                "scores": {}
            }
            
            # Extract quality scores
            quality_analysis = audio_data.get("quality_analysis", {})
            
            for metric in request.quality_metrics:
                if metric == "clarity":
                    quality_assessment["scores"]["clarity"] = quality_analysis.get("audio_quality", {}).get("clarity_score", 0)
                elif metric == "volume":
                    volume_level = quality_analysis.get("audio_quality", {}).get("volume_level", "unknown")
                    volume_score = {"good": 85, "low": 40, "high": 60}.get(volume_level, 50)
                    quality_assessment["scores"]["volume"] = volume_score
                elif metric == "background_noise":
                    snr = quality_analysis.get("audio_quality", {}).get("signal_to_noise_ratio", 20)
                    noise_score = min(100, (snr / 30) * 100)
                    quality_assessment["scores"]["background_noise"] = noise_score
                elif metric == "interruptions":
                    interruption_count = audio_data.get("speech_patterns", {}).get("interruption_count", 0)
                    interruption_score = max(0, 100 - (interruption_count * 10))
                    quality_assessment["scores"]["interruptions"] = interruption_score
                elif metric == "pace":
                    words_per_minute = audio_data.get("transcription", {}).get("word_count", 0) / (audio_data.get("duration_seconds", 1) / 60)
                    pace_score = 100 if 120 <= words_per_minute <= 180 else max(0, 100 - abs(words_per_minute - 150) * 2)
                    quality_assessment["scores"]["pace"] = pace_score
            
            # Overall assessment
            avg_score = sum(quality_assessment["scores"].values()) / len(quality_assessment["scores"])
            quality_assessment["overall_score"] = avg_score
            quality_assessment["grade"] = QualityAnalyzer._score_to_grade(avg_score)
            
            # Recommendations based on agent guidelines
            recommendations = []
            if request.agent_guidelines:
                for metric, score in quality_assessment["scores"].items():
                    threshold = request.agent_guidelines.get(f"{metric}_threshold", 70)
                    if score < threshold:
                        recommendations.append(f"Improve {metric} - current score: {score:.1f}, target: {threshold}")
            
            quality_assessment["recommendations"] = recommendations
            
            return {
                "success": True,
                "audio_id": request.audio_id,
                "quality_assessment": quality_assessment
            }
            
        except Exception as e:
            logger.error(f"Error assessing call quality: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def analyze_sentiment(request: SentimentAnalysisRequest) -> Dict[str, Any]:
        """Analyze sentiment and customer satisfaction"""
        try:
            # Load audio analysis
            analysis_file = PROCESSED_DIR / request.audio_id / "analysis.json"
            if not analysis_file.exists():
                return {"success": False, "error": f"Audio analysis not found for ID: {request.audio_id}"}
            
            with open(analysis_file, 'r') as f:
                audio_data = json.load(f)
            
            transcript = audio_data.get("transcription", {}).get("transcript", "")
            if not transcript:
                return {"success": False, "error": "No transcript available for sentiment analysis"}
            
            # Perform sentiment analysis
            sentiment_result = SentimentAnalyzer.analyze_sentiment(transcript, request.analysis_segments)
            
            # Add customer satisfaction focus
            if request.customer_satisfaction_focus:
                satisfaction_analysis = MCPTools._analyze_customer_satisfaction(transcript, audio_data)
                sentiment_result["customer_satisfaction"] = satisfaction_analysis
            
            sentiment_result["audio_id"] = request.audio_id
            sentiment_result["analyzed_at"] = datetime.now().isoformat()
            
            return {
                "success": True,
                "audio_id": request.audio_id,
                "sentiment_analysis": sentiment_result
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _analyze_customer_satisfaction(transcript: str, audio_data: Dict) -> Dict[str, Any]:
        """Analyze customer satisfaction indicators"""
        try:
            satisfaction_indicators = {
                "resolution_keywords": ["solved", "resolved", "fixed", "worked", "helped", "thank you"],
                "escalation_keywords": ["manager", "supervisor", "escalate", "complaint", "unacceptable"],
                "emotion_keywords": {
                    "positive": ["happy", "satisfied", "pleased", "great", "excellent"],
                    "negative": ["frustrated", "angry", "disappointed", "upset", "terrible"]
                }
            }
            
            text_lower = transcript.lower()
            
            # Count satisfaction indicators
            resolution_count = sum([text_lower.count(word) for word in satisfaction_indicators["resolution_keywords"]])
            escalation_count = sum([text_lower.count(word) for word in satisfaction_indicators["escalation_keywords"]])
            
            positive_emotion_count = sum([text_lower.count(word) for word in satisfaction_indicators["emotion_keywords"]["positive"]])
            negative_emotion_count = sum([text_lower.count(word) for word in satisfaction_indicators["emotion_keywords"]["negative"]])
            
            # Calculate satisfaction score
            base_score = 50
            resolution_bonus = resolution_count * 10
            escalation_penalty = escalation_count * 15
            emotion_adjustment = (positive_emotion_count - negative_emotion_count) * 5
            
            # Factor in call quality
            quality_score = audio_data.get("quality_analysis", {}).get("overall_score", 70)
            quality_adjustment = (quality_score - 70) * 0.2
            
            satisfaction_score = max(0, min(100, base_score + resolution_bonus - escalation_penalty + emotion_adjustment + quality_adjustment))
            
            return {
                "satisfaction_score": satisfaction_score,
                "resolution_indicators": resolution_count,
                "escalation_indicators": escalation_count,
                "positive_emotions": positive_emotion_count,
                "negative_emotions": negative_emotion_count,
                "quality_impact": quality_adjustment,
                "satisfaction_level": "high" if satisfaction_score >= 80 else "medium" if satisfaction_score >= 60 else "low"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing customer satisfaction: {e}")
            return {}
    
    @staticmethod
    async def search_audio(request: AudioSearchRequest) -> Dict[str, Any]:
        """Search through analyzed audio files"""
        try:
            if request.search_type == "semantic":
                # Generate query embedding
                query_embedding = text_encoder.encode(request.query).tolist()
                
                # Search in Qdrant
                search_results = qdrant_client.search(
                    collection_name="audio_analysis",
                    query_vector=query_embedding,
                    limit=request.limit,
                    with_payload=True
                )
                
                results = []
                for result in search_results:
                    result_data = {
                        "audio_id": result.payload.get("audio_id"),
                        "audio_name": result.payload.get("audio_name"),
                        "score": result.score,
                        "duration": result.payload.get("duration"),
                        "quality_score": result.payload.get("quality_score"),
                        "sentiment_score": result.payload.get("sentiment_score"),
                        "created_at": result.payload.get("created_at"),
                        "transcript_preview": result.payload.get("transcript_preview", "")
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
            logger.error(f"Error searching audio: {e}")
            return {"success": False, "error": str(e)}

# API Endpoints
@app.get("/")
async def root():
    return {
        "service": "Audio Analysis MCP Server",
        "version": "1.0.0",
        "status": "running",
        "capabilities": [
            "Audio quality assessment and metrics",
            "Speech transcription and analysis",
            "Sentiment analysis and customer satisfaction",
            "Call centre QA automation",
            "Audio search and indexing",
            "Batch processing and reporting"
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
        
        # Count audio records
        audio_info = qdrant_client.get_collection("audio_analysis")
        audio_count = audio_info.points_count
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "audio_files_analyzed": audio_count,
            "models_loaded": {
                "text_encoder": text_encoder is not None,
                "speech_recognition": True  # Always available
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@api_v1.post("/mcp/tools/analyze_audio")
async def analyze_audio(request: AudioAnalysisRequest, current_user: str = Depends(verify_token)):
    """Analyze audio for quality, sentiment, and transcription"""
    return await MCPTools.analyze_audio(request)

@api_v1.post("/mcp/tools/assess_quality")
async def assess_quality(request: CallQualityRequest, current_user: str = Depends(verify_token)):
    """Assess call quality against specific metrics"""
    return await MCPTools.assess_call_quality(request)

@api_v1.post("/mcp/tools/analyze_sentiment")
async def analyze_sentiment(request: SentimentAnalysisRequest, current_user: str = Depends(verify_token)):
    """Analyze sentiment and customer satisfaction"""
    return await MCPTools.analyze_sentiment(request)

@api_v1.post("/mcp/tools/search_audio")
async def search_audio(request: AudioSearchRequest, current_user: str = Depends(verify_token)):
    """Search through analyzed audio files"""
    return await MCPTools.search_audio(request)

@api_v1.post("/mcp/tools/upload_audio")
async def upload_audio(
    file: UploadFile = File(...),
    analysis_type: str = "comprehensive",
    metadata: str = "{}"
, current_user: str = Depends(verify_token)):
    """Upload and analyze audio file"""
    try:
        # Save uploaded audio
        audio_path = AUDIO_DIR / file.filename
        with open(audio_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Analyze the audio
        request = AudioAnalysisRequest(
            audio_path=str(audio_path),
            analysis_type=analysis_type,
            metadata=json.loads(metadata) if metadata != "{}" else {}
        )
        
        result = await MCPTools.analyze_audio(request)
        
        return result
        
    except Exception as e:
        logger.error(f"Error uploading audio: {e}")
        return {"success": False, "error": str(e)}


# Include API v1 router
app.include_router(api_v1)

if __name__ == "__main__":
    logger.info("Starting Audio Analysis MCP Server...")
    
    # Setup Qdrant
    setup_qdrant()
    
    logger.info(f"Data directory: {DATA_DIR}")
    logger.info(f"Audio directory: {AUDIO_DIR}")
    logger.info("Server running at http://localhost:8009")
    
    uvicorn.run(app, host="0.0.0.0", port=8009)