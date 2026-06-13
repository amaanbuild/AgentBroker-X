# AgentBroker X - backend container
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Railway provides $PORT at runtime; default to 8000 locally.
ENV PORT=8000
EXPOSE 8000

# Boot the API. Use sh -c so ${PORT} is expanded by the shell (Railway runs
# the start command in exec form, which would otherwise pass "$PORT" literally
# to uvicorn). The app creates its schema on startup (init_db), so no blocking
# migration step is needed before the server binds the port.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
