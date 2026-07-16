"""
REST and WebSocket API Server for Nate AI Assistant.
"""

import os
import sys
import time
import threading
import asyncio
from typing import Optional, List
import torch

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from audio.recorder import AudioRecorder, RecordingConfig
from audio.vad import VoiceActivityDetector
from audio.latency import LatencyTracker
from stt.whisper_engine import WhisperEngine
from llm.gemini_client import GeminiClient
from tts.piper_engine import PiperEngine
from tts.player import TTSPlayer
from memory.manager import MemoryManager
from orchestrator.session import ConversationSession
from orchestrator.pipeline import Pipeline
from orchestrator.state import AssistantState
from orchestrator.events import (
    PipelineEvent,
    RecordingStoppedEvent,
    TranscriptionCompletedEvent,
    ResponseGeneratedEvent,
    SpeechSynthesizedEvent,
    SpeechPlaybackCompletedEvent,
    ThinkingStartedEvent,
    ThinkingFinishedEvent,
)
from utils.logger import setup_logger

logger = setup_logger("nate.api.server", level="INFO")

app = FastAPI(title="Nate AI Assistant API Server")

# Allow CORS for dev environments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
pipeline: Optional[Pipeline] = None
recorder: Optional[AudioRecorder] = None
tracker: Optional[LatencyTracker] = None
session: Optional[ConversationSession] = None
memory: Optional[MemoryManager] = None
piper: Optional[PiperEngine] = None
player: Optional[TTSPlayer] = None

connected_websockets: List[WebSocket] = []
recording_active = False
recording_thread: Optional[threading.Thread] = None


class MessageRequest(BaseModel):
    message: str


def broadcast_event(event_name: str, payload: dict) -> None:
    """Send JSON events to all connected WebSockets safely across threads."""
    message = {"event": event_name, **payload}
    
    # Try to schedule the WebSocket send on the running loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    for ws in list(connected_websockets):
        try:
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(ws.send_json(message), loop)
            else:
                loop.run_until_complete(ws.send_json(message))
        except Exception as exc:
            logger.debug("Failed to send WS message: %s", exc)


class SystemEventHandler:
    """Routes pipeline events directly to connected WebSocket clients."""
    
    def __call__(self, event: PipelineEvent) -> None:
        event_class = event.__class__.__name__
        payload = {}
        for k, v in event.__dict__.items():
            if isinstance(v, (str, int, float, bool)):
                payload[k] = v
            elif k in ("old_state", "new_state") and hasattr(v, "name"):
                payload[k] = v.name
        broadcast_event(event_class, payload)


@app.on_event("startup")
def startup_event() -> None:
    """Initialize system models and warm up the pipeline."""
    global pipeline, recorder, tracker, session, memory, piper, player
    
    logger.info("Initializing Nate backend models...")
    
    tracker = LatencyTracker()
    session = ConversationSession()
    memory = MemoryManager(default_limit=8)
    
    # Connect WebSocket Broadcaster to Event Listeners
    session.register_listener(SystemEventHandler())
    
    # Initialize hardware detectors
    vad = VoiceActivityDetector(
        threshold=config.VAD_THRESHOLD,
        silence_duration=config.SILENCE_DURATION
    )
    
    rec_config = RecordingConfig(
        sample_rate=config.SAMPLE_RATE,
        channels=config.CHANNELS,
        output_dir=os.path.join("assets", "recordings"),
        output_filename="api_session.wav"
    )
    
    recorder = AudioRecorder(
        recording_config=rec_config,
        vad=vad,
        latency_tracker=tracker
    )
    
    # Load model engines once
    whisper = WhisperEngine(latency_tracker=tracker)
    gemini = GeminiClient(latency_tracker=tracker)
    piper = PiperEngine(latency_tracker=tracker)
    piper.initialize()
    player = TTSPlayer(latency_tracker=tracker)
    
    pipeline = Pipeline(
        whisper_engine=whisper,
        gemini_client=gemini,
        session=session,
        latency_tracker=tracker,
        piper_engine=piper,
        tts_player=player,
        memory_manager=memory
    )
    logger.info("Nate API backend fully initialized.")


@app.on_event("shutdown")
def shutdown_event() -> None:
    """Clean up resources on server shutdown."""
    if piper:
        piper.shutdown()
    logger.info("Nate API backend shutdown complete.")


@app.post("/conversation/start")
def start_conversation():
    """Start or restart a conversation session (clears memory)."""
    global recording_active
    logger.info("REST: Starting new conversation.")
    
    if memory:
        memory.clear()
        
    if session:
        session.set_state(AssistantState.IDLE)
        session.clear_history()
        
    if recording_active:
        recording_active = False
        if recorder:
            recorder._stop_event.set()
            
    return {"status": "started", "state": session.state.name if session else "IDLE"}


@app.post("/conversation/stop")
def stop_conversation():
    """Interrupt current speech generation or playback."""
    global recording_active
    logger.info("REST: Stopping active conversation turn.")
    
    recording_active = False
    if recorder and recorder.is_recording:
        recorder._stop_event.set()
        
    if player:
        player.stop()
        
    if session:
        session.set_state(AssistantState.IDLE)
        
    return {"status": "stopped", "state": session.state.name if session else "IDLE"}


