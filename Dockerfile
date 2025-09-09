# Dockerfile for O2 On-Demand SMS Sender
FROM python:3.12-slim

# Install supervisor and basics
RUN apt-get update && apt-get install -y --no-install-recommends           supervisor bash tzdata ca-certificates         && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies provided by the repo
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of the project (your Python scripts are in your repo)
COPY . /app

# Supervisor config + entrypoint
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Unbuffered stdout for real-time logs
ENV PYTHONUNBUFFERED=1
ENV TZ=Europe/Berlin

# Healthcheck: watch the supervisor program status
HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD       supervisorctl status sms-runner || exit 1

ENTRYPOINT ["/entrypoint.sh"]
