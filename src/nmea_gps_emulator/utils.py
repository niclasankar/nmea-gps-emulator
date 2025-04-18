"""
Module for utilities in NMEA-GPS-EMULATOR containing:
- Input methods
- Log methods
- Helpers

Created in 2024
Based on the works of luk-kop

:author: ankars
:copyright: Ankars.se © 2024
:license: MIT
"""

import re
import sys
import os
import time
import platform
import logging
import json
import socket
import psutil
import serial.tools.list_ports

#from nmea_utils import ddd2nmea, ll2dir
from nmea_utils import ll2dir

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

default_position_dict = {
    "lat": 57.70011131,
    "lng": 11.98827852,
}
default_speed = 0
default_alt = 42
default_head = 260

# List of filters for use in logging
filters_dict = {
    1: {"$GPGGA": "Fix data and undulation (GPGGA)"},
    2: {"$GPGLL": "Geographic position (GPGLL)"},
    3: {"$GPRMC": "GPS specific information (GPRMC)"},
    4: {"$GPGSA": "GPS DOP and active satellites (GPGSA)"},
    5: {"$GPGSV": "GPS satellites in view (GPGSV)"},
    6: {"$GPHDT": "NMEA heading (GPHDT)"},
    7: {"$GPVTG": "Track made good and SOG (GPVTG)"},
    8: {"$GPZDA": "UTC time/date (GPZDA)"},
    9: {"$GPZDA": "UTC time/date", "$GPGLL": "Geographic position"},
    10: {"$GPZDA": "UTC time/date", "$GPGLL": "Geographic position", "$GPGSV": "GPS satellites in view"},
    11: {"$GPGLL": "Geographic position", "$GPGSV": "GPS satellites in view"},
    0: "No filter"
}
default_ip = "127.0.0.1"
default_port = 10110
default_telnet_port = 10110

def output_message(message_str, newline_mode = True):
    """
    Output of messages to user.

    :param string message_str: message to output
    :param bool newline_mode: should the message be surrounded by newlines
    """
    if newline_mode:
        print("\n\n " + message_str)
    else:
        print(" " + message_str)

def output_listrow(message_str, listsign_str = "-"):
    """
    Output row in list to user.
    The row is indented with blanks and a list char

    :param string message_str: message to output
    :param string listsign_str: chars to use before list row
    """
    print(f"   {listsign_str} {message_str}")
    
def output_error(message_str, newline_mode = True):
    """
    Output of error message to user.

    :param string message_str: message to output
    :param bool newline_mode: should the message be surrounded by newlines
    """
    if newline_mode:
        print("\n\n " + "\033[0;36;41m--- " + message_str + " ---\033[0;37;40m\n")
    else:
        print("\033[0;36;41m--- " + message_str + " ---\033[0;37;40m\n")

def input_prompt(message_str = ""):
    """
    Input prompt with message to user.

    :param string message_str: message to output
    :return: input string defaults to "" which gives a >>> prompt
    :rtype: str
    """
    default_prompt = " >>> "
    if message_str:
        return input("\n " + message_str + "\n" + default_prompt)
    else:
        return input(" " + default_prompt)

def exit_script():
    """
    The method terminates the script (main thread) from inside of
    child thread
    """
    current_script_pid = os.getpid()
    current_script_proc = psutil.Process(current_script_pid)
    output_error(f"Closing the script ({current_script_pid})...")
    time.sleep(1)
    current_script_proc.terminate()

def filter_input():
    """
    The method asks for type of messages to log

    :return: filter message id as string
    :rtype: str
    """
    output_message("Choose message filter:")
    for x, y in filters_dict.items():
        if isinstance(y, dict):
            filters_str = ", ".join(y.values())
            output_listrow(filters_str, x)
        else:
            output_listrow(y, x)
    
    try:
        filter_choice = input(" >>> ")
        mo = re.match("^\\d+$", filter_choice)
        if mo:
            # Filter is first match group
            filter = int(mo.group())
        else:
            # No filter
            filter = 0
    except KeyboardInterrupt:
        output_error("Closing the script...")
        sys.exit()

    filter_type = filters_dict.get(filter)

    if filter != 0:
        if isinstance(filter_type, dict):
            output_message(f"Filtering messages by type {", ".join(filter_type.values())}.\n")
        else:
            output_message(f"Filtering messages by type {filter_type}.\n")
    else:
        output_message("No message filtering active.\n")
        filter_type = ""

    return filter_type

