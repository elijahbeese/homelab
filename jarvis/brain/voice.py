"""
Voice pipeline — Whisper STT and Piper TTS.

Both run fully local on the ProLiant's CPU. On Xeon X5650 cores:
  - tiny.en transcribes realtime audio in ~0.2x realtime (very fast)
  - small.en transcribes in ~0.4x realtime (still faster than human speech)
  - piper synthesizes ~5x realtime (plenty fast)
"""
from __future__ import annotations
import asyncio
import io
import wave
import tempfile
import subprocess
from pathlib import Path

from faster_whisper import WhisperModel
import structlog

log = structlog.get_logger()


class STT:
    def __init__(self, model_name: str, device: str, compute_type: str, beam_size: int):
        log.info("loading_whisper", model=model_name, device=device, compute_type=compute_type)
        self.model = WhisperModel(model_name, device=device, compute_type=compute_type)
        self.beam_size = beam_size

    def transcribe(self, wav_bytes: bytes) -> str:
        # Write to a temp file; faster-whisper wants a path or a numpy array
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
            f.write(wav_bytes)
            f.flush()
            segments, info = self.model.transcribe(
                f.name,
                beam_size=self.beam_size,
                vad_filter=True,
                language="en",
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            log.info("transcribed", chars=len(text), detected_language=info.language)
            return text


class TTS:
    def __init__(self, voice: str, length_scale: float = 1.0):
        self.voice = voice
        self.length_scale = length_scale
        self.voice_path = Path(f"/app/voices/{voice}.onnx")
        if not self.voice_path.exists():
            raise FileNotFoundError(f"Piper voice not found: {self.voice_path}")

    def synthesize(self, text: str) -> bytes:
        """Return WAV bytes for the given text."""
        # piper reads text from stdin, writes WAV to stdout
        proc = subprocess.run(
            [
                "piper",
                "--model", str(self.voice_path),
                "--length-scale", str(self.length_scale),
                "--output_raw",
            ],
            input=text.encode("utf-8"),
            capture_output=True,
            check=False,
            timeout=30,
        )
        if proc.returncode != 0:
            log.error("piper_failed", stderr=proc.stderr.decode(errors="replace")[:500])
            return b""

        # piper --output_raw emits headerless 16-bit PCM at the voice's sample rate.
        # Wrap it in a WAV header.
        raw = proc.stdout
        # Sample rate is embedded in the voice's .json config; Amy medium is 22050
        # We'll read it lazily — for now hardcode common defaults.
        sample_rate = 22050
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(raw)
        return buf.getvalue()
