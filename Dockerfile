FROM python:3.11

WORKDIR /app

# ✅ System dependencies (OpenCV / image processing fix)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# Create uploads directory
RUN mkdir -p uploads

EXPOSE 10000

CMD ["gunicorn", "-k", "eventlet", "-w", "1", "--bind", "0.0.0.0:10000", "app:app"]