def poi_input(poi_file: str):
    """
    The method reads the poi file and asks for user choice.
    POI file must contain posts formed like below
    [{
        "name": "East Cape Lighthouse, New Zeeland (+12 GMT)",
        "lat": -37.68899790444831,
        "lng": 178.54812819713842,
        "alt": 154,
        "head": 90.0
    }]

    :param string poi_file: optional file name with complete path
    :return: position dictionary, float altitude, float heading
    :rtype: tuple (dict, float, float) (None, None, None) on error
    :raises: json.JSONDecodeError when JSON content is malformed
    """
    pos_dict = default_position_dict
    try:
        # Listing of and input of selected POI
        while True:
            if poi_file != "":
                if os.path.isabs(poi_file):
                    # The argument is a absolute path and can be used as-is
                    poi_filename_path = poi_file
                else:
                    # Assume the input is a filename and append it to the default directory
                    poi_filename_path = os.path.join(__location__, "pois", poi_file)
            else:
                # If no poi file was given use the default
                poi_filename = "poi.json"
                poi_filename_path = os.path.join(__location__, "pois", poi_filename)

            if os.path.exists(poi_filename_path):
                output_message("Showing points from: " + poi_filename_path)
                with open(poi_filename_path, "r") as file:
                    poi_list = json.load(file)

                # Add a number to each object in the list
                for index, item in enumerate(poi_list, start=1):
                    item["uid"] = index

                # Loop through each object in the list
                for poi in poi_list:
                    lat_dir = ll2dir(poi["lat"], "lat")
                    lng_dir = ll2dir(poi["lng"], "lng")
                    output_listrow(f"{poi["name"]}, " +
                                   f"({poi["lat"]:2f}°{lat_dir}, " +
                                   f"{poi["lng"]:3.3f}°{lng_dir})", poi["uid"])

                # Get the chosen POI
                selected_uid = int(input(" >>> "))
                sel_poi_item = None
                for poi_item in poi_list:
                    if poi_item.get("uid") == selected_uid:
                        sel_poi_item = poi_item

                if sel_poi_item != None:
                    pos_dict["lat"] = sel_poi_item["lat"]
                    pos_dict["lng"] = sel_poi_item["lng"]
                    # Return position dictionary, alt and heding
                    return pos_dict, sel_poi_item["alt"], sel_poi_item["head"]
                else:
                    output_error("Non valid POI choice. Continue with manual input.")
                    return None, None, None
            else:
                output_error("The POI file doesn't exist!")
                output_error("Create the POI file according to docs or supply the path to the file with argument -p.", False)
                output_message("Continuing with manual input.")
                time.sleep(2)
                return None, None, None
            
    except json.JSONDecodeError as jsonerr:
        output_error(f"Could not parse the supplied JSON file. Continuing with manual input. ({jsonerr.msg})")
        return None, None, None
    except KeyboardInterrupt:
        output_error("Closing the script...")
        sys.exit()

def position_sep_input() -> dict:
    """
    The method asks for position and checks validity of entry data.

    :return: dictionary containing latitude, longitude and lat/lon directions
    :rtype: dictionary
    """
    position_dict = default_position_dict
    try:
        # Input of latitude
        while True:
            output_message("Enter unit position:")
            try:
                output_message(f"Latitude (defaults to {default_position_dict["lat"]}).", False)
                output_message(f"Negative value for southern hemisphere.", False)
                latitude_data = input_prompt("Latitude:")
            except KeyboardInterrupt:
                output_error("Closing the script...")
                sys.exit()
            # Input is empty, use default value
            if latitude_data == "":
                latitude_data = float(default_position_dict["lat"])
                position_dict["lat"] = latitude_data
                break
            latitude_regex_pattern = r"^(\+|-)?(?:90(?:(?:\.0{1,14})?)|(?:[0-9]|[1-8][0-9])(?:(?:\.[0-9]{1,14})?))$"
            mo = re.fullmatch(latitude_regex_pattern, str(latitude_data))
            if mo:
                position_dict["lat"] = float(mo.group())
                break
        # Input of longitude
        while True:
            try:
                output_message(f"Longitude (defaults to {default_position_dict["lng"]}):", False)
                output_message(f"Negative value for west of Greenwich)", False)
                longitude_data = input_prompt("Longitude:")
            except KeyboardInterrupt:
                output_error("Closing the script...")
                sys.exit()
            # Input is empty, use default value
            if longitude_data == "":
                longitude_data = float(default_position_dict["lng"])
                position_dict["lng"] = longitude_data
                break
            longitude_regex_pattern = r"^(\+|-)?(?:180(?:(?:\.0{1,6})?)|(?:[0-9]|[1-9][0-9]|1[0-7][0-9])(?:(?:\.[0-9]{1,14})?))$"
            mo = re.fullmatch(longitude_regex_pattern, str(longitude_data))
            if mo:
                position_dict["lng"] = float(mo.group())

        return position_dict
    except KeyboardInterrupt:
        output_error("Closing the script...")
        sys.exit()

