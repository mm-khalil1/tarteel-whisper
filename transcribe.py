"""Transcribe Quran recitation audio with tarteel-ai/whisper-base-ar-quran.

Usage:
    python transcribe.py path/to/recitation.wav
"""

import argparse
import sys

import librosa
import torch
from transformers import GenerationConfig, WhisperForConditionalGeneration, WhisperProcessor

MODEL_ID = "tarteel-ai/whisper-base-ar-quran"
BASE_MODEL_ID = "openai/whisper-base"
SAMPLE_RATE = 16_000  # Whisper expects 16 kHz mono audio


def load_model(device: str):
    processor = WhisperProcessor.from_pretrained(MODEL_ID)
    model = WhisperForConditionalGeneration.from_pretrained(MODEL_ID).to(device)
    # The checkpoint ships an old generation config that doesn't support
    # `language=`/`task=`; use the one from the base model it was fine-tuned from.
    model.generation_config = GenerationConfig.from_pretrained(BASE_MODEL_ID)
    model.eval()
    return processor, model


def transcribe(audio, processor, model, device: str) -> str:
    """Transcribe a 16 kHz mono float array. Whisper sees at most 30 s per call,
    so longer audio is split into 30 s chunks and the results joined."""
    chunk = 30 * SAMPLE_RATE
    texts = []
    for start in range(0, len(audio), chunk):
        segment = audio[start : start + chunk]
        inputs = processor(segment, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        features = inputs.input_features.to(device)
        with torch.no_grad():
            ids = model.generate(features, language="ar", task="transcribe")
        texts.append(processor.batch_decode(ids, skip_special_tokens=True)[0].strip())
    return " ".join(t for t in texts if t)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("audio", help="Path to an audio file (wav, flac, mp3, ogg, ...)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading {MODEL_ID} on {device}...")
    processor, model = load_model(device)

    audio, _ = librosa.load(args.audio, sr=SAMPLE_RATE, mono=True)
    print(f"Audio length: {len(audio) / SAMPLE_RATE:.1f} s\n")
    print(transcribe(audio, processor, model, device))


if __name__ == "__main__":
    main()
