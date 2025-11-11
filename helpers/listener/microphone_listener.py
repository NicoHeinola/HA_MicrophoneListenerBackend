import logging
import os
import threading

import pyaudio


logger = logging.getLogger(__name__)


class MicrophoneListener:
    def __init__(self):
        self._is_listening = False
        self._listening_thread: threading.Thread | None = None

    @property
    def is_listening(self) -> bool:
        return self._is_listening and self._listening_thread is not None and self._listening_thread.is_alive()

    def _open_microphone_stream(self) -> pyaudio.Stream:
        """Open microphone audio stream for recording"""

        # Suppress ALSA and audio device warnings during PyAudio instantiation
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr_fd = os.dup(2)
        os.dup2(devnull, 2)
        try:
            mic: pyaudio.PyAudio = pyaudio.PyAudio()
            stream = mic.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
        finally:
            os.dup2(old_stderr_fd, 2)
            os.close(devnull)
            os.close(old_stderr_fd)

        return stream

    def _listen_loop(self, model: str, duration_seconds: int):
        stream: pyaudio.Stream = self._open_microphone_stream()
        stream.start_stream()
        start_time = os.times()[4]

        logger.info("Listening for speech...")
        data: bytes = b""

        try:
            while self._is_listening and self._listening_thread is not None and self._listening_thread.is_alive():
                # Check time conditions
                elapsed_time = os.times()[4] - start_time
                if duration_seconds > 0 and elapsed_time >= duration_seconds:
                    break

                # Stop when we some data
                if len(data) > 0:
                    break

                data: bytes = stream.read(4096, exception_on_overflow=False)
                if len(data) == 0:
                    break

        finally:
            stream.stop_stream()
            stream.close()

        # Automatically restart listening if duration is zero (continuous mode) and still listening
        if duration_seconds == 0 and self._is_listening:
            self._is_listening = False
            self._listening_thread = None

            self.start_listening(model=model, duration_seconds=duration_seconds)
        else:
            logger.info("Listening loop ended.")

    def start_listening(self, model: str, duration_seconds: int):
        if self.is_listening:
            return

        self._is_listening = True
        self._listening_thread = threading.Thread(
            target=self._listen_loop,
            args=(model, duration_seconds),
            daemon=True,
        )
        self._listening_thread.start()

    def stop_listening(self):
        if not self.is_listening:
            return

        # Signal the listening loop to stop
        self._is_listening = False

        # Signal the speech-to-text helper to stop its processing
        if self._speech_to_text_helper is not None:
            self._speech_to_text_helper.stop_listening()

        # Wait for the thread to finish with a reasonable timeout
        if self._listening_thread is not None:
            self._listening_thread.join(timeout=2.0)

            if self._listening_thread.is_alive():
                logger.warning("Listening thread did not stop gracefully within timeout")

            self._listening_thread = None

        self._speech_to_text_helper = None
