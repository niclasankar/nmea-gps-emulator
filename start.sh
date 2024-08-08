#!/bin/bash

# Activate the virtual environment
source venv/bin/activate

# Run the Python script
python ./src/nmea_gps_emulator/main_gui.py

# Deactivate the virtual environment (optional)
deactivate
