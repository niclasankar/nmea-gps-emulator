# GPS NMEA Emulator

[![Python 3.12.0](https://img.shields.io/badge/python-3.12.0-blue.svg)](https://www.python.org/downloads/release/python-385/)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)

The **GPS NMEA Emulator** is a simple script that emulates a GPS receiver (simulates unit's movement). Data generated by the script are sent to clients in **NMEA 0183** format. 
This script can be useful for testing applications or systems that require some unit's GPS position data.

The script is a highly modified script based on the script originally created by GitHub user [luk-kop](https://github.com/luk-kop/nmea-gps-emulator/) and published on GitHub.
The code has been documented and modified to use decimal coordinates, to allow input of altitude, logging to file and other changes.

The **GPS NMEA Emulator** script can be used in one of the following operating modes:
- NMEA TCP Stream (sends TCP packets to the specified client),
- NMEA UDP Stream (sends UDP packets to the specified client),
- NMEA TCP Server (the server waits for client connections, then sends TCP packets to the connected clients - max 10 connections)
- NMEA Serial (transmit serial data on specified RS port).
- NMEA messages filtered by type logged to a file
***
## Features
- The script allows the user to enter the following data:
  - unit's position;
  - unit's speed;
  - unit's course;
  - unit's altitude
  - operating mode selection (NMEA Serial, NMEA TCP Server, NMEA TCP or UDP Stream);
  - IP address & port pair or serial port name.
- After the NMEA data transmission has started, the script allows the user to interactively change the speed and course of the unit.
- Generated NMEA sentences are resent to the selected clients periodically (every second). Each time a data with NMEA sentences is sent, the position of the unit is updated based on its speed and course.

List of NMEA sentences generated by **GPS NMEA Emulator** script:
```
GPGGA - Global Positioning System Fix Data
GPGLL - Position data: position fix, time of position fix, and status
GPRMC - Recommended minimum specific GPS/Transit data
GPGSA - GPS DOP and active satellites
GPGSV - GPS Satellites in view
GPHDT - True Heading
GPVTG - Track made good and ground speed
GPZDA - Date & Time
```
Output example:
```
$GPGGA,173124.00,5430.000,N,01921.029,E,1,09,0.92,15.2,M,32.5,M,,*6C
$GPGSA,A,3,22,11,27,01,03,02,10,21,19,,,,1.56,0.92,1.25*02
$GPGSV,4,1,15,26,25,138,53,16,25,091,67,01,51,238,77,02,45,085,41*79
$GPGSV,4,2,15,03,38,312,01,30,68,187,37,11,22,049,44,09,67,076,71*77
$GPGSV,4,3,15,10,14,177,12,19,86,235,37,21,84,343,95,22,77,040,66*79
$GPGSV,4,4,15,08,50,177,60,06,81,336,46,27,63,209,83*4C
$GPGLL,5430.000,N,01921.029,E,173124.000,A,A*59
$GPRMC,173124.000,A,5430.000,N,01921.029,E,10.500,90.0,051121,,,A*65
$GPHDT,90.0,T*0C
$GPVTG,90.0,T,,M,10.5,N,19.4,K*51
$GPZDA,173124.000,05,11,2021,0,0*50
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

In order to use **NMEA Serial** mode correctly, it is necessary to use dedicated serial **null modem** cable or a virtual pipe.

On Linux systems you will probably need to change the permissions for the device matching your serial port before running the script.
```bash
# Example command for /dev/ttyS0 device
sudo chmod a+rw /dev/ttyS0
```

### Installation with virtual environment
The script can be build and run locally with virtualenv tool. Run following commands in order to create virtual environment and install the required packages.
```bash
$ python -m venv /path/to/new/virtual/environment
$ source venv/bin/activate
(venv) $ pip install pyproj
(venv) $ pip install pyserial
(venv) $ pip install psutil
(venv) $ pip install pygeomag
```
### Running the script
You can start the script using the following command:
```bash
(venv) $ python main.py
```
After starting the script correctly, the following prompt should appear in the console:

```bash
┳┓┳┳┓┏┓┏┓  ┏┓     ┓             
┃┃┃┃┃┣ ┣┫  ┣ ┏┳┓┓┏┃┏┓╋┏┓┏┓      
┛┗┛ ┗┗┛┛┗  ┗┛┛┗┗┗┻┗┗┻┗┗┛┛       
                                
 based on source code by luk-kop

### Choose emulator mode:            ###
### -------------------------------- ###
1 - NMEA Serial port output
2 - NMEA TCP Server
3 - NMEA TCP or UDP Stream
4 - NMEA output to log
0 - Quit
>>>
```

After selecting the mode, user is prompted for use of predefined points of interests (POI) stored in a JSON file.
```bash
Do you want to use a predefined starting point? (Y/N)
>>> Y
POI:s
1 - Gothenburg, Scandinavium Arena, (11.988E, 57.700105N)
2 - Helsingborg, Knutpunkten, (12.696E, 56.042846N)
3 - London, Prime Meridian, (0.000E, 51.477885N)
4 - San Fransisco, Golden Gate Bridge, (122.478W, 37.818570N)
>>> 4
´´´
If the user chooses to use a POI (Y) the user is prompted with a list of stored POIS:s.

If the user chooses to manually input (N) the position data the user is prompted
for input of latitude, longitude, speed, heading and altitude.

```bash
### Enter unit position latitude (defaults to 57.70011131502446): ###
>>> 59.27567459

### Enter unit position latitude hemisphere (defaults to N): ###
>>> N

### Enter unit position longitude (defaults to 11.988278521104876): ###
>>> 15.21254755

### Enter unit position longitude hemisphere (defaults to E): ###
>>> E

### Enter unit course - range 000-359 degrees (defaults to 45): ###
>>> 45

### Enter unit speed in knots - range 0-999 (defaults to 2 knots): ###
>>> 2

### Enter unit altitude in meters above sea level - range -40-9000 (defaults to 42): ###
>>> 42
```

### Filtering messages when logging
When logging mode i chosen can the NMEA messages be filtered by type to allow testing and debugging. The input below will be shown after coordinate input.

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
### Creating the poi.json file
The poi.json file should be located alongside the script and should have the following structure.
```bash
[
    {
        "name": "Gothenburg, Scandinavium Arena",
        "lat": 57.70010540643474,
        "lat_d": "N",
        "lon": 11.988275923454133,
        "lon_d": "E",
        "alt": 4,
        "head": 260.0
    },
    {
        "name": "Helsingborg, Knutpunkten",
        "lat": 56.042846426281685,
        "lat_d": "N",
        "lon": 12.696462909108408,
        "lon_d": "E",
        "alt": 3,
        "head": 300.0
    }
]
```

### Starting the script with a config file
The script can be run by supplying a JSON config file with the starting point and type of output. The config file is given via the argument -c in the call
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
    "lat_d": "N",
    "lon": 11.988275923454133,
    "lon_d": "E",
    "alt": 4,
    "head": 260.0,
    "speed": 2
}
´´´