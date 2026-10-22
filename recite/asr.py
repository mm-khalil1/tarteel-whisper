"""Speech recognition with tarteel-ai/whisper-base-ar-quran."""

import io
from functools import lru_cache

import librosa
import numpy as np
import soundfile as sf
import torch
from transformers import GenerationConfig, WhisperForConditionalGeneration, WhisperProcessor, pipeline

MODEL_ID = "tarteel-ai/whisper-base-ar-quran"
BASE_MODEL_ID = "openai/whisper-base"
SAMPLE_RATE = 16_000  # Whisper expects 16 kHz mono audio


@lru_cache(maxsize=1)
def _pipe():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = WhisperProcessor.from_pretrained(MODEL_ID)
    model = WhisperForConditionalGeneration.from_pretrained(MODEL_ID)
    # The checkpoint ships an old generation config that doesn't support
    # `language=`/`task=`; use the one from the base model it was fine-tuned from.
    model.generation_config = GenerationConfig.from_pretrained(BASE_MODEL_ID)
    return pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        # Whisper sees 30 s at a time; overlapping chunks avoid cutting words.
        chunk_length_s=30,
        stride_length_s=5,
        device=device,
    )


def device() -> str:
    return str(_pipe().device)


def load_audio(data: bytes) -> np.ndarray:
    """Decode wav/flac/ogg/mp3 bytes to 16 kHz mono float32."""
    audio, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=True)
    audio = audio.mean(axis=1)
    if sr != SAMPLE_RATE:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLE_RATE)
    return audio


def transcribe(audio: np.ndarray) -> str:
    out = _pipe()(
        {"raw": audio, "sampling_rate": SAMPLE_RATE},
        batch_size=4,
        generate_kwargs={"language": "ar", "task": "transcribe"},
    )
    return out["text"].strip()
