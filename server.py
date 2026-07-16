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
from tts.sentence_splitter import StreamingSentenceBuffer
from memory.manager import MemoryManager
from orchestrator.session import ConversationSession
from orchestrator.pipeline import Pipeline, TTSQueue
from orchestrator.state import AssistantState
from orchestrator.events import (
    PipelineEvent,
    RecordingStoppedEvent,
    TranscriptionCompletedEvent,
    ResponseGeneratedEvent,
    ResponseChunkEvent,
    SpeechSynthesizedEvent,
    SpeechPlaybackCompletedEvent,
    ThinkingStartedEvent,
    ThinkingFinishedEvent,
    WakeWordDetectedEvent,
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
wake_word_detector = None  # Will be set if openwakeword is available

connected_websockets: List[WebSocket] = []
recording_active = False
recording_thread: Optional[threading.Thread] = None
wake_word_active = False
wake_word_thread: Optional[threading.Thread] = None


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
    
    # Initialize wake word detector
    _init_wake_word()
    
    logger.info("Nate API backend fully initialized.")


def _init_wake_word() -> None:
    """Try to initialize OpenWakeWord for 'Hey Nate' detection."""
    global wake_word_detector
    try:
        from wakeword.detector import WakeWordDetector
        wake_word_detector = WakeWordDetector()
        logger.info("Wake word detector initialized.")
    except ImportError:
        logger.warning("OpenWakeWord not installed. Wake word detection disabled. Run: pip install openwakeword")
    except Exception as exc:
        logger.warning("Wake word initialization failed: %s", exc)


@app.on_event("shutdown")
def shutdown_event() -> None:
    """Clean up resources on server shutdown."""
    global wake_word_active
    wake_word_active = False
    if wake_word_detector:
        try:
            wake_word_detector.stop()
        except Exception:
            pass
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

    # Interrupt streaming pipeline
    if pipeline:
        pipeline.interrupt()
        
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
        if session.state != AssistantState.IDLE:
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
    """Text chat interface with streaming LLM and streaming TTS."""
    if not pipeline or not memory or not session:
        return {"status": "error", "message": "System not fully initialized."}
        
    session.set_state(AssistantState.THINKING)
    
    # Store user turn
    memory.add_user_turn(req.message)
    
    # Start thinking
    thinking_start = time.time()
    session.emit(ThinkingStartedEvent(timestamp=thinking_start))
    
    try:
        # Get history turns and use streaming Gemini
        history_contents = memory.get_history_for_gemini()
        
        # Start TTS queue worker
        tts_queue = None
        if pipeline.piper and pipeline.player:
            tts_queue = TTSQueue(pipeline.piper, pipeline.player, session)
            tts_queue.start()
        
        sentence_buffer = StreamingSentenceBuffer()
        accumulated_text = ""
        first_chunk = True
        
        for chunk_text in pipeline.llm.generate_response_stream(history_contents):
            accumulated_text += chunk_text
            
            if first_chunk:
                session.set_state(AssistantState.STREAMING)
                first_chunk = False
            
            # Emit chunk for frontend
            session.emit(ResponseChunkEvent(chunk=chunk_text, accumulated=accumulated_text))
            
            # Feed to TTS sentence buffer
            if tts_queue:
                sentences = sentence_buffer.feed(chunk_text)
                for sentence in sentences:
                    tts_queue.enqueue(sentence)
        
        # Flush remaining
        if tts_queue:
            remaining = sentence_buffer.flush()
            for sentence in remaining:
                tts_queue.enqueue(sentence)
        
        # Get final response
        response = pipeline.llm.last_stream_result
        if response is None:
            response_text = accumulated_text.strip()
            latency_ms = (time.time() - thinking_start) * 1000.0
        else:
            response_text = response.text
            latency_ms = response.latency_ms
        
        memory.add_assistant_turn(response_text)
        
        # Stop thinking
        thinking_duration = (time.time() - thinking_start) * 1000.0
        session.emit(ThinkingFinishedEvent(timestamp=time.time(), duration_ms=thinking_duration))
        session.emit(ResponseGeneratedEvent(text=response_text, latency_ms=latency_ms))
        
        # Wait for TTS to finish
        if tts_queue:
            tts_queue.finish()
            session.emit(SpeechPlaybackCompletedEvent(wav_path="", duration_ms=0.0))
                
        session.set_state(AssistantState.IDLE)
        return {
            "status": "success",
            "reply": response_text,
            "latency_ms": latency_ms,
            "prompt_tokens": response.prompt_tokens if response else 0,
            "response_tokens": response.response_tokens if response else 0
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
    ww_status = "Active" if wake_word_active else ("Available" if wake_word_detector else "Unavailable")
    return {
        "session_state": session.state.name if session else "IDLE",
        "whisper_model": pipeline.whisper.model_size if pipeline else "small",
        "cuda_status": "CUDA Available" if torch.cuda.is_available() else "CPU Mode",
        "gemini_model": pipeline.llm.model_name if pipeline else "gemini-flash-latest",
        "piper_voice": pipeline.piper.config.voice if pipeline and pipeline.piper else "en_US-joe-medium.onnx",
        "memory_size": memory.total_turns if memory else 0,
        "wake_word": ww_status,
        "streaming": True
    }


@app.get("/latency")
def get_latency():
    """Fetch profile records from the latency tracker."""
    stats = {}
    if tracker:
        for k, v in tracker._timers.items():
            stats[k] = v.elapsed_ms
    return {"latency": stats}


# ─── Wake Word Endpoints ─────────────────────────────────────────────────────

@app.post("/wakeword/start")
def start_wake_word():
    """Start wake word detection loop."""
    global wake_word_active, wake_word_thread
    
    if not wake_word_detector:
        return {"status": "error", "message": "Wake word detector not available."}
    
    if wake_word_active:
        return {"status": "already_active"}
    
    # Start the continuous background audio stream
    try:
        wake_word_detector.start()
    except Exception as exc:
        return {"status": "error", "message": f"Failed to start audio stream: {exc}"}
        
    wake_word_active = True
    wake_word_thread = threading.Thread(target=_wake_word_loop, daemon=True)
    wake_word_thread.start()
    
    if session:
        session.set_state(AssistantState.WAKE_LISTENING)
    
    return {"status": "started"}


@app.post("/wakeword/stop")
def stop_wake_word():
    """Stop wake word detection."""
    global wake_word_active
    wake_word_active = False
    
    if wake_word_detector:
        try:
            wake_word_detector.stop()
        except Exception as exc:
            logger.error("Error stopping wake word detector: %s", exc)
        
    if session and session.state == AssistantState.WAKE_LISTENING:
        session.set_state(AssistantState.IDLE)
    
    return {"status": "stopped"}


def _wake_word_loop() -> None:
    """Background loop for wake word detection."""
    global wake_word_active
    
    if not wake_word_detector or not session:
        wake_word_active = False
        return
    
    logger.info("Wake word detection started. Listening for 'Hey Nate'...")
    
    try:
        while wake_word_active:
            # Only listen when idle or wake_listening
            if session.state not in (AssistantState.IDLE, AssistantState.WAKE_LISTENING):
                import time as _time
                _time.sleep(0.1)
                continue
            
            result = wake_word_detector.listen_once(timeout=0.5)
            
            if result and wake_word_active:
                logger.info("Wake word detected: '%s' (confidence=%.2f)", result.keyword, result.confidence)
                session.emit(WakeWordDetectedEvent(keyword=result.keyword, confidence=result.confidence))
                
                # Stop the wake word stream to release the mic device for AudioRecorder
                try:
                    wake_word_detector.stop()
                except Exception as exc:
                    logger.error("Failed to stop detector for recording: %s", exc)

                # Trigger conversation flow
                session.set_state(AssistantState.IDLE)
                run_voice_recording_loop()
                
                # Check if we should resume listening
                if wake_word_active:
                    try:
                        wake_word_detector.start()
                        session.set_state(AssistantState.WAKE_LISTENING)
                    except Exception as exc:
                        logger.error("Failed to restart detector: %s", exc)
                        wake_word_active = False
                        session.set_state(AssistantState.IDLE)
                
    except Exception as exc:
        logger.error("Wake word loop error: %s", exc)
    finally:
        wake_word_active = False
        try:
            wake_word_detector.stop()
        except Exception:
            pass
        logger.info("Wake word detection stopped.")


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