def ip_port_input(option: str) -> tuple:
    """
    The method asks for IP address and port number for connection.

    :param string option: type of connection 
    :return: tuple containing IP address and port
    :rtype: tuple (string, int)
    """
    while True:
        try:
            if option == "telnet":
                #output_message(f"Enter Local IP address and port number (defaults to local ip: {get_ip()}:{default_telnet_port}):")
                try:
                    ip_port_socket = input_prompt(f"Enter Local IP address and port number (defaults to local ip: {get_ip()}:{default_telnet_port}):")
                except KeyboardInterrupt:
                    output_error("Closing the script...")
                    sys.exit()
                if ip_port_socket == "":
                    # All available interfaces and default NMEA port.
                    return (get_ip(), default_port)
            elif option == "stream":
                output_message(f"Enter Remote IP address and port number (defaults to {default_ip}:{default_port}):")
                try:
                    ip_port_socket = input(" >>> ")
                except KeyboardInterrupt:
                    output_error("Closing the script...")
                    sys.exit()
                if ip_port_socket == "":
                    return (default_ip, default_port)
            # Regex matchs only unicast IP addr from range 0.0.0.0 - 223.255.255.255
            # and port numbers from range 1 - 65535.
            ip_port_regex_pattern = re.compile(r'''^(
                ((22[0-3]\.|2[0-1][0-9]\.|1[0-9]{2}\.|[0-9]{1,2}\.)    # 1st octet
                (25[0-5]\.|2[0-4][0-9]\.|1[0-9]{2}\.|[0-9]{1,2}\.){2}  # 2nd and 3th octet
                (25[0-5]|2[0-4][0-9]|1[0-9]{2}|[0-9]{1,2}))            # 4th octet
                :
                ([1-9][0-9]{0,3}|[1-6][0-5]{2}[0-3][0-5])   # port number
                )$''', re.VERBOSE)
            mo = ip_port_regex_pattern.fullmatch(ip_port_socket)
            if mo:
                # return tuple with IP address (str) and port number (int).
                return (mo.group(2), int(mo.group(6)))
            output_error(f"Error: Wrong format use - 192.168.10.10:2020.")
        except KeyboardInterrupt:
            output_error("Closing the script...")
            sys.exit()

def trans_proto_input() -> str:
    """
    The method asks for transport protocol for NMEA stream.

    :return: transport protocol as lowercase string
    :rtype: str
    """
    while True:
        try:
            #output_message("Enter transport protocol - TCP or UDP (defaults to TCP):")
            try:
                stream_proto = input_prompt("Enter transport protocol - TCP or UDP (defaults to TCP):").strip().lower()
            except KeyboardInterrupt:
                output_error("Closing the script...")
                sys.exit()

            if stream_proto == "" or stream_proto == "tcp":
                return "tcp"
            elif stream_proto == "t":
                return "tcp"
            elif stream_proto == "udp":
                return "udp"
            elif stream_proto == "u":
                return "udp"
        except KeyboardInterrupt:
            output_error("Closing the script...")
            sys.exit()

def get_ip() -> str:
    """
    The method gets the first local IP address of the computer.

    :return: local IP address as string
    :rtype: str
    """
    sck = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sck.settimeout(0)
    try:
        # Doesn't even have to be reachable
        sck.connect(("10.254.254.254", 1))
        _ip_local = sck.getsockname()[0]
    except Exception:
        _ip_local = "127.0.0.1"
    finally:
        sck.close()
    output_message("Local IP address: " + _ip_local)
    return _ip_local

