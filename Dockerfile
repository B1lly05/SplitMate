FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY back ./back
CMD exec uvicorn back.main:app --host 0.0.0.0 --port ${PORT:-8080}