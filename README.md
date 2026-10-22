# tarteel-whisper

A small demo of [`tarteel-ai/whisper-base-ar-quran`](https://huggingface.co/tarteel-ai/whisper-base-ar-quran),
a Whisper-base model fine-tuned for Quran recitation (Arabic ASR).

## Setup (Windows)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

The model (~290 MB) downloads from Hugging Face on first run and is cached.

### Optional: GPU

`pip install torch` gives the CPU build on Windows. For an NVIDIA GPU, install the CUDA build instead:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu126
```

## Usage

Command line:

```bash
python transcribe.py path/to/recitation.wav
```

Web demo (microphone or file upload):

```bash
python app.py
```

Then open http://127.0.0.1:7860.

## Notes

- Audio is resampled to 16 kHz mono. Audio longer than 30 s is split into 30 s chunks.
- Output is Arabic text with diacritics (tashkeel).
- Like all Whisper models, it can hallucinate text on silence or non-speech audio.
