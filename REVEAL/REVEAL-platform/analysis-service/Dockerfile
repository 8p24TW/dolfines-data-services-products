FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl fonts-dejavu-core libasound2 \
    libatk-bridge2.0-0 libatk1.0-0 libcairo2 libdrm2 libffi8 \
    libfontconfig1 libgbm1 libgdk-pixbuf-2.0-0 libglib2.0-0 \
    libgtk-3-0 libharfbuzz0b libnss3 libpango-1.0-0 libpangocairo-1.0-0 \
    libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxdamage1 libxext6 \
    libxfixes3 libxkbcommon0 libxrandr2 shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY ["requirements.txt", "./requirements.txt"]
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && python -m playwright install chromium

COPY ["app/", "./app/"]
COPY ["solar_engine/", "./solar_engine/"]
COPY ["data/", "./data/"]

RUN mkdir -p /app/cache /tmp/reveal-analysis

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --timeout-keep-alive 600"]
