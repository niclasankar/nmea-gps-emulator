#!/bin/bash

echo ">>> Activating the virtual environment"
source venv/bin/activate

echo ">>> Run the Python script main.py"
python ./src/nmea_gps_emulator/main.py

echo ">>> Deactivate the virtual environment"
#deactivate
