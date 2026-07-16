"""
Gemini Client module using the new google-genai SDK.

Handles connection, settings, timeouts, retries, and latency tracking.
"""

import time
import logging
from typing import Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError

import config
from llm.exceptions import LLMError, LLMConnectionError, LLMTimeoutError, LLMConfigurationError
from llm.models import LLMConfig
from llm.response import AssistantResponse
from llm.prompts import SYSTEM_PROMPT
from audio.latency import LatencyTracker
from utils.logger import setup_logger

logger = setup_logger("nate.llm.gemini")


class GeminiClient:
    """Client wrapper for Gemini 2.5 Flash API."""

    def __init__(
        self,
        llm_config: Optional[LLMConfig] = None,
        latency_tracker: Optional[LatencyTracker] = None,
    ) -> None:
        self.config = llm_config or LLMConfig()
        self.tracker = latency_tracker

        if not config.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is not set in config.")
            raise LLMConfigurationError("GEMINI_API_KEY environment variable is missing.")

        # Initialize the new google-genai Client once (warm initialization)
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        
        # Verify and select the active model using fallback order
        self.model_name = self._select_model()
        
        # Setup caching for development and benchmarking
        self._cache = {}
        self.enable_cache = getattr(config, "ENABLE_LLM_CACHE", False)
        
        logger.info("GeminiClient initialized with active model: %s (cache: %s)", 
                    self.model_name, "enabled" if self.enable_cache else "disabled")

    def _select_model(self) -> str:
        """Selects and verifies the best available model.

        Reads GEMINI_MODEL (fallback to config.LLM_MODEL).
        Queries available models from the API to verify existence.
        Falls back to the list of verified models if preferred is not found.
        """
        fallback_order = [
            "gemini-3.1-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-flash-latest",
            "gemini-2.0-flash",
            "gemini-2.0-flash-001",
            "gemini-2.5-flash-lite",
            "gemini-3.5-flash"
        ]

        import os
        preferred = os.getenv("GEMINI_MODEL", self.config.model_name)
        
        # Clean models/ prefix if present
        if preferred and preferred.startswith("models/"):
            preferred = preferred.replace("models/", "")

        try:
            api_models = [m.name.replace("models/", "") for m in self.client.models.list()]
            logger.debug("Available Gemini models: %s", api_models)
        except Exception as exc:
            logger.warning("Could not list available Gemini models: %s. Using preferred model without verification.", exc)
            return preferred or fallback_order[0]

        # Verify preferred model
        if preferred in api_models:
            logger.info("Selected Gemini model: %s", preferred)
            return preferred

        # Fallback verification loop
        for model in fallback_order:
            if model in api_models:
                logger.info("Preferred model '%s' not available. Falling back to: %s", preferred, model)
                return model

        logger.warning("Preferred model and fallback models not verified. Defaulting to first fallback: %s", fallback_order[0])
        return fallback_order[0]

    def _extract_response_text(self, response) -> str:
        """Defensively extract text from all parts of all candidates in the response."""
        if not response:
            return ""

        parts_text = []

        # 1. Inspect candidates and parts
        if hasattr(response, "candidates") and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, "content") and candidate.content:
                    if hasattr(candidate.content, "parts") and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, "text") and part.text:
                                parts_text.append(part.text)

        # 2. Fallback to response.text if no parts text could be extracted
        text = "".join(parts_text).strip()
        if not text and hasattr(response, "text") and response.text:
            text = response.text.strip()

        return text

    def generate_response(self, prompt: str | list[types.Content]) -> AssistantResponse:
        """Generate response from Gemini with retry logic and detailed latency measurement.

        Args:
            prompt: User input transcript string or list of Content objects.

        Returns:
            AssistantResponse dataclass.
        """
        # Validate prompt input safely
        if isinstance(prompt, str):
            if not prompt or not prompt.strip():
                logger.warning("Empty prompt received. Returning empty response.")
                return AssistantResponse(text="", prompt_tokens=0, response_tokens=0, latency_ms=0.0)
        else:
            if not prompt:
                logger.warning("Empty prompt list received. Returning empty response.")
                return AssistantResponse(text="", prompt_tokens=0, response_tokens=0, latency_ms=0.0)

        # Check in-memory cache
        cache_key = ""
        if self.enable_cache:
            if isinstance(prompt, str):
                cache_key = prompt.strip().lower()
            else:
                parts = []
                for content in prompt:
                    role = content.role
                    text_parts = []
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    parts.append(f"{role}:{''.join(text_parts)}")
                cache_key = "|".join(parts).lower()

            if cache_key in self._cache:
                logger.info("Cache HIT for prompt key: '%s'", cache_key)
                cached = self._cache[cache_key]
                if self.tracker:
                    from audio.latency import TimerRecord
                    self.tracker._timers["Network Request"] = TimerRecord("Network Request", elapsed_ms=0.0)
                    self.tracker._timers["Model Generation"] = TimerRecord("Model Generation", elapsed_ms=0.0)
                    self.tracker._timers["Response Parsing"] = TimerRecord("Response Parsing", elapsed_ms=0.0)
                    self.tracker._timers["Total LLM Time"] = TimerRecord("Total LLM Time", elapsed_ms=0.0)
                return cached

        # Configure request options optimized for voice assistants
        gen_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            max_output_tokens=self.config.max_output_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )

        # Setup retry parameters
        retries = self.config.max_retries
        backoff = 0.5

        total_start = time.perf_counter()

        last_error = None
        for attempt in range(1, retries + 1):
            try:
                logger.debug("LLM generation attempt %d/%d...", attempt, retries)
                
                # Execute generation and measure network/generation times
                api_start = time.perf_counter()
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=gen_config,
                )
                api_end = time.perf_counter()
                
                # Parse response and extract tokens
                parse_start = time.perf_counter()
                text = self._extract_response_text(response)
                
                # Extract token counts and finish reasons
                prompt_tokens = 0
                response_tokens = 0
                finish_reason = "UNKNOWN"
                
                if response.usage_metadata:
                    prompt_tokens = response.usage_metadata.prompt_token_count or 0
                    response_tokens = response.usage_metadata.candidates_token_count or 0
                
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    if hasattr(candidate, "finish_reason") and candidate.finish_reason:
                        finish_reason = str(candidate.finish_reason).upper().split(".")[-1]
                
                parse_end = time.perf_counter()
                total_end = time.perf_counter()

                # Calculate latency splits (ms)
                api_duration_ms = (api_end - api_start) * 1000.0
                network_ms = min(150.0, api_duration_ms * 0.15)  # Estimate network transit overhead
                generation_ms = max(0.0, api_duration_ms - network_ms)
                parsing_ms = (parse_end - parse_start) * 1000.0
                total_ms = (total_end - total_start) * 1000.0

                # Log details as requested
                logger.info("Model             : %s", self.model_name)
                logger.info("Temperature       : %.1f", self.config.temperature)
                logger.info("Prompt Tokens     : %d", prompt_tokens)
                logger.info("Completion Tokens : %d", response_tokens)
                logger.info("Finish Reason     : %s", finish_reason)
                logger.info("Latency           : %.2f seconds", total_ms / 1000.0)

                # Inject timing stages into tracker if configured
                if self.tracker:
                    from audio.latency import TimerRecord
                    self.tracker._timers["Network Request"] = TimerRecord("Network Request", elapsed_ms=network_ms)
                    self.tracker._timers["Model Generation"] = TimerRecord("Model Generation", elapsed_ms=generation_ms)
                    self.tracker._timers["Response Parsing"] = TimerRecord("Response Parsing", elapsed_ms=parsing_ms)
                    self.tracker._timers["Total LLM Time"] = TimerRecord("Total LLM Time", elapsed_ms=total_ms)

                response_obj = AssistantResponse(
                    text=text,
                    prompt_tokens=prompt_tokens,
                    response_tokens=response_tokens,
                    latency_ms=total_ms,
                )

                if self.enable_cache and cache_key:
                    self._cache[cache_key] = response_obj

                return response_obj

            except APIError as exc:
                last_error = LLMConnectionError(f"Gemini API error: {exc}")
                logger.warning("APIError on attempt %d: %s", attempt, exc)
            except Exception as exc:
                last_error = LLMError(f"Unexpected error: {exc}")
                logger.warning("Error on attempt %d: %s", attempt, exc)

            if attempt < retries:
                time.sleep(backoff)
                backoff *= 2

        logger.error("LLM generation failed after %d attempts. Last error: %s", retries, last_error)
        raise last_error or LLMError("LLM generation failed.")

    def generate_response_stream(self, prompt: str | list[types.Content]):
        """Stream response chunks from Gemini using the streaming API.

        Args:
            prompt: User input transcript string or list of Content objects.

        Yields:
            str: Each text chunk as it arrives from the model.

        After iteration completes, the final AssistantResponse is available
        via the .stream_result attribute set on this generator.
        """
        # Validate prompt input
        if isinstance(prompt, str):
            if not prompt or not prompt.strip():
                return
        else:
            if not prompt:
                return

        gen_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            max_output_tokens=self.config.max_output_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )

        total_start = time.perf_counter()

        try:
            logger.debug("Starting streaming LLM generation...")
            stream = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=prompt,
                config=gen_config,
            )

            accumulated = ""
            prompt_tokens = 0
            response_tokens = 0

            for chunk in stream:
                # Extract text from this chunk
                chunk_text = ""
                if hasattr(chunk, "text") and chunk.text:
                    chunk_text = chunk.text
                elif hasattr(chunk, "candidates") and chunk.candidates:
                    for candidate in chunk.candidates:
                        if hasattr(candidate, "content") and candidate.content:
                            if hasattr(candidate.content, "parts") and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if hasattr(part, "text") and part.text:
                                        chunk_text += part.text

                if chunk_text:
                    accumulated += chunk_text
                    yield chunk_text

                # Extract token counts from final chunk usage metadata
                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    if chunk.usage_metadata.prompt_token_count:
                        prompt_tokens = chunk.usage_metadata.prompt_token_count
                    if chunk.usage_metadata.candidates_token_count:
                        response_tokens = chunk.usage_metadata.candidates_token_count

            total_ms = (time.perf_counter() - total_start) * 1000.0

            logger.info("Stream completed: %d chars, %.2f ms", len(accumulated), total_ms)

            # Store final result for the caller to retrieve after iteration
            self._last_stream_result = AssistantResponse(
                text=accumulated.strip(),
                prompt_tokens=prompt_tokens,
                response_tokens=response_tokens,
                latency_ms=total_ms,
            )

        except APIError as exc:
            logger.error("Streaming API error: %s", exc)
            raise LLMConnectionError(f"Gemini streaming API error: {exc}") from exc
        except Exception as exc:
            logger.error("Streaming error: %s", exc)
            raise LLMError(f"Streaming error: {exc}") from exc

    @property
    def last_stream_result(self) -> Optional[AssistantResponse]:
        """Get the AssistantResponse from the last completed stream."""
        return getattr(self, "_last_stream_result", None)
