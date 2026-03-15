ARG BUILD_FROM
FROM python:3.11-slim

COPY rootfs/app/requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && playwright install --with-deps chromium

COPY rootfs/ /

CMD ["python3", "/app/main.py"]
