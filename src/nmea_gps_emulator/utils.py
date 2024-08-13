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

from nmea_utils import ddd2nmeall

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

default_position_dict = {
    'latitude_value': 57.70011131502446,
    'latitude_nmea_value': '5742.01113',
    'latitude_direction': 'N',
    'longitude_value': 11.988278521104876,
    'longitude_nmea_value': '01159.82785',
    'longitude_direction': 'E',
}
default_speed = 2
default_alt = 42
default_head = 260

filters_dict = {
    1: '$GPGGA',
    2: '$GPGLL',
    3: '$GPRMC',
    4: '$GPGSA',
    5: '$GPGSV',
    6: '$GPHDT',
    7: '$GPVTG',
    8: '$GPZDA',
    0: 'No filter'
}
default_ip = '127.0.0.1'
default_port = 10110
default_telnet_port = 10110

def exit_script(errortx = 'unspecified'):
    """
    The function terminates the script (main thread) from inside of
    child thread
    """
    current_script_pid = os.getpid()
    current_script = psutil.Process(current_script_pid)
    print(f'*** Closing the script ({errortx})... ***\n')
    time.sleep(1)
    current_script.terminate()

def filter_input():
    """
    The function asks for type of messages to log

    :return: filter message id as string
    :rtype: str
    """
    print('Choose filter:')
    for x, y in filters_dict.items():
        print(f'  {x} - {y}') 
    try:
        filter_choice = input('>>> ')
        mo = re.match(r'([0-8])', filter_choice)
        if mo:
            # Filter is first match group
            filter = int(mo.group())
        else:
            # No filter
            filter = 0
    except KeyboardInterrupt:
        print('\n\n*** Closing the script... ***\n')
        sys.exit()
    filter_type = filters_dict.get(filter)
    if filter != 0:
        print('Filtering messages by type ' + filter_type + '.\n')
    else:
        print('No message filtering active.\n')
        filter_type = ''
    return filter_type

def poi_input():
    """
    The function reads the poi file and asks for user choice
    """
    pos_dict = default_position_dict
    try:
        # Listing of and input of selected POI
        while True:
            poi_filename = 'poi.json'
            poi_filename_path = os.path.join(__location__, "pois", poi_filename)
            if os.path.exists(poi_filename_path):
                print("Showing points from: " + poi_filename_path)
                with open(poi_filename_path, 'r') as file:
                    poi_list = json.load(file)

                # Add a number to each object in the list
                for index, item in enumerate(poi_list, start=1):
                    item['uid'] = index

                # Loop through each object in the list
                for poi in poi_list:
                    print(f"{poi['uid']} - {poi['name']}, " +
                          f"({poi['lon']:3.3f}º{poi['lon_d']}, " +
                          f"{poi['lat']:2f}º{poi['lat_d']})")

                selected_uid = int(input('>>> '))
                sel_poi_item = None
                for poi_item in poi_list:
                    if poi_item.get('uid') == selected_uid:
                        sel_poi_item = poi_item

                if sel_poi_item != None:
                    pos_dict['latitude_value'] = sel_poi_item['lat']
                    if sel_poi_item['lat'] < 0:
                        pos_dict['latitude_direction'] = 'S'
                    else:
                        pos_dict['latitude_direction'] = 'N'

                    pos_dict['longitude_value'] = sel_poi_item['lon']
                    if sel_poi_item['lon'] < 0:
                        pos_dict['longitude_direction'] = 'W'
                    else:
                        pos_dict['longitude_direction'] = 'E'

                    pos_dict['latitude_nmea_value'] = ddd2nmeall(sel_poi_item['lat'], 'lat')
                    pos_dict['longitude_nmea_value'] = ddd2nmeall(sel_poi_item['lon'], 'lng')

                    return pos_dict, sel_poi_item['alt'], sel_poi_item['head']
                else:
                    print('Non valid POI choice. Continue with manual input.')
                    return None, None, None
            else:
                print('No POI file exists! Create pois/poi.json with data according to docs.')
                print('Continuing with manual input.')
                time.sleep(1)
                return None
    except json.JSONDecodeError as json_error:
        print(json_error.msg)
        return None
    except KeyboardInterrupt:
        print('\n\n*** Closing the script... ***\n')
        sys.exit()