def heading_input() -> float:
    """
    The method asks for the unit's start heading.

    :return: unit's heading
    :rtype: float
    """
    while True:
        try:
            #output_message(f"Enter unit course - range 000-359 degrees (defaults to {default_head}):", False)
            try:
                heading_data = input_prompt(f"Enter unit course - range 000-359 degrees (defaults to {default_head}):")
            except KeyboardInterrupt:
                output_error("Closing the script...")
                sys.exit()
            if heading_data == "":
                return 45.0
            heading_regex_pattern = r"(3[0-5]\d|[0-2]\d{2}|\d{1,2})"
            mo = re.fullmatch(heading_regex_pattern, heading_data)
            if mo:
                return float(mo.group())
        except re.error as reerr:
            output_error("Error occurred: " + reerr.msg)
            output_error("Pattern: " + reerr.pattern, False)
            output_error("Position: " + reerr.pos, False)
            return 0.0
        except KeyboardInterrupt:
            output_error("Closing the script...")
            sys.exit()

def speed_input() -> float:
    """
    The method asks for the unit's starting speed.

    :return: unit's speed
    :rtype: float
    """
    while True:
        try:
            #output_message(f"Enter unit speed in knots - range 0-999 (defaults to {default_speed} knots):")
            try:
                speed_data = input_prompt(f"Enter unit speed in knots - range 0-999 (defaults to {default_speed} knots):")
            except KeyboardInterrupt:
                output_error("Closing the script...")
                sys.exit()
            if speed_data == "":
                return default_speed
            speed_regex_pattern = r"(\d{1,3}(\.\d)?)"
            mo = re.fullmatch(speed_regex_pattern, speed_data)
            if mo:
                match = mo.group()
                if match.startswith("0") and match != "0":
                    match = match.lstrip("0")
                return float(match)
        except re.error as reerr:
            output_error("Error occurred: " + reerr.msg)
            output_error("Pattern: " + reerr.pattern, False)
            output_error("Position: " + reerr.pos, False)
            return 0.0
        except KeyboardInterrupt:
            output_error("Closing the script...")
            sys.exit()

def alt_input() -> float:
    """
    The method asks for the unit's starting altitude.

    :return: unit's altitude
    :rtype: float
    """
    while True:
        try:
            #output_message(f"Enter unit altitude in meters above sea level - range -40-9000 (defaults to {default_alt}):")
            try:
                alt_data = input_prompt(f"Enter unit altitude in meters above sea level - range -40-9000 (defaults to {default_alt}):")
            except KeyboardInterrupt:
                output_error("Closing the script...")
                sys.exit()
            if alt_data == "":
                return default_alt
            alt_regex_pattern = r"(\d{1,3}(\.\d)?)"
            mo = re.fullmatch(alt_regex_pattern, alt_data)
            if mo:
                match = mo.group()
                if match.startswith("0") and match != "0":
                    match = match.lstrip("0")
                return float(match)
        except re.error as reerr:
            output_error("Error occurred: " + reerr.msg)
            output_error("Pattern: " + reerr.pattern, False)
            output_error("Position: " + reerr.pos, False)
            return 0.0
        except KeyboardInterrupt:
            output_error("Closing the script...")
            sys.exit()

def change_heading_input(self, heading_old: float) -> float:
    """
    The method asks for the unit's new  heading.

    :param float old_course: active course of unit
    :return: new course of unit
    :rtype: float
    """
    try:
        while True:
            try:
                output_message(f"Enter new course or press \"Enter\" to skip (Target {heading_old})", False)
                heading_data = input(" >>> ")
            except KeyboardInterrupt:
                output_error("Closing the script...")
                sys.exit()
            if heading_data == "":
                heading_new = heading_old
                break
            else:
                heading_regex_pattern = r"(3[0-5]\d|[0-2]\d{2}|\d{1,2})"
                mo = re.fullmatch(heading_regex_pattern, heading_data)
                if mo:
                    heading_new = float(mo.group())
                    break
        return heading_new
    except KeyboardInterrupt:
        output_error("Closing the script...")
        sys.exit()

def change_speed_input(self, speed_old:float) -> float:
    """
    The method asks for the unit's new speed.

    :param float old_speed: active speed of unit 
    :return: new speed of unit
    :rtype: float
    """
    try:
        while True:
            try:
                output_message(f"Enter new speed or press \"Enter\" to skip (Target {speed_old})", False)
                speed_data = input(" >>> ")
            except KeyboardInterrupt:
                output_error("Closing the script...")
                sys.exit()
            if speed_data == "":
                speed_new = speed_old
                break
            else:
                speed_regex_pattern = r"(\d{1,3}(\.\d)?)"
                mo = re.fullmatch(speed_regex_pattern, speed_data)
                if mo:
                    match = mo.group()
                    if match.startswith("0") and match != "0":
                        match = match.lstrip("0")
                    speed_new = float(match)
                    break
        return speed_new
    except KeyboardInterrupt:
        output_error("Closing the script...")
        sys.exit()

