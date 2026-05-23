# Stage 1: Build frontend
FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + built frontend
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY watchlist.yaml .
COPY --from=frontend-builder /app/frontend/dist frontend/dist

RUN mkdir -p /app/data /data

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
