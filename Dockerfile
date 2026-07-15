FROM python:3.12-slim

WORKDIR /app

# 의존성 먼저 (레이어 캐시)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 공유 코어 + 웹 앱만 포함 (Foundry transforms/functions/backup 은 제외)
COPY src ./src
COPY webapp ./webapp

# /app : webapp 패키지 import, /app/src : core 패키지 import
ENV PYTHONPATH=/app:/app/src \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Railway 는 $PORT 를 주입한다. 없으면 8000.
CMD ["sh", "-c", "uvicorn webapp.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
