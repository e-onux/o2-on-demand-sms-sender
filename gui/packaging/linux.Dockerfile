FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        binutils \
        libpython3.12 \
        python3 \
        python3-pip \
        python3-tk \
        python3-venv \
        xauth \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY gui/requirements-build.txt /tmp/requirements-build.txt
RUN python3 -m venv /opt/gui-build \
    && /opt/gui-build/bin/python -m pip install --disable-pip-version-check \
        -r /tmp/requirements-build.txt
