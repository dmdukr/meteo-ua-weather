ARG BUILD_FROM
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

COPY rootfs/app/requirements.txt /tmp/
RUN pip install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

COPY rootfs/ /

CMD ["python3", "/app/main.py"]