def change_altitude_input(self, altitude_old: float) -> float:
    """
    The method asks for the unit's new altitude.

    :param float old_altitude: active altitude of unit 
    :return: new altitude of unit
    :rtype: float
    """
    try:
        while True:
            try:
                output_message(f"Enter new altitude or press \"Enter\" to skip (Target {altitude_old})", False)
                alt_data = input(" >>> ")
            except KeyboardInterrupt:
                output_error("Closing the script...")
                sys.exit()
            if alt_data == "":
                altitude_new = altitude_old
                break
            else:
                alt_regex_pattern = r"(\d{1,3}(\.\d)?)"
                mo = re.fullmatch(alt_regex_pattern, alt_data)
                if mo:
                    match = mo.group()
                    if match.startswith("0") and match != "0":
                        match = match.lstrip("0")
                    altitude_new = float(match)
                    break
        return altitude_new
    except KeyboardInterrupt:
        output_error("Closing the script...")
        sys.exit()

def serial_config_input() -> dict:
    """
    The method is asking for serial settings
    Lists available ports for the user
    Complete serial config set should look like below:
    {
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
        "timeout": 1,
        "port": "/dev/ttyS0",
        "baudrate": 9600
    }

    :return: Dictionary storing serial settings
    :rtype: dict
    """
    # Dict with all serial port settings.
    serial_set = {"bytesize": 8,
                  "parity": "N",
                  "stopbits": 1,
                  "timeout": 1}

    # List of available serial ports.
    ports_connected = serial.tools.list_ports.comports(include_links=False)

    # List of available serial port's names.
    ports_connected_names = [port.device for port in ports_connected]
    output_message("Connected Serial Ports:", False)
    for port in sorted(ports_connected):
        output_listrow(port)
    
    # Check OS platform.
    platform_os = platform.system()

    # Asks for serial port name and checks the name validity.
    while True:
        if platform_os.lower() == "linux":
            output_message("Choose Serial Port (defaults to /dev/ttyS0):")
            try:
                serial_set["port"] = input(" >>> ")
            except KeyboardInterrupt:
                output_error("Closing the script...")
                sys.exit()
            if serial_set["port"] == "":
                serial_set["port"] = "/dev/ttyS0"
            if serial_set["port"] in ports_connected_names:
                break
        elif platform_os.lower() == "windows":
            output_message("Choose Serial Port (defaults to COM1):")
            try:
                serial_set["port"] = input(" >>> ")
            except KeyboardInterrupt:
                output_error("Closing the script...")
                sys.exit()
            if serial_set["port"] == "":
                serial_set["port"] = "COM1"
            if serial_set["port"] in ports_connected_names:
                break
        output_error(f"Error: '{serial_set["port"]}' is not a valid port name.")

    # Serial port settings:
    baudrate_list = ["300", "600", "1200", "2400", "4800", "9600", "14400",
                     "19200", "38400", "57600", "115200", "128000"]
    
    # Ask for baud rate, defaults to 9600 (NMEA standard)
    while True:
        output_message("Enter serial baudrate (defaults to 9600):")
        try:
            serial_set["baudrate"] = input(" >>> ")
        except KeyboardInterrupt:
            output_error("Closing the script...")
            sys.exit()
        if serial_set["baudrate"] == "":
            serial_set["baudrate"] = 9600
        if str(serial_set["baudrate"]) in baudrate_list:
            break
        output_error(f"Error: '{serial_set["baudrate"]}' is not a valid baudrate.")
    return serial_set

def _setup_logger(logger_name, log_file, log_format="%(message)s", level=logging.INFO):
    """
    The method creates a logging instance and returns it.

    :param str logger_name: Name of the logging instance
    :param str log_file: Name of the logging file
    :param str log_format: Logging format, defaults to %(message)s
    :param object level: Logging level, defaults to logging.INFO
    :return: Logging instance to use in other methods
    :rtype: object
    """
    # Get logger instance
    new_logger = logging.getLogger(logger_name)
    # Create formatter, defaults to '%(message)s'
    formatter = logging.Formatter(log_format)
    # Create file handler and add formatter
    fileHandler = logging.FileHandler(log_file, mode="w")
    fileHandler.setFormatter(formatter)
    # Set level add handler
    new_logger.setLevel(level)
    new_logger.addHandler(fileHandler)
    return new_logger

def data_log(log_message):
    data_logger.info(log_message.rstrip("\r\n"))

data_logger = _setup_logger("data_logger", "emulator_data.log")
