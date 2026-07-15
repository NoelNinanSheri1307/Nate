"""
Audio device detection and enumeration.

Provides functions to discover available audio input and output devices,
retrieve defaults, and log device information.
"""

from dataclasses import dataclass

import sounddevice as sd

from utils.logger import setup_logger

logger = setup_logger("nate.audio.devices")


@dataclass(frozen=True)
class AudioDeviceInfo:
    """Structured representation of an audio device."""

    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_sample_rate: float
    is_default_input: bool = False
    is_default_output: bool = False


def _query_devices() -> list[dict]:
    """Query all audio devices from sounddevice.

    Returns:
        List of raw device info dictionaries.
    """
    try:
        return list(sd.query_devices())
    except Exception as exc:
        logger.error("Failed to query audio devices: %s", exc)
        return []


def _get_defaults() -> tuple[int | None, int | None]:
    """Get default input and output device indices.

    Returns:
        Tuple of (default_input_index, default_output_index).
        Either value may be None if no default is available.
    """
    try:
        defaults = sd.default.device
        input_idx = defaults[0] if isinstance(defaults, (list, tuple)) else defaults
        output_idx = defaults[1] if isinstance(defaults, (list, tuple)) else defaults
        return input_idx, output_idx
    except Exception as exc:
        logger.warning("Could not determine default devices: %s", exc)
        return None, None


def _build_device_info(
    index: int,
    raw: dict,
    default_input_idx: int | None,
    default_output_idx: int | None,
) -> AudioDeviceInfo:
    """Build an AudioDeviceInfo from a raw sounddevice dict."""
    return AudioDeviceInfo(
        index=index,
        name=raw.get("name", "Unknown"),
        max_input_channels=raw.get("max_input_channels", 0),
        max_output_channels=raw.get("max_output_channels", 0),
        default_sample_rate=raw.get("default_samplerate", 0.0),
        is_default_input=(index == default_input_idx),
        is_default_output=(index == default_output_idx),
    )


def list_input_devices() -> list[AudioDeviceInfo]:
    """List all available audio input (microphone) devices.

    Returns:
        List of AudioDeviceInfo for devices with input channels.
    """
    raw_devices = _query_devices()
    default_in, default_out = _get_defaults()

    inputs: list[AudioDeviceInfo] = []
    for i, dev in enumerate(raw_devices):
        if dev.get("max_input_channels", 0) > 0:
            info = _build_device_info(i, dev, default_in, default_out)
            inputs.append(info)

    logger.info("Found %d input device(s)", len(inputs))
    for dev in inputs:
        marker = " [DEFAULT]" if dev.is_default_input else ""
        logger.debug("  [%d] %s (%d ch, %.0f Hz)%s",
                      dev.index, dev.name, dev.max_input_channels,
                      dev.default_sample_rate, marker)

    if not inputs:
        logger.warning("No input devices detected")

    return inputs


def list_output_devices() -> list[AudioDeviceInfo]:
    """List all available audio output (speaker) devices.

    Returns:
        List of AudioDeviceInfo for devices with output channels.
    """
    raw_devices = _query_devices()
    default_in, default_out = _get_defaults()

    outputs: list[AudioDeviceInfo] = []
    for i, dev in enumerate(raw_devices):
        if dev.get("max_output_channels", 0) > 0:
            info = _build_device_info(i, dev, default_in, default_out)
            outputs.append(info)

    logger.info("Found %d output device(s)", len(outputs))
    for dev in outputs:
        marker = " [DEFAULT]" if dev.is_default_output else ""
        logger.debug("  [%d] %s (%d ch, %.0f Hz)%s",
                      dev.index, dev.name, dev.max_output_channels,
                      dev.default_sample_rate, marker)

    if not outputs:
        logger.warning("No output devices detected")

    return outputs


def get_default_input() -> AudioDeviceInfo | None:
    """Get the default input device.

    Returns:
        AudioDeviceInfo for the default microphone, or None if unavailable.
    """
    inputs = list_input_devices()
    for dev in inputs:
        if dev.is_default_input:
            logger.info("Default input: [%d] %s", dev.index, dev.name)
            return dev

    # Fallback to the first available input
    if inputs:
        logger.warning("No explicit default input; using first available: [%d] %s",
                        inputs[0].index, inputs[0].name)
        return inputs[0]

    logger.error("No input devices available")
    return None


def get_default_output() -> AudioDeviceInfo | None:
    """Get the default output device.

    Returns:
        AudioDeviceInfo for the default speaker, or None if unavailable.
    """
    outputs = list_output_devices()
    for dev in outputs:
        if dev.is_default_output:
            logger.info("Default output: [%d] %s", dev.index, dev.name)
            return dev

    # Fallback to the first available output
    if outputs:
        logger.warning("No explicit default output; using first available: [%d] %s",
                        outputs[0].index, outputs[0].name)
        return outputs[0]

    logger.error("No output devices available")
    return None
