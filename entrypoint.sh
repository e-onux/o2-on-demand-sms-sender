#!/usr/bin/env bash
set -e

# Load env from .env if present (Portainer environment variables still take precedence)
if [ -f "/app/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . /app/.env
  set +a
fi

# Start supervisor
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
