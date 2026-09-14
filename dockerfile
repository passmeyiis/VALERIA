FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run akan otomatis mengisi port, Gunicorn mendengarkan port tersebut
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app