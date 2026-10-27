# One image for all Python services; docker-compose.yml picks the command.
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY plc_simulator plc_simulator
COPY gateway gateway
COPY cloud cloud

ENV PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 1000 app && mkdir /data && chown app /data
USER app
