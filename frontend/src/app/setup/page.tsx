'use client';

import React from 'react';
import { ArrowLeft, BookOpen, Terminal, ShieldAlert, Cpu, Layers, HelpCircle, FileText, Settings, Play } from 'lucide-react';
import Link from 'next/link';

export default function SetupPage() {
  return (
    <div className="h-screen max-h-screen bg-[#0B0B0D] text-[#F5F5F5] font-mono selection:bg-[#3B82F6]/30 selection:text-white p-6 md:p-12 overflow-y-auto">
      {/* Header Navigation */}
      <header className="max-w-4xl mx-auto flex items-center justify-between mb-12 border-b border-[#2A2E38] pb-6">
        <Link
          href="/"
          className="flex items-center gap-2 text-xs font-semibold text-[#9EA6B2] hover:text-[#3B82F6] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Assistant
        </Link>
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-[#3B82F6]" />
          <span className="text-xs font-bold uppercase tracking-wider text-[#9EA6B2]">Local Environment Setup</span>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-4xl mx-auto space-y-12">
        {/* Title Section */}
        <section className="space-y-4">
          <h1 className="text-2xl font-bold text-white tracking-tight">Run Nate on Your Machine</h1>
          <p className="text-sm text-[#9EA6B2] leading-relaxed max-w-2xl font-sans">
            Nate is built as a desktop-native voice assistant. Deep-learning speech models (Faster-Whisper STT, Piper TTS ONNX, and Silero VAD) are compute-intensive and require large RAM footprints that exceed standard cloud hosting limits (such as standard 512MB free-tier constraints). Additionally, a voice-to-voice workflow requires direct, low-latency access to your local microphone and speaker hardware. Therefore, the pipeline must run locally.
          </p>
        </section>

        {/* Prerequisites */}
        <section className="bg-[#111215] border border-[#2A2E38] rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-3">
            <Cpu className="w-5 h-5 text-[#3B82F6]" />
            <h2 className="text-sm uppercase font-bold tracking-wider text-white">1. System Prerequisites</h2>
          </div>
          <ul className="text-xs text-[#9EA6B2] space-y-2 list-disc pl-5 font-sans leading-relaxed">
            <li><strong className="text-[#F5F5F5] font-mono">Python 3.10+</strong>: Core programming language.</li>
            <li><strong className="text-[#F5F5F5] font-mono">Node.js 18+ & npm</strong>: Runtime to compile and serve the Next.js chat interface.</li>
            <li><strong className="text-[#F5F5F5] font-mono">Git</strong>: To clone the code repositories.</li>
            <li><strong className="text-[#F5F5F5] font-mono">Nvidia CUDA (Optional)</strong>: If you have an RTX GPU, ensure CUDA Toolkit 11.8+ is installed to accelerate speech recognition.</li>
          </ul>
        </section>

        {/* Quick Start Guide */}
        <section className="space-y-6">
          <div className="flex items-center gap-3">
            <Settings className="w-5 h-5 text-[#3B82F6]" />
            <h2 className="text-sm uppercase font-bold tracking-wider text-white">2. Installation Guide</h2>
          </div>

          <div className="space-y-6">
            {/* Step 2.1 */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-white">Step A: Clone the Repository</h3>
              <pre className="bg-[#181A1F] border border-[#2A2E38] p-4 rounded-lg overflow-x-auto text-[11px] text-[#60A5FA]">
{`git clone https://github.com/NoelNinanSheri1307/Nate.git
cd Nate`}
              </pre>
            </div>

            {/* Step 2.2 */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-white">Step B: Initialize Python Backend</h3>
              <p className="text-xs text-[#9EA6B2] font-sans">
                Create a virtual environment and install backend libraries (VAD, speech processing, and WebSocket layers):
              </p>
              <pre className="bg-[#181A1F] border border-[#2A2E38] p-4 rounded-lg overflow-x-auto text-[11px] text-[#60A5FA]">
{`python -m venv venv
# Activate the environment:
# Windows (PowerShell):
.\\venv\\Scripts\\Activate.ps1
# macOS/Linux:
source venv/bin/activate

# Install dependencies:
pip install -r requirements.txt
pip install openwakeword`}
              </pre>
            </div>

            {/* Step 2.3 */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-white">Step C: Setup Environment Configuration</h3>
              <p className="text-xs text-[#9EA6B2] font-sans">
                Create a <code className="text-white font-mono bg-[#20242C] px-1 py-0.5 rounded">.env</code> file in the root directory to store your Gemini API Key:
              </p>
              <pre className="bg-[#181A1F] border border-[#2A2E38] p-4 rounded-lg overflow-x-auto text-[11px] text-[#60A5FA]">
{`GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
WHISPER_MODEL=small`}
              </pre>
            </div>

            {/* Step 2.4 */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-white">Step D: Download local Piper TTS files</h3>
              <p className="text-xs text-[#9EA6B2] font-sans">
                Download the local voice synthesis binaries and place them under the <code className="text-white font-mono bg-[#20242C] px-1 py-0.5 rounded">models/piper/</code> directory. Your file hierarchy must look like:
              </p>
              <pre className="bg-[#181A1F] border border-[#2A2E38] p-4 rounded-lg overflow-x-auto text-[11px] text-[#9EA6B2]">
{`models/piper/
├── piper.exe                  # Local C++ Piper runtime
├── en_US-joe-medium.onnx      # Vocal character model
├── en_US-joe-medium.onnx.json # Vocal phoneme configurations
└── espeak-ng-data/            # Phoneme lookup database`}
              </pre>
            </div>

            {/* Step 2.5 */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-white">Step E: Initialize Frontend Node Packages</h3>
              <pre className="bg-[#181A1F] border border-[#2A2E38] p-4 rounded-lg overflow-x-auto text-[11px] text-[#60A5FA]">
{`cd frontend
npm install`}
              </pre>
            </div>
          </div>
        </section>

        {/* Execution Commands */}
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <Play className="w-5 h-5 text-[#3B82F6]" />
            <h2 className="text-sm uppercase font-bold tracking-wider text-white">3. Running the Experience</h2>
          </div>
          <p className="text-xs text-[#9EA6B2] font-sans">
            Start both endpoints in separate terminals from the project root directory:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-[#111215] border border-[#2A2E38] p-4 rounded-xl space-y-2">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">Terminal 1: Python API Backend</h4>
              <pre className="bg-[#181A1F] border border-[#2A2E38] p-3 rounded text-[10px] text-[#60A5FA]">
{`# Activate venv first
.\\venv\\Scripts\\Activate.ps1
uvicorn server:app --reload`}
              </pre>
            </div>
            <div className="bg-[#111215] border border-[#2A2E38] p-4 rounded-xl space-y-2">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">Terminal 2: React UI Client</h4>
              <pre className="bg-[#181A1F] border border-[#2A2E38] p-3 rounded text-[10px] text-[#60A5FA]">
{`cd frontend
npm run dev`}
              </pre>
            </div>
          </div>
          <p className="text-[10px] text-[#9EA6B2] italic font-sans">
            Once running, open http://localhost:3000 in your browser. Turn on the "Wake Word" header switch, say "Hey Jarvis" or "Hey Mycroft", and speak.
          </p>
        </section>

        {/* Pipeline Architecture */}
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <Layers className="w-5 h-5 text-[#3B82F6]" />
            <h2 className="text-sm uppercase font-bold tracking-wider text-white">4. Pipeline Architecture</h2>
          </div>
          <div className="bg-[#111215] border border-[#2A2E38] p-6 rounded-xl space-y-4 font-sans text-xs text-[#9EA6B2]">
            <p className="leading-relaxed">
              Nate uses a fully pipelined, asynchronous architecture to overlap networking latency with deep learning synthesis.
            </p>
            <div className="bg-[#181A1F] p-4 rounded-lg text-center border border-[#2A2E38] font-mono text-[10px] text-[#60A5FA] overflow-x-auto whitespace-nowrap">
              Microphone → Silero VAD → Faster-Whisper (STT) → Memory State → Gemini 2.5 Flash → Sentence Splitting → Piper TTS → Speaker
            </div>
            <ul className="list-disc pl-5 space-y-2 leading-relaxed">
              <li><strong>Zero-Gap VAD</strong>: Keeps the device stream active. VAD checks speech probabilities in parallel.</li>
              <li><strong>Model Warm-Up</strong>: ONNX engines are loaded into RAM once during startup, ensuring subsequent speech synthesis completes in under 200ms.</li>
              <li><strong>Sentence Splitting</strong>: Text chunks emitted by the Gemini Stream are split into sentences on punctuation marks, allowing synthesis to play speech while the rest of the text is still generating.</li>
            </ul>
          </div>
        </section>

        {/* FAQ Section */}
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <HelpCircle className="w-5 h-5 text-[#3B82F6]" />
            <h2 className="text-sm uppercase font-bold tracking-wider text-white">5. Troubleshooting & FAQ</h2>
          </div>
          <div className="space-y-4">
            <div className="border-l-2 border-[#3B82F6] pl-4 space-y-1">
              <h4 className="text-xs font-bold text-white">Q: I get "Port already in use" errors during backend startup?</h4>
              <p className="text-xs text-[#9EA6B2] font-sans leading-relaxed">
                A: Another uvicorn or local process is bound to port 8000. Run <code className="text-white bg-[#181A1F] px-1 py-0.5 rounded font-mono">netstat -ano | findstr 8000</code> to find the PID, and kill the process.
              </p>
            </div>
            <div className="border-l-2 border-[#3B82F6] pl-4 space-y-1">
              <h4 className="text-xs font-bold text-white">Q: Can I run speech synthesis on AMD / CPU?</h4>
              <p className="text-xs text-[#9EA6B2] font-sans leading-relaxed">
                A: Yes. Piper TTS is optimized to execute on CPU. Faster-Whisper will automatically select CPU mode (`int8` execution) if CUDA-compatible Nvidia drivers are not detected.
              </p>
            </div>
            <div className="border-l-2 border-[#3B82F6] pl-4 space-y-1">
              <h4 className="text-xs font-bold text-white">Q: The wake word is not responding?</h4>
              <p className="text-xs text-[#9EA6B2] font-sans leading-relaxed">
                A: Make sure the package <code className="text-white bg-[#181A1F] px-1 py-0.5 rounded font-mono">openwakeword</code> is installed inside your active Python environment. Ensure your default input microphone is connected and unmuted.
              </p>
            </div>
          </div>
        </section>

        {/* External Resources */}
        <section className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 pt-6 border-t border-[#2A2E38]">
          <a
            href="https://github.com/NoelNinanSheri1307/Nate"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between p-4 bg-[#111215] border border-[#2A2E38] hover:border-[#3B82F6] rounded-xl group transition-all cursor-pointer"
          >
            <div className="space-y-1">
              <h4 className="text-xs font-bold text-white group-hover:text-[#60A5FA]">GitHub Code</h4>
              <p className="text-[10px] text-[#9EA6B2]">Repository & Issues</p>
            </div>
            <FileText className="w-4 h-4 text-[#9EA6B2]" />
          </a>

          <a
            href="https://github.com/NoelNinanSheri1307/Nate/blob/main/README.md"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between p-4 bg-[#111215] border border-[#2A2E38] hover:border-[#3B82F6] rounded-xl group transition-all cursor-pointer"
          >
            <div className="space-y-1">
              <h4 className="text-xs font-bold text-white group-hover:text-[#60A5FA]">Docs (README)</h4>
              <p className="text-[10px] text-[#9EA6B2]">Architecture & Details</p>
            </div>
            <BookOpen className="w-4 h-4 text-[#9EA6B2]" />
          </a>

          <a
            href="https://github.com/NoelNinanSheri1307/Nate/releases/tag/v1.0.0"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between p-4 bg-[#111215] border border-[#2A2E38] hover:border-[#3B82F6] rounded-xl group transition-all cursor-pointer"
          >
            <div className="space-y-1">
              <h4 className="text-xs font-bold text-white group-hover:text-[#60A5FA]">Latest Release</h4>
              <p className="text-[10px] text-[#9EA6B2]">Binaries & Downloads</p>
            </div>
            <ShieldAlert className="w-4 h-4 text-[#9EA6B2]" />
          </a>

          <Link
            href="/"
            className="flex items-center justify-between p-4 bg-[#111215] border border-[#2A2E38] hover:border-[#3B82F6] rounded-xl group transition-all cursor-pointer"
          >
            <div className="space-y-1">
              <h4 className="text-xs font-bold text-white group-hover:text-[#60A5FA]">Back to App</h4>
              <p className="text-[10px] text-[#9EA6B2]">Showcase Interface</p>
            </div>
            <ArrowLeft className="w-4 h-4 text-[#9EA6B2]" />
          </Link>
        </section>
      </main>
    </div>
  );
}
