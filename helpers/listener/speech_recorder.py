"""Speech recorder helper.

Opens the microphone stream and records until speech is detected and ends.
Provides a small, testable class that encapsulates stream management and energy-based
speech detection.
"""

from __future__ import annotations

import logging
import os
import time
import audioop
from typing import Optional

import pyaudio


logger = logging.getLogger(__name__)


class SpeechRecorder:
    def __init__(
        self,
        rate: int = 16000,
        channels: int = 1,
        format: int = pyaudio.paInt16,
        frames_per_buffer: int = 8192,
        device_index: Optional[int] = None,
    ):
        self._rate = rate
        self._channels = channels
        self._format = format
        self._frames_per_buffer = frames_per_buffer
        self._device_index = device_index

        self._stream: Optional[pyaudio.Stream] = None

    def _open_stream(self) -> pyaudio.Stream:
        if self._stream is not None:
            return self._stream

        # Suppress ALSA / device warnings during PyAudio instantiation
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr_fd = os.dup(2)
        os.dup2(devnull, 2)
        try:
            pa = pyaudio.PyAudio()

            # Log device info for debugging
            if self._device_index is not None:
                device_info = pa.get_device_info_by_index(self._device_index)
                logger.info(f"Opening microphone: {device_info['name']} (Device {self._device_index})")
            else:
                device_info = pa.get_default_input_device_info()
                if device_info:
                    logger.info(f"Opening default microphone: {device_info['name']}")
                else:
                    logger.info("Opening default microphone: (no device info available)")

            self._stream = pa.open(
                format=self._format,
                channels=self._channels,
                rate=self._rate,
                input=True,
                frames_per_buffer=self._frames_per_buffer,
                input_device_index=self._device_index,
            )
            self._stream.start_stream()
        except Exception as e:
            logger.error(f"Error opening audio stream: {e}")
            raise
        finally:
            os.dup2(old_stderr_fd, 2)
            os.close(devnull)
            os.close(old_stderr_fd)

        return self._stream

    def close(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def record_until_speech_end(
        self,
        duration_seconds: int,
        start_threshold: int = 500,
        silence_threshold: int = 400,
        silence_max_frames: int = 3,
        chunk: int = 4096,
    ) -> bytes:
        """Open the stream (if needed) and record until speech end.

        Returns raw PCM bytes (16-bit mono) — may be empty if nothing detected.
        """
        stream = self._open_stream()

        start_time = time.time()
        buffer = bytearray()

        speech_started = False
        silence_frames = 0

        while self._stream is not None:
            # duration guard
            if duration_seconds > 0 and (time.time() - start_time) >= duration_seconds:
                # Allow user to finish speaking if they already started
                if not speech_started:
                    break

            try:
                chunk_bytes = stream.read(chunk, exception_on_overflow=False)
            except Exception as e:
                logger.error(f"Error reading from stream: {e}")
                break

            if not chunk_bytes:
                break

            try:
                rms = audioop.rms(chunk_bytes, 2)
            except Exception:
                rms = 0

            # Wait for speech start
            if not speech_started:
                if rms >= start_threshold:
                    speech_started = True
                    logger.info(f"Speech detected (RMS: {rms} / {start_threshold})")
                else:
                    continue

            # Add to speech buffer
            buffer.extend(chunk_bytes)

            # Wait for speech end
            if rms < silence_threshold:
                silence_frames += 1
            else:
                silence_frames = 0

            if silence_frames >= silence_max_frames:
                logger.info(f"Silence detected ({silence_frames} frames) / {silence_threshold}, ending recording")
                break

        return bytes(buffer)
