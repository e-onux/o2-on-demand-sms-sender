# O2 On-Demand SMS Sender

This project automates the free `WEITER` SMS used to request another 2 GB of
high-speed data for O2 Unlimited On Demand plans. It runs continuously against
a supported Huawei LTE/5G modem and includes a cross-platform desktop control
panel.

Supported modem models depend on
[huawei-lte-api](https://github.com/Salamek/huawei-lte-api).

## How it works

The worker checks the modem once per minute by default. It sends `WEITER` when
either condition is met:

- the configured new-data threshold is reached (1.9 GiB by default, allowing
  for reporting delay around O2's 2 GB boundary), or
- an O2 SMS reports that 80% of the high-speed allowance has been used or that
  the allowance is exhausted.

An O2 trigger immediately moves the usage baseline to the verified current byte
counter. Periodic threshold checks then continue from that new baseline.
Processed trigger messages are fingerprinted so a retained message cannot send
the same reply again.

The incoming and sent SMS folders are treated as one timeline. Only the newest
three messages are retained by default. Runtime event history, processed
fingerprints, Docker logs, and the GUI log view are all bounded for long-running
installations.

### Slow-connection recovery

The worker also watches the connection itself. Every run times a tiny HTTP
request to a few public connectivity-check endpoints; a 1 MB download probe runs
every 15 minutes (about 100 MB/day) and on every run while a slowdown is being
confirmed. A probe counts as slow below 5 Mbit/s, or below 35% of the line's
usual healthy speed once enough history exists; very high latency also counts.
Probes that fail outright (DNS or routing errors inside Docker, for example)
never trigger an action, because a modem restart cannot fix them; the control
panel shows "cannot measure" instead.

The 4G signal (RSRP/SINR) is read from the modem every run and shown as a
coloured strip under the chart. When it is weak (RSRP below -105 dBm or SINR
below 0 dB) the restart notification SMS says so, for example
`Modem yeniden baslatiliyor. 4G sinyal zayif: RSRP -112 dBm, SINR -3 dB.`
The existing modem-ping watch and this recovery share one restart marker, and
this recovery waits 10 minutes after any automatic restart before deciding.

When the connection stays slow, recovery escalates instead of looping:

1. two slow measurements in a row: send `WEITER` once;
2. still slow two minutes later: restart the modem;
3. further restarts only after 30 min, 3 h, 6 h, 12 h, then 24 h, and never
   more than 4 restarts in any 24 hours.

The ladder resets only after an hour of healthy probes, so a rainy day with a
weak signal costs at most a few restarts. The control panel charts latency and
download speed for the last 1, 6 or 24 hours and shows the current phase. Set
`WATCHDOG_ENABLED=false` to turn the feature off; the SMS renewal is unaffected.

## Configuration

Copy the example environment file and add the modem credentials:

```bash
cp .env.example .env
```

Important settings:

```dotenv
API_USER=your_username_here
API_PASSWORD=your_password_here
MODEM_HOST=192.168.8.1
INTERVAL_SECONDS=60
SMS_THRESHOLD_GB=1.9
SMS_RETENTION_COUNT=3
TZ=Europe/Berlin

# Slow-connection recovery (defaults shown)
WATCHDOG_ENABLED=true
WATCHDOG_MIN_DOWNLOAD_MBPS=5
WATCHDOG_RELATIVE_SLOW_FACTOR=0.35
WATCHDOG_SLOW_PING_MS=400
WATCHDOG_SPEED_INTERVAL_SECONDS=900
WATCHDOG_SMS_WAIT_SECONDS=120
WATCHDOG_RESTART_BACKOFF_MINUTES=30,180,360,720,1440
WATCHDOG_RECOVERY_SECONDS=3600
WATCHDOG_MAX_RESTARTS_PER_DAY=4
```

Advanced: `WATCHDOG_PING_TARGETS` (default
`cp.cloudflare.com/generate_204,connectivitycheck.gstatic.com/generate_204,www.msftconnecttest.com/connecttest.txt`),
`WATCHDOG_SPEED_URL`, `WATCHDOG_SPEED_BYTES`, `WATCHDOG_CONFIRM_COUNT`.

## Run with Docker Compose

```bash
docker compose up -d --build
docker compose logs -f o2-ondemand-sms
```

Persistent status, event history, and the SMS threshold baseline are stored in
`./data` and bind-mounted at `/app/data`. Keep this directory when recreating
the container.

See [README.DOCKER.md](README.DOCKER.md) for Portainer and Docker image build
details.

## Run directly with Python

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python o2_on_demand_hack.py
```

On Windows, activate the environment with `venv\Scripts\activate` and use the
corresponding Python executable.

## Desktop control panel

The Tkinter control panel is located under `gui/`. It can:

- update and operate the Docker Compose service;
- show service health, verified daily usage, SMS statistics, thresholds,
  errors, recent events, and Docker logs;
- chart connection latency and download speed and show the slow-connection
  recovery phase;
- send a confirmed manual `WEITER` SMS or restart the modem after a separate warning;
- clear the modem SMS inbox and copy or clear event history;
- disable Docker-dependent controls while Docker Engine is unavailable, and
  modem controls while the worker service is not running;
- switch between Turkish, English, German, Polish, and Russian;
- minimize to the system tray and optionally start minimized at user login.

Run it from source:

```bash
python3 gui/src/control_panel.py
```

Platform builds are written under `gui/build`. Build and installation details
are documented in [gui/README.md](gui/README.md). Docker Desktop or Docker Engine
must be running for service controls and status collection.

## Tests

```bash
venv/bin/python -m unittest discover -s tests -v
```

The suite covers modem date parsing, verified counter resets, trigger
idempotency, SMS retention, long-running event compaction, decimal usage
display, slow-connection escalation and its daily cap, translations, action availability, confirmation gates, and desktop
project discovery.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