def position_sep_input() -> dict:
    """
    The function asks for position and checks validity of entry data.
    Function returns position dictionary.
    """
    position_dict = default_position_dict
    try:
        # Input of latitude
        while True:
            try:
                print(f'\n- Enter unit position latitude (defaults to {default_position_dict["latitude_value"]}):')
                print(f'- (Negative for southern hemisphere) ')
                latitude_data = input('>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            # Input is empty, use default value
            if latitude_data == '':
                latitude_data = float(default_position_dict["latitude_value"])
                position_dict['latitude_value'] = latitude_data
                break
            latitude_regex_pattern = r'^(\+|-)?(?:90(?:(?:\.0{1,14})?)|(?:[0-9]|[1-8][0-9])(?:(?:\.[0-9]{1,14})?))$'
            mo = re.fullmatch(latitude_regex_pattern, str(latitude_data))
            if mo:
                position_dict['latitude_value'] = float(mo.group())
                break
        # Input of longitude
        while True:
            try:
                print(f'\n- Enter unit position longitude (defaults to {default_position_dict["longitude_value"]}):')
                print(f'- (Negative for west of Greenwich)')
                longitude_data = input('>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            # Input is empty, use default value
            if longitude_data == '':
                longitude_data = float(default_position_dict["longitude_value"])
                position_dict['longitude_value'] = longitude_data
                break
            longitude_regex_pattern = r'^(\+|-)?(?:180(?:(?:\.0{1,6})?)|(?:[0-9]|[1-9][0-9]|1[0-7][0-9])(?:(?:\.[0-9]{1,14})?))$'
            mo = re.fullmatch(longitude_regex_pattern, str(longitude_data))
            if mo:
                position_dict['longitude_value'] = float(mo.group())
        
        #Convert lat/lon to NMEA form and store in dictionary
        position_dict['latitude_nmea_value'] = ddd2nmeall(position_dict['latitude_value'], 'lat')
        position_dict['longitude_nmea_value'] = ddd2nmeall(position_dict['longitude_value'], 'lng')

        print(str(position_dict))
        return position_dict
    except KeyboardInterrupt:
        print('\n\n*** Closing the script... ***\n')
        sys.exit()

def ip_port_input(option: str) -> tuple:
    """
    The function asks for IP address and port number for connection.
    """
    while True:
        try:
            if option == 'telnet':
                print(f'\n### Enter Local IP address and port number (defaults to local ip: {get_ip()}:{default_telnet_port}): ###')
                try:
                    ip_port_socket = input('>>> ')
                except KeyboardInterrupt:
                    print('\n\n*** Closing the script... ***\n')
                    sys.exit()
                if ip_port_socket == '':
                    # All available interfaces and default NMEA port.
                    return (get_ip(), default_port)
            elif option == 'stream':
                print(f'\n### Enter Remote IP address and port number (defaults to {default_ip}:{default_port}): ###')
                try:
                    ip_port_socket = input('>>> ')
                except KeyboardInterrupt:
                    print('\n\n*** Closing the script... ***\n')
                    sys.exit()
                if ip_port_socket == '':
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
            print(f'\n\nError: Wrong format use - 192.168.10.10:2020.')
        except KeyboardInterrupt:
            print('\n*** Closing the script... ***\n')
            sys.exit()

def trans_proto_input() -> str:
    """
    The function asks for transport protocol for NMEA stream.
    """
    while True:
        try:
            print('\n### Enter transport protocol - TCP or UDP (defaults to TCP): ###')
            try:
                stream_proto = input('>>> ').strip().lower()
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()

            if stream_proto == '' or stream_proto == 'tcp':
                return 'tcp'
            elif stream_proto == 't':
                return 'tcp'
            elif stream_proto == 'udp':
                return 'udp'
            elif stream_proto == 'u':
                return 'udp'
        except KeyboardInterrupt:
            print('\n\n*** Closing the script... ***\n')
            sys.exit()

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # Doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        ip_local = s.getsockname()[0]
    except Exception:
        ip_local = '127.0.0.1'
    finally:
        s.close()
    return ip_local

def heading_input() -> float:
    """
    The function asks for the unit's course.
    """
    while True:
        try:
            print(f'\n### Enter unit course - range 000-359 degrees (defaults to {default_head}): ###')
            try:
                heading_data = input('>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            if heading_data == '':
                return 45.0
            heading_regex_pattern = r'(3[0-5]\d|[0-2]\d{2}|\d{1,2})'
            mo = re.fullmatch(heading_regex_pattern, heading_data)
            if mo:
                return float(mo.group())
        except KeyboardInterrupt:
            print('\n\n*** Closing the script... ***\n')
            sys.exit()

def speed_input() -> float:
    """
    The function asks for the unit's speed.
    """
    while True:
        try:
            print(f'\n### Enter unit speed in knots - range 0-999 (defaults to {default_speed} knots): ###')
            try:
                speed_data = input('>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            if speed_data == '':
                return default_speed
            speed_regex_pattern = r'(\d{1,3}(\.\d)?)'
            mo = re.fullmatch(speed_regex_pattern, speed_data)
            if mo:
                match = mo.group()
                if match.startswith('0') and match != '0':
                    match = match.lstrip('0')
                return float(match)
        except KeyboardInterrupt:
            print('\n\n*** Closing the script... ***\n')
            sys.exit()

def alt_input() -> float:
    """
    The function asks for the unit's altitude.
    """
    while True:
        try:
            print(f'\n### Enter unit altitude in meters above sea level - range -40-9000 (defaults to {default_alt}): ###')
            try:
                alt_data = input('>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            if alt_data == '':
                return default_alt
            alt_regex_pattern = r'(\d{1,3}(\.\d)?)'
            mo = re.fullmatch(alt_regex_pattern, alt_data)
            if mo:
                match = mo.group()
                if match.startswith('0') and match != '0':
                    match = match.lstrip('0')
                return float(match)
        except KeyboardInterrupt:
            print('\n\n*** Closing the script... ***\n')
            sys.exit()

def change_input(self, old_course, old_speed, old_altitude) -> tuple:
    """
    The function asks for the unit's heading, speed and altitude (online).
    """
    try:
        while True:
            try:
                heading_data = input(f'New course (Active target {old_course})>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            heading_regex_pattern = r'(3[0-5]\d|[0-2]\d{2}|\d{1,2})'
            mo = re.fullmatch(heading_regex_pattern, heading_data)
            if mo:
                heading_new = float(mo.group())
                print(f'\nCourse updated: {heading_new}\n')
                break
        while True:
            try:
                speed_data = input(f'New speed (Active target {old_speed})>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            speed_regex_pattern = r'(\d{1,3}(\.\d)?)'
            mo = re.fullmatch(speed_regex_pattern, speed_data)
            if mo:
                match = mo.group()
                if match.startswith('0') and match != '0':
                    match = match.lstrip('0')
                speed_new = float(match)
                print(f'\nSpeed updated: {speed_new}\n')
                break
        while True:
            try:
                alt_data = input(f'New altitude (Active target {old_altitude})>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            alt_regex_pattern = r'(\d{1,3}(\.\d)?)'
            mo = re.fullmatch(alt_regex_pattern, alt_data)
            if mo:
                match = mo.group()
                if match.startswith('0') and match != '0':
                    match = match.lstrip('0')
                altitude_new = float(match)
                print(f'\nAltitude updated: {altitude_new}\n')
                break
        return heading_new, speed_new, altitude_new
    except KeyboardInterrupt:
        print('\n\n*** Closing the script... ***\n')
        sys.exit()

def serial_config_input() -> dict:
    """
    The function asks for serial configuration.
    """
    # serial_port = '/dev/ttyS0'
    # Dict with all serial port settings.
    serial_set = {'bytesize': 8,
                  'parity': 'N',
                  'stopbits': 1,
                  'timeout': 1}

    # List of available serial ports.
    ports_connected = serial.tools.list_ports.comports(include_links=False)

    # List of available serial port's names.
    ports_connected_names = [port.device for port in ports_connected]
    print('\n### Connected Serial Ports: ###')
    for port in sorted(ports_connected):
        print(f'   - {port}')
    
    # Check OS platform.
    platform_os = platform.system()

    # Asks for serial port name and checks the name validity.
    while True:
        if platform_os.lower() == 'linux':
            print('\n### Choose Serial Port [/dev/ttyS0]: ###')
            try:
                serial_set['port'] = input('>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            if serial_set['port'] == '':
                serial_set['port'] = '/dev/ttyS0'
            if serial_set['port'] in ports_connected_names:
                break
        elif platform_os.lower() == 'windows':
            print('\n### Choose Serial Port [COM1]: ###')
            try:
                serial_set['port'] = input('>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            if serial_set['port'] == '':
                serial_set['port'] = 'COM1'
            if serial_set['port'] in ports_connected_names:
                break
        print(f'\nError: \'{serial_set["port"]}\' is wrong port\'s name.')

    # Serial port settings:
    baudrate_list = ['300', '600', '1200', '2400', '4800', '9600', '14400',
                     '19200', '38400', '57600', '115200', '128000']
    
    # Ask for baud rate, defaults to 9600 (NMEA standard)
    while True:
        print('\n### Enter serial baudrate [9600]: ###')
        try:
            serial_set['baudrate'] = input('>>> ')
        except KeyboardInterrupt:
            print('\n\n*** Closing the script... ***\n')
            sys.exit()
        if serial_set['baudrate'] == '':
            serial_set['baudrate'] = 9600
        if str(serial_set['baudrate']) in baudrate_list:
            break
        print(f'\n*** Error: \'{serial_set["baudrate"]}\' is wrong port\'s baudrate. ***')
    return serial_set

def setup_logger(logger_name, log_file, log_format='%(message)s', level=logging.INFO):
    """
    The function creates a logging instance and returns it.
    """
    # Get logger instance
    new_logger = logging.getLogger(logger_name)
    # Create formatter, defaults to '%(message)s'
    formatter = logging.Formatter(log_format)
    # Create file handler and add formatter
    fileHandler = logging.FileHandler(log_file, mode='w')
    fileHandler.setFormatter(formatter)
    # Set level add handler
    new_logger.setLevel(level)
    new_logger.addHandler(fileHandler)
    return new_logger

def system_log(log_message):
    system_logger.info(log_message)

def data_log(log_message):
    data_logger.info(log_message)

system_logger = setup_logger('system_logger', 'emulator_system.log')
data_logger = setup_logger('data_logger', 'emulator_data.log')
