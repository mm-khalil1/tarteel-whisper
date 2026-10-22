"""HTTP service: the recite page plus a JSON API the Quran portal can call.

Run:
    uvicorn recite.server:app --host 0.0.0.0 --port 8000

Environment:
    PORTAL_ORIGIN   origin of the portal, e.g. https://quran.muslimwellness.ca.
                    Allowed to call the API (CORS), to embed the page in an
                    iframe, and to receive the result via postMessage.
    MAX_AUDIO_MB    upload limit (default 25).
"""

import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from . import asr, quran
from .checker import check

PORTAL_ORIGIN = os.environ.get("PORTAL_ORIGIN", "").rstrip("/")
MAX_AUDIO_BYTES = int(float(os.environ.get("MAX_AUDIO_MB", "25")) * 1e6)
STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Tarteel Whisper recitation checker")
if PORTAL_ORIGIN:
    app.add_middleware(CORSMiddleware, allow_origins=[PORTAL_ORIGIN], allow_methods=["GET", "POST"], allow_headers=["*"])


@app.middleware("http")
async def frame_policy(request, call_next):
    response = await call_next(request)
    ancestors = f"'self' {PORTAL_ORIGIN}".strip()
    response.headers["Content-Security-Policy"] = f"frame-ancestors {ancestors}"
    return response


def _passage(from_surah: int, to_surah: int | None, from_ayah: int, to_ayah: int | None):
    try:
        return quran.passage(from_surah, to_surah or from_surah, from_ayah, to_ayah)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/config")
def config():
    return {"portal_origin": PORTAL_ORIGIN or None}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/surahs")
def surahs():
    return quran.surah_list()


@app.get("/api/passage")
def get_passage(
    from_surah: int = Query(..., ge=1, le=114),
    to_surah: int | None = Query(None, ge=1, le=114),
    from_ayah: int = Query(1, ge=1),
    to_ayah: int | None = Query(None, ge=1),
):
    words = _passage(from_surah, to_surah, from_ayah, to_ayah)
    names = {s["n"]: s for s in quran.surah_list()}
    ayahs = []
    for w in words:
        if not ayahs or (ayahs[-1]["surah"], ayahs[-1]["ayah"]) != (w.surah, w.ayah):
            ayahs.append({"surah": w.surah, "ayah": w.ayah, "words": []})
        ayahs[-1]["words"].append({"text": w.uthmani, "page": w.page})
    return {
        "surahs": [names[n] for n in sorted({w.surah for w in words})],
        "pages": sorted({w.page for w in words}),
        "ayahs": ayahs,
    }


@app.post("/api/check")
async def check_recitation(
    audio: UploadFile = File(..., description="wav, flac, ogg or mp3"),
    from_surah: int = Form(..., ge=1, le=114),
    to_surah: int | None = Form(None, ge=1, le=114),
    from_ayah: int = Form(1, ge=1),
    to_ayah: int | None = Form(None, ge=1),
):
    words = _passage(from_surah, to_surah, from_ayah, to_ayah)
    data = await audio.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "audio file too large")
    try:
        samples = asr.load_audio(data)
    except Exception:
        raise HTTPException(415, "could not decode audio; send wav, flac, ogg or mp3")
    transcript = await run_in_threadpool(asr.transcribe, samples)
    return {
        "range": {"from_surah": from_surah, "to_surah": to_surah or from_surah, "from_ayah": from_ayah, "to_ayah": to_ayah},
        "duration_s": round(len(samples) / asr.SAMPLE_RATE, 1),
        **check(words, transcript),
    }


app.mount("/static", StaticFiles(directory=STATIC), name="static")
