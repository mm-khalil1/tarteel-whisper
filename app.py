"""Gradio web demo: record or upload a recitation and get the Arabic transcript.

Usage:
    python app.py   # then open http://127.0.0.1:7860
"""

import gradio as gr
import librosa
import torch

from transcribe import MODEL_ID, SAMPLE_RATE, load_model, transcribe

device = "cuda" if torch.cuda.is_available() else "cpu"
processor, model = load_model(device)


def run(audio_path):
    if audio_path is None:
        return ""
    audio, _ = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    return transcribe(audio, processor, model, device)


demo = gr.Interface(
    fn=run,
    inputs=gr.Audio(sources=["microphone", "upload"], type="filepath", label="Recitation"),
    outputs=gr.Textbox(label="Transcript", rtl=True, lines=6),
    title="Tarteel Whisper — Quran Recitation ASR",
    description=f"Model: `{MODEL_ID}` running on **{device}**.",
    flagging_mode="never",
)

if __name__ == "__main__":
    demo.launch()
