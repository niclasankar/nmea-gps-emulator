import re
import sys
import os
import time
import platform
import logging
import json

import psutil
import serial.tools.list_ports
from nmea_gps import NmeaMsg

def exit_script(errortx = 'unspecified'):
    """
    The function terminates the script (main thread) from inside of child thread
    """
    current_script_pid = os.getpid()
    current_script = psutil.Process(current_script_pid)
    # TODO: Remove script name
    print(f'*** Closing the script ({errortx}, {current_script_pid})... ***\n')
    time.sleep(1)
    current_script.terminate()

def filter_input():
    """
    The function asks for type of message to log
    """
    filter_mess = {
        '1': '$GPGGA',
        '2': '$GPGLL',
        '3': '$GPRMC',
        '4': '$GPGSA',
        '5': '$GPGSV',
        '6': '$GPHDT',
        '7': '$GPVTG',
        '8': '$GPZDA',
        '0': None
    }

    print(r'''
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
    ''')

    try:
        filter = input('>>> ')
        if filter == '':
            # No filter
            filter = 0
    except KeyboardInterrupt:
        print('\n\n*** Closing the script... ***\n')
        sys.exit()
    filter_type = filter_mess.get(filter)
    print('Filtering by message type ' + filter_type + '.\n')
    return filter_type

def poi_input():
    """
    The function reads the poi file and asks for user choice
    """
    # TODO: Implement poi input
    try:
        # Listin of and input of selected POI
        while True:
            print('POI:s')
            poi_filename = 'poi.json'
            if os.path.exists(poi_filename):
            	with open('poi.json', 'r') as file:
                	data_list = json.load(file)
        
            	# Check the type of the parsed data
            	print(type(data))  # Output: <class 'list'>
    
            	# Add a number to each object in the list
            	for index, item in enumerate(data_list, start=1):
                	item['uid'] = index
    
            	# Loop through each object in the list
            	for poi in data_list:
                	print(f"{uid} - {poi['name']}")
        
            	selected_uid = input('>>> ')
    
            	for item in data_list:
                	if item.get('uid') == selected_uid:
                    	selected_item = item
                        
                return selected_item['name']
    		else:
                print('No POI file exists! Create poi.json with data according to docs.')
                return None

        except KeyboardInterrupt:
            print('\n\n*** Closing the script... ***\n')
            sys.exit()


def position_sep_input() -> dict:
    """
    The function asks for position and checks validity of entry data.
    Function returns position dictionary.
    """
    position_dict = {
        'latitude_value': '57.70011131502446',
        'latitude_nmea_value': '5742.011131502446',
        'latitude_direction': 'N',
        'longitude_value': '11.988278521104876',
        'longitude_nmea_value': '01159.8278521104876',
        'longitude_direction': 'E',
    }
    try:
        # Input of latitude
        while True:
            try:
                print('\n### Enter unit position latitude (defaults to 57.70011131502446): ###')
                latitude_data = input('>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            if latitude_data == '':
                # Default position
                latitude_data = 57.70011131502446
                position_dict['latitude_value'] = latitude_data
                break
            latitude_regex_pattern = r'^(\+|-)?(?:90(?:(?:\.0{1,14})?)|(?:[0-9]|[1-8][0-9])(?:(?:\.[0-9]{1,14})?))$'
            mo = re.fullmatch(latitude_regex_pattern, str(latitude_data))
            if mo:
                position_dict['latitude_value'] = float(mo.group())
                break
        # Input of latitude hemisphere
        while True:
            try:
                print('\n### Enter unit position latitude hemisphere (defaults to N): ###')
                latitude_hemi_data = input('>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            if latitude_hemi_data == '':
                # Default position
                latitude_hemi_data = 'N'
                position_dict['latitude_direction'] = latitude_hemi_data
                break
            latitude_hemi_regex_pattern = r'[N,S]'
            mo = re.fullmatch(latitude_hemi_regex_pattern, latitude_hemi_data.upper())
            if mo:
                position_dict['latitude_direction'] = float(mo.group())
                break
        # Input of longitude
        while True:
            try:
                print('\n### Enter unit position longitude (defaults to 11.988278521104876): ###')
                longitude_data = input('>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            if longitude_data == '':
                # Default position
                longitude_data = 11.988278521104876
                position_dict['longitude_value'] = longitude_data
                break
            longitude_regex_pattern = r'^(\+|-)?(?:180(?:(?:\.0{1,6})?)|(?:[0-9]|[1-9][0-9]|1[0-7][0-9])(?:(?:\.[0-9]{1,6})?))$'
            mo = re.fullmatch(longitude_regex_pattern, str(longitude_data))
            if mo:
                position_dict['longitude_value'] = float(mo.group())
        # Input of longitude hemisphere
        while True:
            try:
                print('\n### Enter unit position longitude hemisphere (defaults to E): ###')
                longitude_hemi_data = input('>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            if longitude_hemi_data == '':
                # Default position
                longitude_hemi_data = 'E'
                position_dict['longitude_direction'] = longitude_hemi_data
                break
            latitude_hemi_regex_pattern = r'[E,W]'
            mo = re.fullmatch(latitude_hemi_regex_pattern, longitude_hemi_data.upper())
            if mo:
                position_dict['longitude_direction'] = float(mo.group())
                break
        #Convert lat/lon to NMEA form and store
        position_dict['latitude_nmea_value'],position_dict['longitude_nmea_value'] = NmeaMsg.to_nmea_position(position_dict['latitude_value'], position_dict['longitude_value'])
        #print(str(position_dict))
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
                print('\n### Enter Local IP address and port number [0.0.0.0:10110]: ###')
                try:
                    ip_port_socket = input('>>> ')
                except KeyboardInterrupt:
                    print('\n\n*** Closing the script... ***\n')
                    sys.exit()
                if ip_port_socket == '':
                    # All available interfaces and default NMEA port.
                    return ('0.0.0.0', 10110)
            elif option == 'stream':
                print('\n### Enter Remote IP address and port number [127.0.0.1:10110]: ###')
                try:
                    ip_port_socket = input('>>> ')
                except KeyboardInterrupt:
                    print('\n\n*** Closing the script... ***\n')
                    sys.exit()
                if ip_port_socket == '':
                    return ('127.0.0.1', 10110)
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
            print('\n### Enter transport protocol - TCP or UDP [TCP]: ###')
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

def heading_input() -> float:
    """
    The function asks for the unit's course.
    """
    while True:
        try:
            print('\n### Enter unit course - range 000-359 degrees (defaults to 45): ###')
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
            print('\n### Enter unit speed in knots - range 0-999 (defaults to 2 knots): ###')
            try:
                speed_data = input('>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            if speed_data == '':
                return 0
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
            print('\n### Enter unit altitude in meters above sea level - range -40-9000 (defaults to 42): ###')
            try:
                alt_data = input('>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            if alt_data == '':
                return 30
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
                print('\n\nCourse updated: ', heading_new)
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
                print('\n\nSpeed updated: ', speed_new)
                break
        while True:
            try:
                alt_data = input('New altitude (Active target {old_altitude})>>> ')
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
                print('\n\nAltitude updated: ', altitude_new)
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
