#!/usr/bin/env python3

# https://swairlearn.bluecover.pt/nmea_analyser
# https://pygeomag.readthedocs.io/en/latest/api.html
# https://pyproj4.github.io/pyproj/stable/api/geod.html
# https://receiverhelp.trimble.com/alloy-gnss/en-us/NMEA-0183messages_MessageOverview.html
# https://swairlearn.bluecover.pt/nmea_analyser

import time
import sys
import threading
import uuid

from nmea_gps import NmeaMsg
from utils import position_sep_input, ip_port_input, trans_proto_input, heading_input, speed_input, \
    change_input, serial_config_input, alt_input, filter_input, poi_input

from custom_thread import NmeaStreamThread, NmeaSerialThread, NmeaOutputThread, run_telnet_server_thread

class Menu:
    """
    Display a menu and respond to choices when run.
    """
    def __init__(self):
        self.nmea_thread = None
        self.nmea_obj = None
        self.choices = {
            '1': self.nmea_serial,
            '2': self.nmea_tcp_server,
            '3': self.nmea_stream,
            '4': self.nmea_logging,
            '0': self.quit,
        }

    def display_menu(self):
        # Show menu with choises
        print(r'''
┳┓┳┳┓┏┓┏┓  ┏┓     ┓             
┃┃┃┃┃┣ ┣┫  ┣ ┏┳┓┓┏┃┏┓╋┏┓┏┓      
┛┗┛ ┗┗┛┛┗  ┗┛┛┗┗┗┻┗┗┻┗┗┛┛       
                                
based on source code by luk-kop
''')
        print('### Choose emulator mode:            ###')
        print('### -------------------------------- ###')
        print('1 - NMEA Serial port output')
        print('2 - NMEA TCP Server')
        print('3 - NMEA TCP or UDP Stream')
        print('4 - NMEA output to log')
        print('0 - Quit')

    def run(self):
        """
        Display the menu and respond to choices.
        """
        self.display_menu()

        # Get choise from user
        while True:
            try:
                choice = input('>>> ')
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            action = self.choices.get(choice)
            if action:
                # Dummy 'nav_data_dict'
                nav_data_dict = {
                    'gps_speed': 10.035,
                    'gps_heading': 45.0,
                    'gps_altitude_amsl': 1.2,
                    'position': {}
                }
                print('Do you want to use a predefined starting point? (Y/N)')
                poi_active = input('>>> ')
                if poi_active.upper() == 'Y':
                    # Position, initial course, speed and altitude from file
                    poi_data, alt, heading = poi_input()
                    nav_data_dict['position'] = poi_data
                    nav_data_dict['gps_heading'] = heading
                    nav_data_dict['gps_speed'] = 0
                    nav_data_dict['gps_altitude_amsl'] = alt
                else:
                    # Position, initial course, speed and altitude queries
                    nav_data_dict['position'] = position_sep_input()
                    nav_data_dict['gps_heading'] = heading_input()
                    nav_data_dict['gps_speed'] = speed_input()
                    nav_data_dict['gps_altitude_amsl'] = alt_input()

                # Initialize NmeaMsg object
                self.nmea_obj = NmeaMsg(position=nav_data_dict['position'],
                                        altitude=nav_data_dict['gps_altitude_amsl'],
                                        speed=nav_data_dict['gps_speed'],
                                        heading=nav_data_dict['gps_heading'])
                action()
                break
        
        # Changing the unit's course and speed by the user in the main thread.
        first_run = True
        while True:
            if not self.nmea_thread.is_alive():
                print('\n\n*** Closing the script... ***\n')
                sys.exit()
            try:
                if first_run:
                    time.sleep(2)
                    first_run = False
                try:
                    prompt = input('Press "Enter" to change course/speed/altitude or "Ctrl + c" to exit...\n')
                except KeyboardInterrupt:
                    print('\n\n*** Closing the script... ***\n')
                    sys.exit()
                if prompt == '':
                    # Get active values
                    old_heading = self.nmea_obj.get_heading
                    old_speed = self.nmea_obj.get_speed
                    old_altitude = self.nmea_obj.get_altitude
                    new_heading, new_speed, new_altitude = change_input(self, old_heading, old_speed, old_altitude)

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
                    else:
                        # Set targeted head, speed and altitude without connected clients
                        self.nmea_obj.heading_targeted = new_heading
                        self.nmea_obj.speed_targeted = new_speed
                        self.nmea_obj.altitude_targeted = new_altitude
            except KeyboardInterrupt:
                print('\n\n*** Closing the script... ***\n')
                sys.exit()

    def nmea_serial(self):
        """
        Runs serial which emulates NMEA server-device
        """
        # serial_port = '/dev/ttyUSB0'
        # Serial configuration query
        serial_config = serial_config_input()
        self.nmea_thread = NmeaSerialThread(name=f'nmea_srv{uuid.uuid4().hex}',
                                       daemon=True,
                                       serial_config=serial_config,
                                       nmea_object=self.nmea_obj)
        self.nmea_thread.start()

    def nmea_logging(self):
        """
        Runs in debug mode which outputs NMEA messages to log
        """
        filter_mess = filter_input()
        self.nmea_thread = NmeaOutputThread(name=f'nmea_srv{uuid.uuid4().hex}',
                                       daemon=True,
                                       filter_mess=filter_mess,
                                       nmea_object=self.nmea_obj)
        self.nmea_thread.start()

    def nmea_tcp_server(self):
        """
        Runs telnet server which emulates NMEA device.
        """
        # Local TCP server IP address and port number.
        srv_ip_address, srv_port = ip_port_input('telnet')
        self.nmea_thread = threading.Thread(target=run_telnet_server_thread,
                                            args=[srv_ip_address, srv_port, self.nmea_obj],
                                            daemon=True,
                                            name='nmea_thread')
        self.nmea_thread.start()

    def nmea_stream(self):
        """
        Runs TCP or UDP NMEA stream to designated host.
        """
        # IP address and port number query
        ip_add, port = ip_port_input('stream')
        # Transport protocol query.
        stream_proto = trans_proto_input()
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
    # Open menu
    Menu().run()


