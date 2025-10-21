FROM python:3.12-slim

WORKDIR /app

# System deps (psycopg, build tools)
RUN apt-get update && apt-get install -y \
    build-essential curl libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
# Use wheels cache if you like; for now keep it simple
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest (mounted in compose for hot-reload, but present for build)
COPY . /app

# Django runs via compose command
EXPOSE 8000