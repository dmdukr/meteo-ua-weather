ARG BUILD_FROM
FROM python:3.11-slim

# Install system deps for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
    libx11-xcb1 libxcb-dri3-0 fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

COPY rootfs/app/requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && playwright install chromium

COPY rootfs/ /

CMD ["python3", "/app/main.py"]
