#!/usr/bin/env bash
set -e

# Load env from .env if present. Variables already set by Compose/Portainer take
# precedence; .env only fills in the ones that are missing or empty.
if [ -f "/app/.env" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    case "$line" in ''|'#'*) continue ;; esac
    key="${line%%=*}"
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    if [ -z "${!key:-}" ]; then
      value="${line#*=}"
      value="${value%\"}"; value="${value#\"}"
      value="${value%\'}"; value="${value#\'}"
      export "$key=$value"
    fi
  done < /app/.env
fi

# Start supervisor
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
