FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# tesseract-ocr: dùng cho OSD (phát hiện & sửa chiều ảnh/PDF bị xoay) trong OCR Vintern.
# ttf-mscorefonts-installer (kho contrib): Times New Roman cho biên bản chấp thuận theo thể thức Nghị định 30
# (app/consent/pdf.py) — font Microsoft không được đóng kèm mã nguồn, gói tải bộ font lõi lúc build.
RUN sed -i 's/^Components: main$/Components: main contrib/' /etc/apt/sources.list.d/debian.sources \
    && echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections \
    && apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr ttf-mscorefonts-installer \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

EXPOSE 8000

# Đặt SAU các lớp COPY/pip: đổi tag không làm cài lại thư viện.
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

CMD ["sh", "-c", "uvicorn app.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-4}"]
