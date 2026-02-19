FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ src/
COPY assets/ assets/

RUN pip install --no-cache-dir .

# Ensure assets and output directories are discoverable at runtime
ENV ASSETS_DIR=/app/assets
ENV OUTPUT_BASE_DIR=/app/output

EXPOSE 8000

CMD ["uvicorn", "podcast_shorts.main:app", "--host", "0.0.0.0", "--port", "8000"]
