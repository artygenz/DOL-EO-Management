FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Expose container port 80 to match docker-compose mapping (8000:80)
EXPOSE 80

# Start the API on port 80 so host:8000 -> container:80 works as configured
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "80"]