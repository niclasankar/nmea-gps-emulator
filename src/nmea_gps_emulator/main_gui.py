#!/usr/bin/env python3

"""
Main module of NMEA-GPS-EMULATOR with Qt GUI.

Created in 2024

:author: ankars
:copyright: Ankars.se © 2024
:license: MIT
"""

import time
import sys
import threading
import uuid
import argparse
import os
import json
import re

import serial.tools.list_ports

from PySide6.QtCore import QTimer, QRegularExpression, QLocale

from PySide6.QtWidgets import (QApplication, QButtonGroup, QComboBox, 
        QDialog, QFormLayout, QGridLayout, QGroupBox, QLabel, QLineEdit,
        QMessageBox, QPushButton, QRadioButton, 
        QVBoxLayout)

from PySide6.QtGui import QDoubleValidator, QIntValidator, QRegularExpressionValidator

from nmea_gps import NmeaMsg
from nmea_utils import ddd2nmeall
from utils import get_ip, get_status

from custom_thread import NmeaStreamThread, NmeaSerialThread, NmeaOutputThread, run_telnet_server_thread

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

class NmeaGuiApplication(QDialog):
    """
    Display a gui windows with settings and run.
    """
    def __init__(self, parent=None):

        super(NmeaGuiApplication, self).__init__(parent)

        self.locale_en = QLocale(QLocale.English, QLocale.UnitedStates)

        self.nmea_thread = None
        self.nmea_obj = None

        self.mode_select = 0
        self.serial_set = {
            'setup_ok': False,
            'port': '/dev/ttyS0',
            'baudrate': 9600,
            'bytesize': 8,
            'parity': 'N',
            'stopbits': 1,
            'timeout': 1
        }
        self.network_set = {
            'setup_ok': False,
            'ip_srv': '127.0.0.1',
            'port_srv': 10110,
            'ip_str': '127.0.0.1',
            'port_str': 10110
        }
        self.pos_data_dict = {
            'latitude_value': 57.70011131,
            'latitude_nmea_value': '',
            'latitude_direction': 'N',
            'longitude_value': 11.98827852,
            'longitude_nmea_value': '',
            'longitude_direction': 'E'
        }
        self.nav_data_dict = {
            'speed': 2,
            'heading': 45,
            'altitude_amsl': 42,
            'position': self.pos_data_dict
        }
        self.filters_dict = {
            '1': '$GPGGA',
            '2': '$GPGLL',
            '3': '$GPRMC',
            '4': '$GPGSA',
            '5': '$GPGSV',
            '6': '$GPHDT',
            '7': '$GPVTG',
            '8': '$GPZDA',
            '0': 'None'
        }
        self.filter_mess = ''

        self.init_gui()

    def init_gui(self):

        # Setup window
        self.setWindowTitle("NMEA GPS Emulator")
        self.resize(800,600)

        # Create group boxes with controls
        self.create_modegroupbox()
        self.create_positiongroupbox()
        self.create_controlsgroupbox()
        self.create_serialgroupbox()
        self.create_networkgroupbox()
        self.create_filtergroupbox()
        self.create_statusgroupbox()

        # Create timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        
        # Create start and stop buttons
        self.start_button = QPushButton("Start", self)
        self.start_button.resize(10,30)
        self.start_button.clicked.connect(self.run)
        self.stop_button = QPushButton("Stop", self)
        self.stop_button.resize(10,30)
        self.stop_button.clicked.connect(self.stop)

        main_grid = QGridLayout()
        main_grid.setContentsMargins(10, 5, 10, 0)
        main_grid.setColumnMinimumWidth(0, 120)
        main_grid.setColumnMinimumWidth(1, 120)
        main_grid.setColumnMinimumWidth(2, 120)

        # Column 1
        main_grid.addWidget(self.modegroupbox, 0, 0)
        main_grid.addWidget(self.positiongroupbox, 1, 0)
        main_grid.addWidget(self.filtergroupbox, 2, 0)

        # Column 2
        main_grid.addWidget(self.serialgroupbox, 0, 1)
        main_grid.addWidget(self.networkgroupbox, 1, 1)
        main_grid.addWidget(self.controlsgroupbox, 2, 1)

        # Column 3
        main_grid.addWidget(self.statusgroupbox, 0, 2, 2, 1)

        # Buttons
        main_grid.addWidget(self.start_button, 3, 0)
        main_grid.addWidget(self.stop_button, 3, 1)

        self.setLayout(main_grid)

        # Set defaults/focus
        self.mode_combo_box.setCurrentIndex(4)
        self.controlsgroupbox.setDisabled(True)
        self.lat_txt.setFocus()

    def create_modegroupbox(self):
        self.modegroupbox = QGroupBox("Mode:")

        self.mode_combo_box = QComboBox(self)
        self.mode_combo_box.width = 100
        self.mode_combo_box.addItem("NMEA Serial Output", userData=0)
        self.mode_combo_box.addItem("NMEA TCP Server", userData=1)
        self.mode_combo_box.addItem("NMEA Stream (UDP)", userData=2)
        self.mode_combo_box.addItem("NMEA Stream (TCP)", userData=3)
        self.mode_combo_box.addItem("NMEA Logging", userData=4)
        self.mode_combo_box.currentIndexChanged.connect(self.update_mode)

        layout = QFormLayout()
        layout.addRow('Select mode:', self.mode_combo_box)
        self.modegroupbox.setLayout(layout)

    def update_mode(self):
        self.mode_select = self.mode_combo_box.currentData()
        self.serialgroupbox.setEnabled(False)
        self.networkgroupbox.setEnabled(False)
        self.filtergroupbox.setEnabled(False)
        match self.mode_select:
            case 0: # Serial
                self.serialgroupbox.setEnabled(True)
                self.serial_list_combo_box.setFocus()
            case 1: # TCP Server
                self.networkgroupbox.setEnabled(True)
                self.ip_srv_txt.setFocus()
            case 2: # Stream UDP
                self.networkgroupbox.setEnabled(True)
                self.ip_str_txt.setFocus()
            case 3: # Stream TCP
                self.networkgroupbox.setEnabled(True)
                self.ip_str_txt.setFocus()
            case 4: # Logging
                self.filtergroupbox.setEnabled(True)
            case _:
                self.filtergroupbox.setEnabled(True)
                self.mode_select = 4

    def create_serialgroupbox(self):
        self.serialgroupbox = QGroupBox("Serial ports:")

        # Create combo box with available serial ports
        self.serial_list_combo_box = QComboBox(self)
        ports_connected = serial.tools.list_ports.comports(include_links=False)
        for device, desc, hwid in sorted(ports_connected):
            self.serial_list_combo_box.addItem(f'{device}')
        self.serial_select_label = QLabel("-", self)
        self.serial_select_label.width = 120
        self.serial_list_combo_box.currentIndexChanged.connect(self.check_valid_serial)

        # Create a combo box with all baud rates
        self.baudrates_combo_box = QComboBox(self)
        baudrate_list = ['300', '600', '1200', '2400', '4800', '9600', '14400',
                     '19200', '38400', '57600', '115200', '128000']
        self.baudrates_combo_box.addItems(baudrate_list)
        default_baud_rate = "9600"
        self.baudrates_combo_box.setCurrentText(default_baud_rate)
        self.baudrates_combo_box.currentIndexChanged.connect(self.check_valid_serial)

        layout = QVBoxLayout()
        layout.addWidget(self.serial_list_combo_box)
        layout.addWidget(self.serial_select_label)
        layout.addWidget(self.baudrates_combo_box)
        layout.addStretch(1)
        self.serialgroupbox.setLayout(layout)

    def check_valid_serial(self):
        serial_select = self.serial_list_combo_box.currentText()
        baudrate_select = self.baudrates_combo_box.currentText()
        self.serial_select_label.setText(serial_select)
        self.serial_set['setup_ok'] = True
        self.serial_set['port'] = serial_select
        self.serial_set['baudrate'] = int(baudrate_select)

    def create_networkgroupbox(self):
        self.networkgroupbox = QGroupBox("Networking:")

        ipa_pattern = r'''
            \b                      # Word boundary
            (                       # Start of the first capturing group
                (?:                   # Non-capturing group for the first 3 octets
                25[0-5]|            # Match 250-255
                2[0-4][0-9]|        # Match 200-249
                1[0-9][0-9]|        # Match 100-199
                [1-9]?[0-9]         # Match 0-99 (including leading zeros)
            )
            \.                    # Literal dot
            ){3}                    # Repeat the non-capturing group 3 times
            (                       # Start of the fourth octet
                25[0-5]|              # Match 250-255
                2[0-4][0-9]|          # Match 200-249
                1[0-9][0-9]|          # Match 100-199
                [1-9]?[0-9]           # Match 0-99 (including leading zeros)
            )
            \b                      # Word boundary
            '''

        ip_regex = QRegularExpression(ipa_pattern, QRegularExpression.ExtendedPatternSyntaxOption)

        self.ip_srv_txt = QLineEdit(self)
        self.ip_srv_txt.width = 60
        self.ip_srv_txt.setToolTip('Local IP address to use when running a TCP server')
        ipal_txt_validator = QRegularExpressionValidator(ip_regex, self.ip_srv_txt)
        self.ip_srv_txt.setValidator(ipal_txt_validator)
        self.ip_srv_txt.setPlaceholderText('127.0.0.1')
        self.ip_srv_txt.setText(str(f'{get_ip()}'))
        self.ip_srv_txt.textChanged.connect(self.check_valid_network)
        self.ip_srv_txt.textEdited.connect(self.check_valid_network)

        self.port_srv_txt = QLineEdit(self)
        self.port_srv_txt.width = 60
        self.port_srv_txt.setToolTip('Port, used for server')
        ipp_input_validator = QRegularExpressionValidator(
            QRegularExpression(R'''([1-9][0-9]{0,3}|[1-6][0-5]{2}[0-3][0-5])'''),
                self.port_srv_txt
        )
        self.port_srv_txt.setValidator(ipp_input_validator)
        self.port_srv_txt.setText(str({self.network_set['port_srv']}))
        self.port_srv_txt.textChanged.connect(self.check_valid_network)
        self.port_srv_txt.textEdited.connect(self.check_valid_network)

        self.ip_str_txt = QLineEdit(self)
        self.ip_str_txt.width = 60
        self.ip_str_txt.setToolTip('Remote IP address used to send messages to')
        ipar_txt_validator = QRegularExpressionValidator(ip_regex, self.ip_str_txt)
        self.ip_str_txt.setValidator(ipar_txt_validator)
        self.ip_str_txt.setText(str({self.network_set['ip_str']}))
        self.ip_str_txt.textChanged.connect(self.check_valid_network)
        self.ip_str_txt.textEdited.connect(self.check_valid_network)

        self.port_str_txt = QLineEdit(self)
        self.port_str_txt.width = 60
        self.port_str_txt.setToolTip('Port, used for stream')
        ipp_input_validator = QRegularExpressionValidator(
            QRegularExpression(R'''([1-9][0-9]{0,3}|[1-6][0-5]{2}[0-3][0-5])'''),
                self.port_str_txt
        )
        self.port_str_txt.setValidator(ipp_input_validator)
        self.port_str_txt.setText(str({self.network_set['port_str']}))
        self.port_str_txt.textChanged.connect(self.check_valid_network)
        self.port_str_txt.textEdited.connect(self.check_valid_network)

        layout = QFormLayout()
        layout.addRow('Local IP:', self.ip_srv_txt)
        layout.addRow('Server port:', self.port_srv_txt)
        layout.addRow('Stream IP:', self.ip_str_txt)
        layout.addRow('Stream port:', self.port_str_txt)
        self.networkgroupbox.setLayout(layout)
    
    def check_valid_network(self):
        self.network_set['setup_ok'] = False
        if self.ip_srv_txt.hasAcceptableInput() \
            and self.ip_str_txt.hasAcceptableInput() \
            and self.port_srv_txt.hasAcceptableInput() \
            and self.port_str_txt.hasAcceptableInput():
            self.network_set['setup_ok'] = True
            self.network_set['ip_srv'] = self.ip_srv_txt
            self.network_set['port_srv'] = self.port_srv_txt
            self.network_set['ip_stream'] = self.ip_str_txt
            self.network_set['port_stream'] = self.port_str_txt
            print(self.network_set)

    def create_positiongroupbox(self):
        self.positiongroupbox = QGroupBox("Position:")

        self.lat_txt = QLineEdit(self)
        self.lat_txt.width = 60
        self.lat_txt.setText(str(self.nav_data_dict['position']['latitude_value']))
        self.lat_txt.setToolTip(f'Latitude in degrees, negative if on the southern hemisphere')
        lat_validator = QDoubleValidator(-89.9999999, 89.9999999, 8, self)
        lat_validator.setLocale(self.locale_en)
        self.lat_txt.setValidator(lat_validator)

        self.lng_txt = QLineEdit(self)
        self.lng_txt.width = 60
        self.lng_txt.setText(str(self.nav_data_dict['position']['longitude_value']))
        self.lng_txt.setToolTip(f'Longitude in degrees, negative if west of Greenwich, London')
        lng_validator = QDoubleValidator(-179.99999999, 179.99999999, 8, self)
        lng_validator.setLocale(self.locale_en)
        self.lng_txt.setValidator(lng_validator)

        self.alt_txt = QLineEdit(self)
        self.alt_txt.width = 60
        self.alt_txt.setText(str(self.nav_data_dict['altitude_amsl']))
        self.alt_txt.setToolTip(f'Altitude in meters above sea level')
        alt_validator = QIntValidator(-400, 9000, self)
        self.alt_txt.setValidator(alt_validator)

        self.speed_txt = QLineEdit(self)
        self.speed_txt.width = 60
        self.speed_txt.setText(str(self.nav_data_dict['speed']))
        self.speed_txt.setToolTip(f'Speed in knots')
        speed_validator = QIntValidator(0, 200, self)
        self.speed_txt.setValidator(speed_validator)

        self.head_txt = QLineEdit(self)
        self.head_txt.width = 60
        self.head_txt.setText(str(self.nav_data_dict['heading']))
        self.head_txt.setToolTip(f'Heading in degrees')
        head_validator = QIntValidator(0, 359, self)
        self.head_txt.setValidator(head_validator)

        layout = QFormLayout()
        layout.addRow('Lat:',self.lat_txt)
        layout.addRow('Lon:', self.lng_txt)
        layout.addRow('Altitude:', self.alt_txt)
        layout.addRow('Speed:', self.speed_txt)
        layout.addRow('Heading:', self.head_txt)

        self.positiongroupbox.setLayout(layout)

    def check_valid_position(self):
        self.position_ok = False
        if self.lat_txt.hasAcceptableInput() \
            and self.lng_txt.hasAcceptableInput() \
            and self.alt_txt.hasAcceptableInput() \
            and self.speed_txt.hasAcceptableInput() \
            and self.head_txt.hasAcceptableInput():
            self.position_ok = True

    def create_controlsgroupbox(self):
        self.controlsgroupbox = QGroupBox("Controls:")

        self.alt_up_button = QPushButton("Alt +", self)
        self.alt_up_button.resize(10,20)
        self.alt_up_button.setToolTip(f'Increase altitude by 1')
        self.alt_up_button.clicked.connect(self.updateAltPlus)

        self.alt_dn_button = QPushButton("Alt -", self)
        self.alt_dn_button.resize(10,20)
        self.alt_dn_button.setToolTip(f'Decrease altitude by 1')
        self.alt_dn_button.clicked.connect(self.updateAltMinus)

        self.head_plus_button = QPushButton("Right", self)
        self.head_plus_button.resize(10,20)
        self.head_plus_button.setToolTip(f'Turn right by 1 degree')
        self.head_plus_button.clicked.connect(self.updateHeadPlus)

        self.head_minus_button = QPushButton("Left", self)
        self.head_minus_button.resize(10,20)
        self.head_minus_button.setToolTip(f'Turn left by 1 degree')
        self.head_minus_button.clicked.connect(self.updateHeadMinus)

        self.speed_minus_button = QPushButton("Speed -", self)
        self.speed_minus_button.resize(10,30)
        self.speed_minus_button.setToolTip(f'Decrease speed by 1')
        self.speed_minus_button.clicked.connect(self.updateSpeedMinus)

        self.speed_plus_button = QPushButton("Speed +", self)
        self.speed_plus_button.resize(10,30)
        self.speed_plus_button.setToolTip(f'Increase speed by 1')
        self.speed_plus_button.clicked.connect(self.updateSpeedPlus)

        controls_grid = QGridLayout()
        controls_grid.addWidget(self.alt_up_button, 0, 1)
        controls_grid.addWidget(self.speed_plus_button, 0, 2)

        controls_grid.addWidget(self.head_plus_button, 1, 2)
        controls_grid.addWidget(self.head_minus_button, 1, 0)

        controls_grid.addWidget(self.alt_dn_button, 2, 1)
        controls_grid.addWidget(self.speed_minus_button, 2, 2)

        self.controlsgroupbox.setLayout(controls_grid)

    def create_filtergroupbox(self):
        self.filtergroupbox = QGroupBox("Filter messages:")

        filter_stack = QFormLayout()
        self.filter_button_group = QButtonGroup(self)

        for key, option in self.filters_dict.items():
            
            filter_radio_button = QRadioButton(option)
            self.filter_button_group.addButton(filter_radio_button)
            filter_radio_button.setProperty('key', key)
            filter_radio_button.setProperty('filter', option)

            if key == '0':
                filter_radio_button.setChecked(True)
            
            filter_stack.addWidget(filter_radio_button)
            # print(str(option), str(key))

        self.filter_button_group.buttonClicked.connect(self.update_filter)

        self.filtergroupbox.setLayout(filter_stack)

    def update_filter(self, filters_button):
        key = filters_button.property('key')
        filter = filters_button.property('filter')
        # print(f"Selected: {filter} with value {key}")
        if key == 0:
            self.filter_mess = ''
        else:
            self.filter_mess = filter

    def create_statusgroupbox(self):
        self.statusgroupbox = QGroupBox("Status:")
        self.statusgroupbox.setMinimumWidth(250)

        self.status_lat_label = QLabel("-", self)
        self.status_lat_label.width = 250
        self.status_lng_label = QLabel("-", self)
        self.status_lng_label.width = 250

        self.status_speed_label = QLabel("-", self)
        self.status_speed_label.width = 250

        self.status_alt_label = QLabel("-", self)
        self.status_alt_label.width = 250

        self.status_head_label = QLabel("-", self)
        self.status_head_label.width = 250

        self.status_magvar_label = QLabel("-", self)
        self.status_magvar_label.width = 250

        self.status_system_label = QLabel("-", self)
        self.status_system_label.width = 250

        status_stack = QVBoxLayout()
        status_stack.addWidget(self.status_lat_label)
        status_stack.addWidget(self.status_lng_label)
        status_stack.addWidget(self.status_alt_label)
        status_stack.addWidget(self.status_head_label)
        status_stack.addWidget(self.status_speed_label)
        status_stack.addWidget(self.status_magvar_label)
        status_stack.addWidget(self.status_system_label)

        self.statusgroupbox.setLayout(status_stack)

    def update_status(self):
        self.status_lat_label.setText(f'Latitude: {str(self.nmea_obj.position['latitude_value'])}°')
        self.status_lng_label.setText(f'Longitude: {str(self.nmea_obj.position['longitude_value'])}°')
        self.status_speed_label.setText(f'Speed: {str(self.nmea_obj.speed)} kt')
        self.status_alt_label.setText(f'Altitude: {str(self.nmea_obj.altitude)} msl')
        self.status_head_label.setText(f'Heading: {str(self.nmea_obj.heading)}°')
        self.status_magvar_label.setText(f'M: {self.nmea_obj.magvar_dec:.3f}°')
        self.status_system_label.setText(get_status())

    def run(self):
        """
        Run the application and display the menu and respond to choices.
        """
        ready_to_run = False

        match self.mode_select:
            case 0: # Serial
                if self.serial_set['setup_ok']:
                    ready_to_run = True
            case 1: # TCP Server
                if self.network_set['setup_ok'] and self.network_set['ip_srv'] != '' and self.network_set['port_srv'] != '':
                    ready_to_run = True
            case 2: # Stream UDP
                if self.network_set['setup_ok'] and self.network_set['ip_str'] != '' and self.network_set['port_str'] != '':
                    ready_to_run = True
            case 3: # Stream TCP
                if self.network_set['setup_ok'] and self.network_set['ip_str'] != '' and self.network_set['port_str'] != '':
                    ready_to_run = True
            case 4: # Logging
                ready_to_run = True
            case _:
                ready_to_run = False

        if ready_to_run:

            nav_data_dict = {
                'speed': float(self.speed_txt.text()),
                'heading': float(self.head_txt.text()),
                'altitude_amsl': float(self.alt_txt.text()),
                'position': {}
            }
            pos_data_dict = {
                'latitude_value': float(self.lat_txt.text()),
                'latitude_nmea_value': ddd2nmeall(float(self.lat_txt.text()), 'lat'),
                'latitude_direction': 'N',
                'longitude_value': float(self.lng_txt.text()),
                'longitude_nmea_value': ddd2nmeall(float(self.lng_txt.text()), 'lng'),
                'longitude_direction': 'E'
            }
            nav_data_dict['position'] = pos_data_dict

            self.nmea_obj = NmeaMsg(position=nav_data_dict['position'],
                                    altitude=nav_data_dict['altitude_amsl'],
                                    speed=nav_data_dict['speed'],
                                    heading=nav_data_dict['heading'])
        
            time.sleep(1)

            self.controlsgroupbox.setEnabled(True)
            self.positiongroupbox.setDisabled(True)

            self.update_timer.start(1000)

            match self.mode_select:
                case 0: # Serial
                    self.nmea_serial()
                case 1: # TCP Server
                    self.nmea_tcp_server()
                case 2: # Stream UDP
                    self.nmea_stream('UDP')
                case 3: # Stream TCP
                    self.nmea_stream('TCP')
                case 4: # Logging
                    self.nmea_logging()
                case _:
                    sys.exit(0)
        else:
            not_ready_message = QMessageBox()
            not_ready_message.setText("Check your settings...")
            not_ready_message.exec()

    def stop(self):
        self.controlsgroupbox.setDisabled(True)
        self.positiongroupbox.setEnabled(True)
        self.update_timer.stop()
        #self.nmea_thread = None

    def updateRemoteThreds(new_heading, new_speed, new_altitude):
            # Get all 'nmea_srv*' telnet server threads
            thread_list = [thread for thread in threading.enumerate() if thread.name.startswith('nmea_srv')]
            if thread_list:
                for thr in thread_list:
                    # Update speed, heading and altitude
                    #a = time.time()
                    thr.set_heading(new_heading)
                    thr.set_speed(new_speed)
                    thr.set_altitude(new_altitude)
                    #print(time.time() - a)

    def updateAltPlus(self):
        self.nmea_obj.altitude_targeted += 1

    def updateAltMinus(self):
        self.nmea_obj.altitude_targeted -= 1

    def updateSpeedPlus(self):
        self.nmea_obj.speed_targeted += 1

    def updateSpeedMinus(self):
        self.nmea_obj.speed_targeted -= 1

    def updateHeadPlus(self):
        self.nmea_obj.heading_targeted += 1

    def updateHeadMinus(self):
        self.nmea_obj.heading_targeted -= 1
    
    def nmea_serial(self):
        """
        Runs serial which emulates NMEA server-device
        """
        self.nmea_thread = NmeaSerialThread(name=f'nmea_srv{uuid.uuid4().hex}',
                                       daemon=True,
                                       serial_config=self.serial_set,
                                       nmea_object=self.nmea_obj,
                                       gui=True)
        self.nmea_thread.start()

    def nmea_logging(self):
        """
        Runs in debug mode which outputs NMEA messages to log
        """
        self.nmea_thread = NmeaOutputThread(name=f'nmea_srv{uuid.uuid4().hex}',
                                       daemon=True,
                                       filter_mess=self.filter_mess,
                                       nmea_object=self.nmea_obj,
                                       gui=True)
        self.nmea_thread.start()

    def nmea_tcp_server(self):
        """
        Runs telnet server which emulates NMEA device.
        """
        # Local TCP server IP address and port number.
        #srv_ip_address, srv_port = ip_port_input('telnet')
        srv_ip_address = '127.0.0.1'
        srv_port = 10110
        self.nmea_thread = threading.Thread(target=run_telnet_server_thread,
                                            args=[srv_ip_address, srv_port, self.nmea_obj],
                                            daemon=True,
                                            name='nmea_thread')
        self.nmea_thread.start()

    def nmea_stream(self, stream_proto):
        """
        Runs TCP or UDP NMEA stream to designated host.
        """
        ip_add = self.network_set['ip_stream']
        port = self.network_set['port_stream']
        self.nmea_thread = NmeaStreamThread(name=f'nmea_srv{uuid.uuid4().hex}',
                                            daemon=True,
                                            ip_add=ip_add,
                                            port=port,
                                            proto=stream_proto,
                                            nmea_object=self.nmea_obj)
        self.nmea_thread.start()

    def quit(self):
        """
        Exit script.
        """
        sys.exit(0)


if __name__ == '__main__':

    app = QApplication(sys.argv)

    nmea_gui = NmeaGuiApplication()
    nmea_gui.show()

    sys.exit(app.exec())

