# O2 On-Demand SMS — Docker/Portainer & CI

This bundle adds **Docker**, **supervisord**, and **GitHub Actions** on top of the original project so you can run it under Portainer and build multi-arch images automatically.

## Run on Portainer (Stack)
1. Go to **Stacks > Add stack** in Portainer and paste `docker-compose.yml`.
2. Provide environment variables:
   - `API_USER`, `API_PASSWORD` (required)
   - `MODEM_HOST` (default: `192.168.8.1`)
   - `INTERVAL_SECONDS` (default: `60` seconds; controls O2 trigger polling)
   - `SMS_THRESHOLD_GB` (default: `1.9` GiB; legacy variable name)
   - `SMS_RETENTION_COUNT` (default: `3`; newest incoming/sent messages kept as one timeline)
   - `TZ` (default: `Europe/Berlin`)
3. Deploy. Check logs at **Containers > o2-ondemand-sms > Logs**.

The Compose stack stores status, event history, and the current SMS threshold
baseline in `./data`. Keep this directory when rebuilding or recreating the
container.

Docker logs rotate at 5 MB with three files. Runtime event history is compacted
automatically after 2 MB, retaining at most the newest 2,000 records.

> Using `network_mode: host` is recommended to reach modem IPs (e.g., Huawei at 192.168.8.1) without NAT issues.

## Local Docker (optional)
```bash
docker build -t YOUR_DOCKERHUB_USER/o2-ondemand-sms:latest .
docker run --rm --network host       -e API_USER=xxx -e API_PASSWORD=yyy       -e MODEM_HOST=192.168.8.1 -e INTERVAL_SECONDS=600       YOUR_DOCKERHUB_USER/o2-ondemand-sms:latest
```

## GitHub Actions (Multi-arch Build)
The workflow in `.github/workflows/docker-build.yml` builds `linux/arm/v7`, `linux/arm64`, and `linux/amd64` images and pushes to DockerHub on each `push` (and via manual dispatch).

Create repo secrets under **Settings > Secrets and variables > Actions**:
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN` (DockerHub Access Token)

Adjust `tags:` in the workflow to match your DockerHub namespace.
