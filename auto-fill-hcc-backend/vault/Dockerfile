FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY vault_app.py .

EXPOSE 8000
CMD ["uvicorn", "vault_app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "8"]
