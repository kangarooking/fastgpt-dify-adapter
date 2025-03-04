FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 让 Gunicorn 使用环境变量
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT}", "--timeout", "${GUNICORN_TIMEOUT}", "--access-logfile", "-", "--error-logfile", "-", "app:app"]

