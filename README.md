# Nate — Real-Time Conversational AI Assistant

> Audio-In, Audio-Out conversational AI with sub-two-second end-to-end latency.

---

## Overview

**Nate** is a production-quality, real-time conversational AI assistant that listens through your microphone, understands your speech, generates intelligent responses via a large language model, and speaks back — all with a target latency of under two seconds.

Built as a modular Python application, Nate demonstrates professional software engineering practices including clean architecture, comprehensive logging, and scalable module design.

---

## Objectives

- Build a fully functional voice-to-voice AI assistant pipeline
- Achieve end-to-end latency under two seconds
- Maintain production-quality code with modular, extensible architecture
- Handle edge cases gracefully with intelligent fallback dialogue
- Demonstrate real-world AI engineering skills

---

## Features

### Planned

- **Real-time microphone capture** — Continuous audio input via `sounddevice`
- **Voice Activity Detection** — Intelligent speech endpoint detection using Silero VAD
- **Speech-to-Text** — Fast, accurate transcription with Faster Whisper
- **LLM Integration** — Contextual responses powered by Gemini 2.5 Flash
- **Text-to-Speech** — Natural voice synthesis using Piper TTS
- **Low Latency** — Optimized pipeline targeting < 2 second response time
- **Fallback Dialogue** — Graceful handling of processing delays
- **Structured Logging** — Colored console output with file logging support

### Current (Phase 1)

- Project structure and module scaffolding
- Configuration management with environment variable loading
- Dependency verification utility
- Audio device detection
- Reusable logging system

---

## Architecture Overview

```
Microphone → VAD → STT (Faster Whisper) → LLM (Gemini 2.5 Flash) → TTS (Piper) → Speaker
```

Each stage of the pipeline is encapsulated in its own module, enabling independent development, testing, and replacement of components.

---

## Technology Stack

| Component              | Technology            |
|------------------------|-----------------------|
| Language               | Python 3.11+          |
| Async Runtime          | asyncio, threading    |
| Voice Activity Detection | Silero VAD          |
| Speech Recognition     | Faster Whisper        |
| Language Model         | Gemini 2.5 Flash API  |
| Text-to-Speech         | Piper TTS             |
| Audio I/O              | sounddevice, soundfile|
| Configuration          | python-dotenv         |
| Logging                | Python logging module |
| Version Control        | Git                   |

---

## Folder Structure

```
Nate/
│
├── app.py                  # Application entry point
├── config.py               # Configuration and environment loading
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── .gitignore              # Git ignore rules
├── .env.example            # Environment variable template
│
├── audio/                  # Audio capture and playback
│   └── __init__.py
│
├── stt/                    # Speech-to-text (Faster Whisper)
│   └── __init__.py
│
├── llm/                    # LLM integration (Gemini)
│   └── __init__.py
│
├── tts/                    # Text-to-speech (Piper)
│   └── __init__.py
│
├── conversation/           # Conversation state management
│   └── __init__.py
│
├── utils/                  # Shared utilities
│   ├── __init__.py
│   ├── logger.py           # Logging configuration
│   └── verify.py           # Dependency verification
│
├── assets/                 # Static assets
├── logs/                   # Runtime log files
├── models/                 # Downloaded model files
└── tests/                  # Unit and integration tests
```

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/Nate.git
cd Nate
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

**Activate the environment:**

- **Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Windows (CMD):**
  ```cmd
  venv\Scripts\activate.bat
  ```
- **macOS / Linux:**
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and add your API key:

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:

```
GEMINI_API_KEY=your_api_key_here
```

### 5. Run the Verification Script

```bash
python app.py
```

This will:
- Display the Nate startup banner
- Validate your configuration
- Check that all required libraries are installed
- Detect available audio devices
- Report any issues

You can also run verification standalone:

```bash
python -m utils.verify
```

---

## Current Development Phase

### Phase 1 — Project Initialization & Environment Setup (Complete)

- Project structure created
- Configuration management implemented
- Logging utility built
- Dependency verification tool complete
- README and documentation written

---

## Roadmap

| Phase | Description                                    | Status      |
|-------|------------------------------------------------|-------------|
| 1     | Project initialization & environment setup     | Complete    |
| 2     | Audio capture & Voice Activity Detection       | Planned     |
| 3     | Speech-to-Text integration (Faster Whisper)    | Planned     |
| 4     | LLM integration (Gemini 2.5 Flash)            | Planned     |
| 5     | Text-to-Speech integration (Piper)            | Planned     |
| 6     | Full pipeline assembly & latency optimization  | Planned     |
| 7     | Fallback dialogue & error handling             | Planned     |
| 8     | Testing, polish & documentation                | Planned     |

---

## License

This project is part of an AI Engineering internship assignment.  
License to be determined.

---

<p align="center">
  Built with Python
</p>
