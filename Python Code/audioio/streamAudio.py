"""
audio_stream.py — reusable stereo audio capture class.

Usage:
    stream = AudioStream(device_index=0)
    stream.start()
    chunks = stream.read_chunks()   # call repeatedly in your render loop
    stream.stop()

Or use as a context manager:
    with AudioStream(device_index=0) as stream:
        chunks = stream.read_chunks()
"""

import numpy as np
import pyaudio


class AudioStream:
    """
    Wraps a PyAudio input stream for multi-channel audio capture.

    Parameters
    ----------
    device_index : int | None
        PyAudio device index to open. None = system default.
    sample_rate : int
        Samples per second (Hz). Must match device capability.
    channels : int
        Number of input channels (1 = mono, 2 = stereo, …).
    chunk : int
        Frames read per PyAudio call. Smaller = lower latency, higher CPU.
    fmt : int
        PyAudio format constant (default: paInt16).
    """

    def __init__(
        self,
        device_index: int = 0,
        sample_rate: int = 48000,
        channels: int = 2,
        chunk: int = 1024,
        fmt: int = pyaudio.paInt16,
    ):
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk = chunk
        self.fmt = fmt

        self._pa: pyaudio.PyAudio | None = None
        self._stream: pyaudio.Stream | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Open the PyAudio interface and start the input stream."""
        if self._stream is not None:
            raise RuntimeError("Stream is already running. Call stop() first.")

        self._pa = pyaudio.PyAudio()
        self._stream = self._pa.open(
            format=self.fmt,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk,
            input_device_index=self.device_index,
        )

    def stop(self) -> None:
        """Stop and close the stream, releasing hardware resources."""
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        if self._pa is not None:
            self._pa.terminate()
            self._pa = None

    # ── Data retrieval ────────────────────────────────────────────────────────

    def read_chunks(self) -> np.ndarray | None:
        """
        Drain all currently available audio from the device buffer.

        Reads every complete chunk that is ready without blocking, then
        concatenates them into a single array.

        Returns
        -------
        np.ndarray of shape (n_samples, channels), dtype int16,
        or None if no new data was available this call.
        """
        if self._stream is None:
            raise RuntimeError("Stream is not running. Call start() first.")

        frames = []
        while self._stream.get_read_available() >= self.chunk:
            raw = self._stream.read(self.chunk, exception_on_overflow=False)
            interleaved = np.frombuffer(raw, dtype=np.int16)
            frames.append(interleaved.reshape(-1, self.channels))

        if not frames:
            return None

        return np.concatenate(frames, axis=0)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def list_input_devices() -> list[dict]:
        """
        Return a list of available input devices as dicts with keys:
        index, name, channels, sample_rate.
        """
        pa = pyaudio.PyAudio()
        devices = []
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                devices.append({
                    "index":       i,
                    "name":        info["name"],
                    "channels":    int(info["maxInputChannels"]),
                    "sample_rate": int(info["defaultSampleRate"]),
                })
        pa.terminate()
        return devices

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()

    def __repr__(self) -> str:
        state = "running" if self._stream else "stopped"
        return (
            f"AudioStream(device={self.device_index}, "
            f"rate={self.sample_rate}, ch={self.channels}, "
            f"chunk={self.chunk}, state={state})"
        )