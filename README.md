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
```

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
- send a confirmed manual `WEITER` SMS;
- clear the modem SMS inbox and copy or clear event history;
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
display, translations, and desktop project discovery.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
