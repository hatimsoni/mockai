FROM python:3.12-slim

# No system ffmpeg needed: PyAV wheels (used by faster-whisper) bundle FFmpeg to decode webm/ogg.
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# NLTK data + embedding model baked into the image so the container works offline
RUN python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True); nltk.download('stopwords', quiet=True); nltk.download('averaged_perceptron_tagger_eng', quiet=True)"
ENV HF_HOME=/models-cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY app ./app
COPY models ./models

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
