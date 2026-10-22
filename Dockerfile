FROM python:3.13-slim

WORKDIR /app

# CPU-only PyTorch keeps the image small; use a CUDA base image + wheel for GPU.
COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.14.1 \
 && pip install --no-cache-dir -r requirements.txt

COPY recite recite
COPY static static
COPY data data

# Bake the model into the image so containers start without downloading it.
RUN python -c "from recite import asr; asr.device()"

EXPOSE 8000
CMD ["uvicorn", "recite.server:app", "--host", "0.0.0.0", "--port", "8000"]
