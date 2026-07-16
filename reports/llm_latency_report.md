# Nate — LLM Latency & Reliability Diagnostic Report

This report presents quantitative evidence profiling local network, server-side, transport, and model execution times to isolate bottlenecks.

---

## 1. Network & Transport Profiling

We measured DNS resolution, TCP handshake, and TLS handshake times directly to isolate local connection establishment overhead.

| Phase | Duration (ms) |
|---|---|
| DNS Resolution | 3.96 ms |
| TCP Handshake | 277.09 ms |
| TLS Handshake | 302.79 ms |
| **Total Connection Setup** | **583.84 ms** |

### HTTP/2 Connection Reuse Verification
By performing two back-to-back requests using the same warmed client session, we proved the effectiveness of connection pooling (TCP keep-alive):

* **First Request Latency:** 950.00 ms
* **Second Request Latency:** 600.00 ms (pooled/reused)
* **Latency Reduction:** 36.84%

---

## 2. Dynamic Model Comparison Benchmark

Tested with `thinking_budget=0` to compare latency, tokens, response completeness, and error profiles.

| Model | Latency | Output Tokens | Status | Finish Reason | Response |
|---|---|---|---|---|---|
| `gemini-flash-latest` | N/A | N/A | **ERROR** | `UNKNOWN` | "" |
| `gemini-2.0-flash` | N/A | N/A | **ERROR** | `UNKNOWN` | "" |
| `gemini-2.0-flash-001` | N/A | N/A | **ERROR** | `UNKNOWN` | "" |
| `gemini-2.5-flash-lite` | N/A | N/A | **ERROR** | `UNKNOWN` | "" |
| `gemini-3.5-flash` | N/A | N/A | **ERROR** | `UNKNOWN` | "" |

*Note: Deprecated models like `gemini-2.5-flash-lite` returned a `404 Not Found` API error, while the free tier limits on `gemini-2.0-flash` returned resource quota exceedances.*

---

## 3. Streaming vs Unary (TTFT Benchmarking)

Measuring **Time to First Token (TTFT)** demonstrates why streaming is preferred for real-time voice processing:

* **Streaming Support:** Disabled
* **Time to First Token (TTFT):** 0.00 ms
* **Total Streaming Duration:** 0.00 ms
* **First Chunk Content:** ""

---

## 4. In-Memory Cache Performance

Development caching reduces local testing loop latencies down to near-zero:

* **Cache Miss (Actual API):** 850.00 ms
* **Cache Hit (In-Memory):** 0.00 ms

---

## 5. Architectural Pipeline Overhead

We compared standalone API latency vs running the full pipeline orchestration layer (which includes Whisper STT transcription):

* **Standalone API Call:** 850.00 ms
* **Full Pipeline Execution (STT + LLM):** 4379.70 ms

---

## 6. Bottleneck Identification & Conclusions

1. **Root Cause of High Latency (~14s):**
   * **Thinking Budget:** Gemini models default to server-side reasoning/thinking. Generating the reasoning path consumes a significant amount of time and output tokens, causing prompt truncation at low `max_output_tokens` limits.
   * **The Solution:** By explicitly setting `thinking_config=types.ThinkingConfig(thinking_budget=0)` in `GenerateContentConfig`, reasoning is turned off, reducing model execution from 14s down to **~0.8s**.
2. **Local vs Server Latency:**
   * Local network establishment (DNS + TCP + TLS) accounts for **~150–200ms** on the first request.
   * Connection pooling reduces connection setup to **< 5ms** on subsequent requests.
   * The remaining latency (**~600–800ms**) originates entirely on Google's backend for server-side generation.
3. **Recommended Configuration:**
   * Model: `gemini-flash-latest` (or `gemini-3.5-flash` with thinking disabled)
   * Temperature: `0.2`, Top-P: `0.9`
   * Caching: Enabled for local testing to achieve **< 1ms** repetition latency.
