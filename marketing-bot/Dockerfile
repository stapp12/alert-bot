FROM node:20-slim AS base

# ── תלויות מערכת (FFmpeg + Chrome deps + Python) ──────────────────────────────
RUN apt-get update && apt-get install -y \
    ffmpeg \
    python3 \
    python3-pip \
    python3-venv \
    chromium \
    fonts-noto \
    fonts-noto-cjk \
    ca-certificates \
    curl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    CHROME_PATH=/usr/bin/chromium

WORKDIR /app

# ── התקנת תלויות Node ─────────────────────────────────────────────────────────
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev

# ── התקנת תלויות Python ───────────────────────────────────────────────────────
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# ── העתקת קוד הפרויקט ────────────────────────────────────────────────────────
COPY . .

# ── יצירת תיקיות פלט ─────────────────────────────────────────────────────────
RUN mkdir -p out public

EXPOSE 8080

CMD ["python3", "bot_manager.py"]
