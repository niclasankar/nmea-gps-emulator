# GPS NMEA Emulator

[![Python 3.10.0](https://img.shields.io/badge/python-3.10.0-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)

The GPS NMEA Emulator is a simple script that emulates a GPS receiver (simulates unit's movement). 
Data generated by the script are sent to clients in NMEA 0183 format. 
This script can be useful for testing applications or systems that require some unit's GPS position data.

The script is a highly modified script based on the script originally published by GitHub user [luk-kop](https://github.com/luk-kop/) and published on GitHub.
The code has been documented and modified in many ways:
 - use decimal coordinates
 - allow input of altitude
 - output through logging to file
 - storing of points of interest in file
 - input of custom point of interest file
 - starting with a base config in a JSON file
 - other changes...
The script is also available in a version with a GUI created with PySide6 (experimental).

The GPS NMEA Emulator script can be used in one of the following operating modes:
- NMEA TCP Stream (sends TCP packets to the specified client),
- NMEA UDP Stream (sends UDP packets to the specified client),
- NMEA TCP Server (the server waits for client connections, then sends TCP packets to the connected clients - max 10 connections),
- NMEA Serial (transmit serial data on specified serial port),
- NMEA messages filtered by type logged to a file

## Features
- The script allows the user to enter the following data:
  - unit's position
  - unit's speed
  - unit's course
  - unit's altitude
  - operating mode selection (NMEA Serial, NMEA TCP Server, NMEA TCP or UDP Stream)
  - IP address & port pair or serial port name
- Some of the input to the script can be supplied in the start command via a config JSON file.
- Predefined points of interest can be supplied in a JSON file.
- After the NMEA data transmission has started, the script allows the user to interactively change the speed, course and altitude of the unit.
- Generated NMEA sentences are resent to the selected clients periodically (every second). Each time a data with NMEA sentences is sent, the position of the unit is updated based on its speed, course and altitude.

List of NMEA sentences generated by the script:
```
GPGGA - Time, position, and fix related data
GPGLL - Position data: position fix, time of position fix, and status
GPRMC - Position, velocity, and time
GPGSA - GPS DOP and active satellites
GPGSV - GSV message string identifies the number of SVs in view, the PRN numbers, elevations, azimuths, and SNR values.
GPHDT - True Heading
GPVTG - Track made good and ground speed
GPZDA - Date & Time
```

Output example:
```
$GPGGA,125638.00,3853.35778,N,07703.01251,W,1,12,0.92,9,M,11.5,M,,*58
$GPGSA,A,3,02,28,06,19,01,09,14,03,16,05,13,17,1.56,0.92,1.25*03
$GPGSV,4,1,15,19,90,135,25,28,58,234,87,01,62,215,21,03,50,219,25*7F
$GPGSV,4,2,15,02,11,295,14,20,61,220,71,06,81,354,39,16,48,095,82*7B
$GPGSV,4,3,15,05,45,275,10,17,78,098,72,29,85,143,95,23,35,154,93*73
$GPGSV,4,4,15,13,89,187,57,09,24,238,71,14,76,352,31*40
$GPGLL,3853.35778,N,07703.01251,W,125638.000,A,A*47
$GPRMC,125638.000,A,3853.35778,N,07703.01251,W,2.000,270.0,030824,010.71,W,A*34
$GPHDT,270.0,T*30
$GPVTG,270.0,T,259.3,M,2,N,3.7,K*5E
$GPZDA,125638.000,03,08,2024,0,0*52
```

***
## Getting Started

Below instructions will get you a copy of the project up and running on your local machine.

### Requirements

Python third party packages:
* [pyproj](https://pypi.org/project/pyproj/)
* [pyserial](https://pypi.org/project/pyserial/)
* [psutil](https://pypi.org/project/psutil/)
* [pygeomag](https://pypi.org/project/pygeomag/)
* [timezonefinder](https://pypi.org/project/timezonefinder/)
* [pytz](https://pypi.org/project/pytz/)
* [PySide6](https://pypi.org/project/PySide6/)

In order to use NMEA Serial port output mode correctly, it is necessary to use dedicated 
serial null modem cable, a virtual serial port or a virtual pipe if running in a virtual machine.
The available ports are listed at runtime.

On Linux systems you will probably need to change the permissions for the device matching 
your serial port before running the script.
```bash
# Example command for /dev/ttyS0 device
sudo chmod a+rw /dev/ttyS0
```

### Installation with virtual environment
The script can be executed locally with the virtualenv tool. Create and activate
the virtual environment by running the following commands and install the required packages. 
PySide is only needed if you want to run the GUI.
```bash
$ python -m venv /path/to/new/virtual/environment
$ source venv/bin/activate
(venv) $ pip install pyproj
(venv) $ pip install pyserial
(venv) $ pip install psutil
(venv) $ pip install pygeomag
(venv) $ pip install pytz
(venv) $ pip install timezonefinder
(venv) $ pip install PySide6
```
### Running the script
You can start the script using the following command:
```bash
(venv) $ python3 main.py
```
After starting the script correctly, the following prompt should appear in the console:

```bash
┳┓┳┳┓┏┓┏┓  ┏┓     ┓             
┃┃┃┃┃┣ ┣┫  ┣ ┏┳┓┓┏┃┏┓╋┏┓┏┓      
┛┗┛ ┗┗┛┛┗  ┗┛┛┗┗┗┻┗┗┻┗┗┛┛       
                                
 based on source code by luk-kop

 ### Choose emulator output mode:     ###
 ### -------------------------------- ###
 1 - NMEA Serial port output
 2 - NMEA TCP Server
 3 - NMEA TCP or UDP Stream
 4 - NMEA output to log file
 0 - Quit
 >>>
```

### Input of starting point
After selecting the mode, user is prompted for use of predefined points of interests (POI) stored in a JSON file.
If the user chooses to use a POI (Y) the user is prompted with a list of stored POIS:s.

```bash
 Do you want to use a predefined starting point? (Y/N)
 >>> Y
Showing points from: ...
 1 - Washington, Capitoleum, (38.889296°N, -77.050°W)
 2 - London, Prime Meridian, (51.477885°N, 0.000°E)
 3 - Japan, Mount Fuji, (35.360555°N, 138.727°E)
 4 - San Fransisco, Golden Gate Bridge, (37.818570°N, -122.478°W)
 5 - Buenos Aires, Airport, (-34.560427°S, -58.414°W)
 6 - Howland Island, United States (-12 GMT), (0.805653°N, -176.619°W)
 7 - East Cape Lighthouse, New Zeeland (+12 GMT), (-37.688998°S, 178.548°E)
 >>> 2
```

If the user chooses to manually input (N), the user will be prompted
for input of latitude, longitude, speed, heading and altitude.
Longitudes west of Greenwich and latitudes on the south hemisphere are
entered by negative values. 

```bash
 Enter unit position latitude (defaults to 38.889296):
    (Negative for southern hemisphere)
 >>> 59.27567459

 Enter unit position longitude (defaults to -77.050):
    (Negative for west of Greenwich)
 >>> 15.21254755

 Enter unit course - range 000-359 degrees (defaults to 260):
 >>> 45

 Enter unit speed in knots - range 0-999 (defaults to 2 knots):
 >>> 2

 Enter unit altitude in meters above sea level - range -40-9000 (defaults to 42):
 >>> 42
```

### Filtering messages when logging
When in logging mode (4) can the NMEA messages be filtered by type to allow testing
and debugging or to create files for import to parsers. The input below will be shown
after coordinate input.
```bash
 Choose filter:
    1 - GPGGA,
    2 - GPGLL,
    3 - GPRMC,
    4 - GPGSA,
    5 - GPGSV,
    6 - GPHDT,
    7 - GPVTG,
    8 - GPZDA,
    0 - No filter
 >>> 1
```
### Creating the poi.json file or custom point of interest file
The poi.json file should be located in the folder 'pois' alongside the script and should have the following structure.
```bash
[
    {
        "name": "San Fransisco, Golden Gate Bridge",
        "lat": 37.81856987,
        "lng": -122.47846487,
        "alt": 100,
        "head": 340.0
    },
    {
        "name": "Buenos Aires, Airport",
        "lat": -34.56042729,
        "lng": -58.41363783,
        "alt": 100,
        "head": 340.0
    }
]
```
A custom POI file can also be created and can be called at runtime with the argument '-p filename_with_full_path'.

### Starting the script with a config file (experimental)
The script can be run by supplying a JSON config file with the starting point and type
of output. The config file is given via the argument -c in the call. Config files are placed in the sub folder 'confs'
The script runs and asks for serial port, ip address and data that is unique for each run.

```bash
(venv) $ python main.py -c conf.json
```

Below is a example of a config file
```bash
{
    "name": "Gothenburg, Scandinavium Arena, with Stream output",
    "output": 3,
    "lat": 57.70010540643474,
    "lng": 11.988275923454133,
    "alt": 38,
    "head": 230.0,
    "speed": 2
}
```

### Running the script with a GUI (experimental)
The script can be run with a Qt GUI.

```bash
(venv) $ python main_gui.py
```
### Controling the unit
When running the script the unit's position can be controlled by entering new input data.
To start the input sequence press the ENTER button when the text below is visible.
A series of values are requested and the values are controlled.
When all new values are given and the script is ready changing the speed, heading or altitude a text is shown with the values.
```bash
 Press "Enter" to change course/speed/altitude or "Ctrl + c" to exit...

 Enter new course or press "Enter" to skip (Target 260.0)
 >>> 255

 Enter new speed or press "Enter" to skip (Target 0)
 >>> 10

 Enter new altitude or press "Enter" to skip (Target 4)
 >>> 32
 
 All updates ready...
 Latitude: 57.70009968259188°N
 Longitude: 11.988229663475428°E
 Altitude: 4 m
 Speed: 10.0 kt
 Heading: 255.0°

 Press "Enter" to change course/speed/altitude or "Ctrl + c" to exit...
 ```

## NMEA messages warnings

### GPZDA
The time zone offset given in the messages is the one for the starting
position and it is not recalculated as the unit moves to save system
resources.

### GPGGA
The antenna altitude is always 2.5 meters above the calculated altitude
