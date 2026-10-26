FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
  tesseract-ocr tesseract-ocr-eng tesseract-ocr-tam clamav ca-certificates \
  && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY web ./web
RUN mkdir -p /app/uploads && chmod 700 /app/uploads
EXPOSE 8000
CMD ["uvicorn","backend.app:app","--host","0.0.0.0","--port","8000"]