def run_voice_recording_loop() -> None:
    """Task loop to record and run a single turn of voice speech-to-speech."""
    global recording_active
    recording_active = True
    
    if not recorder or not pipeline or not session:
        recording_active = False
        return
        
    try:
        session.set_state(AssistantState.LISTENING)
        logger.info("Voice turn: Listening from microphone...")
        
        # Record until silence VAD trigger
        recording = recorder.record_until_silence(max_duration=15.0)
        
        if recording and recording_active:
            logger.info("Voice turn: Routing raw audio through Pipeline...")
            pipeline.process_audio(recording)
            
    except Exception as exc:
        logger.error("Error in background voice turn loop: %s", exc)
        session.set_state(AssistantState.ERROR)
    finally:
        recording_active = False
        session.set_state(AssistantState.IDLE)


@app.post("/conversation/record")
def record_turn():
    """Trigger the local voice turn recording task in the background."""
    global recording_thread, recording_active
    if recording_active:
        return {"status": "error", "message": "Voice recording task is already active."}
        
    recording_thread = threading.Thread(target=run_voice_recording_loop)
    recording_thread.daemon = True
    recording_thread.start()
    return {"status": "listening"}


@app.post("/conversation/message")
def text_message(req: MessageRequest):
    """Fallback text chat interface mapping directly to conversational pipeline."""
    if not pipeline or not memory or not session:
        return {"status": "error", "message": "System not fully initialized."}
        
    session.set_state(AssistantState.THINKING)
    
    # Store user turn
    memory.add_user_turn(req.message)
    
    # Start thinking
    thinking_start = time.time()
    session.emit(ThinkingStartedEvent(timestamp=thinking_start))
    
    try:
        # Get history turns and query Gemini
        history_contents = memory.get_history_for_gemini()
        response = pipeline.llm.generate_response(history_contents)
        memory.add_assistant_turn(response.text)
        
        # Stop thinking and notify completed response
        thinking_duration = (time.time() - thinking_start) * 1000.0
        session.emit(ThinkingFinishedEvent(timestamp=time.time(), duration_ms=thinking_duration))
        session.emit(ResponseGeneratedEvent(text=response.text, latency_ms=response.latency_ms))
        
        # Synthesize and play response
        if pipeline.piper:
            session.set_state(AssistantState.SPEAKING)
            wav_path = pipeline.piper.synthesize(response.text)
            session.emit(SpeechSynthesizedEvent(wav_path=wav_path, text=response.text, latency_ms=0.0))
            
            if pipeline.player:
                pipeline.player.play(wav_path, blocking=True)
                session.emit(SpeechPlaybackCompletedEvent(wav_path=wav_path, duration_ms=0.0))
                
        session.set_state(AssistantState.IDLE)
        return {
            "status": "success",
            "reply": response.text,
            "latency_ms": response.latency_ms,
            "prompt_tokens": response.prompt_tokens,
            "response_tokens": response.response_tokens
        }
    except Exception as exc:
        logger.error("Text message request failed: %s", exc)
        session.set_state(AssistantState.ERROR)
        return {"status": "error", "message": str(exc)}


@app.get("/conversation/history")
def get_history():
    """Retrieve formatted conversation history."""
    if not memory:
        return {"history": []}
    turns = []
    for turn in memory.get_all_turns():
        turns.append({
            "role": turn.role,
            "text": turn.text,
            "timestamp": turn.timestamp.isoformat()
        })
    return {"history": turns}


@app.get("/session/state")
def get_session_state():
    """Fetch current session state representation."""
    return {"state": session.state.name if session else "IDLE"}


@app.get("/diagnostics")
def get_diagnostics():
    """Fetch hardware and module properties."""
    return {
        "session_state": session.state.name if session else "IDLE",
        "whisper_model": pipeline.whisper.model_size if pipeline else "small",
        "cuda_status": "CUDA Available" if torch.cuda.is_available() else "CPU Mode",
        "gemini_model": pipeline.llm.model_name if pipeline else "gemini-flash-latest",
        "piper_voice": pipeline.piper.config.voice if pipeline and pipeline.piper else "en_US-joe-medium.onnx",
        "memory_size": memory.total_turns if memory else 0
    }


@app.get("/latency")
def get_latency():
    """Fetch profile records from the latency tracker."""
    stats = {}
    if tracker:
        for k, v in tracker._timers.items():
            stats[k] = v.elapsed_ms
    return {"latency": stats}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Client WebSocket interface for receiving real-time pipeline events."""
    await websocket.accept()
    connected_websockets.append(websocket)
    
    # Broadcast current state to new listener immediately
    await websocket.send_json({
        "event": "StateChangedEvent",
        "old_state": "IDLE",
        "new_state": session.state.name if session else "IDLE"
    })
    
    try:
        while True:
            # Idle wait block to keep connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_websockets.remove(websocket)
