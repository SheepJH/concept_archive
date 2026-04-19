# Playwright official image already has Chromium + browsers preinstalled.
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Korean fonts so Pretendard fallback chain can render Hangul correctly even
# if the CDN font fails to load.
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-noto-cjk fonts-noto-cjk-extra fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps (cached layer)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy templates + shared CSS first (rarely changes), then backend code
COPY templates /app/templates
COPY shared /app/shared
COPY backend /app/backend

WORKDIR /app/backend

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
