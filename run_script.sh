#!/bin/bash

cd "$(dirname "$0")"
source venv/bin/activate
python o2_on_demand_hack.py
deactivate