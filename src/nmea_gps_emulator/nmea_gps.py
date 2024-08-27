"""
Module for NMEA messages in NMEA-GPS-EMULATOR.

Created in 2024
Based on the works of luk-kop

:author: ankars
:copyright: Ankars.se © 2024
:license: MIT
"""

import random
import time
from math import ceil
import datetime
from datetime import timezone

from timezonefinder import TimezoneFinder
import pytz
from pyproj import Geod
from pygeomag import GeoMag
from pygeomag import decimal_year_from_date

from nmea_utils import ddd2nmea, ll2dir

class NmeaMsg:
    """
    The class represent a group of NMEA sentences.
    """
    def __init__(self, position_init: dict, altitude_init: float, speed_init: float, heading_init: float):
        """ Class Constructor.

        Creates the initial collection of NMEA messages from supplied values.

        :param dict position_init: initial position dictionary
        :param float altitude_init: initial altitude msl float value
        :param float speed_init: initial speed float value
        :param float heading_init: initial heading float value
        :return: None
        :rtype: None
        """
        # Instance attributes
        self.utc_date_time = datetime.datetime.now(timezone.utc)
        self.position = position_init
        self.position_backup = position_init

        # Get position and create NMEA form in dictionary
        lat = self.position['lat']
        lon = self.position['lng']
        self.position['lat_nmea'] = ddd2nmea(lat, 'lat')
        self.position['lng_nmea'] = ddd2nmea(lon, 'lng')
        self.position['lat_dir'] = ll2dir(lat, 'lat')
        self.position['lng_dir'] = ll2dir(lon, 'lng')

        # Get timezone offset
        timezone_offset_hours, timezone_offset_minutes = self.get_timezone_offset(lat, lon)

        # The unit's speed provided by the user during the operation of the script
        self.speed = speed_init
        self.speed_targeted = speed_init

        # The unit's altitude provided by the user during the operation of the script
        self.altitude = altitude_init
        self.altitude_targeted = altitude_init

        # The magnetic variation is set to dummy values
        self.magvar = 2.1
        self.magvar_dec = 2.1
        self.magvar_direct = 'E'
        # Calculate magnetic variation once if unit is stopped to get real values
        self._magvar_update()

        # The unit's heading provided by the user during the operation of the script
        self.heading = heading_init
        self.heading_targeted = heading_init
        # Calculate magnetic heading from heading
        self.heading_magnetic = self.heading - self.magvar

        # NMEA sentences initialization - by default with 15 sats
        self.gpgsv_group = GpgsvGroup()
        # DOP and active satellites
        self.gpgsa = Gpgsa(gpgsv_group=self.gpgsv_group)
        # Fix data message
        self.gpgga = Gpgga(sats_count=self.gpgsa.sats_count,
                         utc_date_time=self.utc_date_time,
                         position=position_init,
                         altitude=altitude_init,
                         antenna_altitude_above_msl=altitude_init+2.5)
        # Position data: position fix, time of position fix, and status
        self.gpgll = Gpgll(utc_date_time=self.utc_date_time,
                           position=position_init)
        # Recommended minimum specific GPS/Transit data
        self.gprmc = Gprmc(utc_date_time=self.utc_date_time,
                           position=position_init,
                           sog=speed_init,
                           cmg=heading_init,
                           magnetic_var_value=self.magvar,
                           magnetic_var_direct=self.magvar_direct)
        # True heading
        self.gphdt = Gphdt(heading=heading_init)
        # Track Made Good and Ground Speed
        self.gpvtg = Gpvtg(heading_true=heading_init, sog_knots=speed_init)
        # Time and zone
        self.gpzda = Gpzda(utc_date_time=self.utc_date_time,
                           offset_hrs=timezone_offset_hours,
                           offset_min=timezone_offset_minutes)
        # Change in progress flag
        self.change_in_progress = False
        # All sentences
        self.nmea_sentences = [self.gpgga,
                               self.gpgsa,
                               *[gpgsv for gpgsv in self.gpgsv_group.gpgsv_instances],
                               self.gpgll,
                               self.gprmc,
                               self.gphdt,
                               self.gpvtg,
                               self.gpzda,]
        print(self.position)

    def __next__(self):
        """ Iterator function.

        Calculates the next values for generation of NMEA messages.

        :return: list of NMEA messages
        :rtype: list
        """
        # Get time of last execution
        utc_date_time_prev = self.utc_date_time
        self.utc_date_time = datetime.datetime.now(timezone.utc)
        # If unit is moving update position
        if self.speed > 0:
            self.position_update(utc_date_time_prev)
            # Update magnetic variation value
            self._magvar_update()

        # Update heading and set progress flag
        if self.heading != self.heading_targeted:
            self.change_in_progress = True
            self._heading_update()

        # Update speed and set progress flag
        if self.speed != self.speed_targeted:
            self.change_in_progress = True
            self._speed_update()

        # Update altitude and set progress flag
        if self.altitude != self.altitude_targeted:
            self.change_in_progress = True
            self._altitude_update()

        # Get new position and update NMEA form and direction in dictionary
        lat = self.position['lat']
        lon = self.position['lng']
        self.position['lat_nmea'] = ddd2nmea(lat, 'lat')
        self.position['lng_nmea'] = ddd2nmea(lon, 'lng')
        self.position['lat_dir'] = ll2dir(lat, 'lat')
        self.position['lng_dir'] = ll2dir(lon, 'lng')
        
        # All updates done, print message
        if self.change_in_progress == True \
             and self.heading == self.heading_targeted \
             and self.speed == self.speed_targeted \
             and self.altitude == self.altitude_targeted:
            self.change_in_progress = False
            print('\n All updates ready...')
            print(f' Lat: {self.position['lat']}°{self.position['lat_dir']}')
            print(f' Lng: {self.position['lng']}°{self.position['lng_dir']}')
            print(f' Alt: {self.altitude} m')
            print(f' Spd: {self.speed} kt')
            print(f' Head: {self.heading}°')
            print('\n Press "Enter" to change course/speed/altitude or "Ctrl + c" to exit...\n')
            
        # Set new values in messages
        self.gpgga.utc_time = self.utc_date_time
        self.gpgga.altitude = self.altitude
        self.gpgga.antenna_altitude_above_msl = self.altitude + 2.5
        self.gpgll.utc_time = self.utc_date_time
        self.gprmc.utc_time = self.utc_date_time
        self.gprmc.sog = self.speed
        self.gprmc.cmg = self.heading
        self.gprmc.magnetic_var_value = self.magvar
        self.gprmc.magnetic_var_direct = self.magvar_direct
        self.gphdt.heading = self.heading
        self.gpvtg.heading_true = self.heading
        self.gpvtg.heading_magnetic = round(self.heading - self.magvar, 1)
        self.gpvtg.sog_knots = self.speed
        self.gpzda.utc_time = self.utc_date_time
        return self.nmea_sentences

    def __iter__(self):
        return self

    def __str__(self):
        nmea_msgs_str = ''
        for nmea in self.nmea_sentences:
            nmea_msgs_str += f'{nmea}'
        return nmea_msgs_str
    
    def get_timezone_offset(self, lat, lng):
        """
        The method gets the timezone and offset from latitude and longitude

        :param float lat: Latitude value
        :param float lng: Longitude value
        :return: UTC offset hours and minutes in a tuple
        :rtype: int, int
        """
        # Initialize TimezoneFinder
        tzf = TimezoneFinder()

        # Get the timezone name from latitude and longitude
        timezone_str = tzf.timezone_at(lng=lng, lat=lat)

        if timezone_str is None:
            return None, None

        # Get the timezone object from pytz
        pytz_tz = pytz.timezone(timezone_str)

        # Get the current time in the timezone
        current_time = datetime.datetime.now(pytz_tz)

        # Get the UTC offset in hours and minutes
        utc_offset_seconds = current_time.utcoffset().total_seconds() - current_time.dst().total_seconds()
        utc_offset_hours = int(utc_offset_seconds // 3600)
        utc_offset_minutes = int((utc_offset_seconds % 3600) // 60)

        return utc_offset_hours, utc_offset_minutes
    
    def position_update(self, utc_date_time_prev: datetime):
        """
        Update position when unit in move.

        :param datetime utc_date_time_prev: datetime object representing the last time function was called
        :return: None
        :rtype: None
        """
        # The time that has elapsed since the last fix
        time_delta = (self.utc_date_time - utc_date_time_prev).total_seconds()
        # Knots to m/s conversion.
        speed_ms = self.speed * 0.514444
        # Distance in meters.
        distance = speed_ms * time_delta
        
        # Assignment of old coords.
        lat_start = self.position['lat']
        lon_start = self.position['lng']
        
        # Use WGS84 ellipsoid
        g = Geod(ellps='WGS84')

        # Forward transformation - returns longitude, latitude, back azimuth of terminus points
        lon_end, lat_end, back_azimuth = g.fwd(lon_start, lat_start, self.heading, distance)

        # Store the new position
        self.position['lat'] = lat_end 
        self.position['lng'] = lon_end

    def _heading_update(self):
        """
        Updates the unit's heading (course) in case of changes performed by the user.

        :return: None
        :rtype: None
        """
        # Get active values
        head_target = self.heading_targeted
        head_current = self.heading
        turn_angle = head_target - head_current
        # Heading increment in each update
        heading_increment = 3
        # Immediate change of course when the head_increment <= turn_angle
        if abs(turn_angle) <= heading_increment:
            head_current = head_target
        else:
            # The unit's heading is increased gradually (with 'heading_increment')
            if head_target > head_current:
                if abs(turn_angle) > 180:
                    if turn_angle > 0:
                        head_current -= heading_increment
                    else:
                        head_current += heading_increment
                else:
                    if turn_angle > 0:
                        head_current += heading_increment
                    else:
                        head_current -= heading_increment
            else:
                if abs(turn_angle) > 180:
                    if turn_angle > 0:
                        head_current -= heading_increment
                    else:
                        head_current += heading_increment
                else:
                    if turn_angle > 0:
                        head_current += heading_increment
                    else:
                        head_current -= heading_increment
        # Heading range: 0-359
        if head_current == 360:
            head_current = 0
        elif head_current > 360:
            head_current -= 360
        elif head_current < 0:
            head_current += 360
        self.heading = round(head_current, 1)

    def _speed_update(self):
        """
        Updates the unit's speed in case of changes performed by the user.

        :return: None
        :rtype: None
        """
        speed_target = self.speed_targeted
        speed_current = self.speed
        speed_diff = speed_target - speed_current
        # Speed increment in each speed update
        speed_increment = 5
        # Immediate change of speed when the increment <= speed_target
        if abs(speed_diff) <= speed_increment:
            speed_current = speed_target
        elif speed_target > speed_current:
            speed_current += speed_increment
            #print(f'Increase to {speed_current} towards {speed_target}')
        else:
            speed_current -= speed_increment
            #print(f'Decrease to {speed_current} towards {speed_target}')
        self.speed = round(speed_current, 1)

    def _altitude_update(self):
        """
        Updates the unit's altitude in case of changes performed by the user.

        :return: None
        :rtype: None
        """
        # Get active values
        altitude_target = self.altitude_targeted
        altitude_current = self.altitude
        altitude_diff = altitude_target - altitude_current
        # Altitude increment in each position update
        altitude_increment = 3
        # Immediate change of course when the increment <= turn_angle
        if abs(altitude_diff) <= altitude_increment:
            altitude_current = altitude_target
        elif altitude_target > altitude_current:
            altitude_current += altitude_increment
        else:
            altitude_current -= altitude_increment
        self.altitude = round(altitude_current, 3)

    def _magvar_update(self):
        """
        Updates the magnetic declination variables from WMM in pygeomag
        Protected method

        :return: None
        :rtype: None
        """
        try:
            date_decimal = decimal_year_from_date(self.utc_date_time)
            lat = self.position['lat']
            lon = self.position['lng']
            alt = self.altitude
            gm = GeoMag()
            result = gm.calculate(glat=lat, glon=lon, alt=alt, time=date_decimal)
            self.magvar = abs(result.d)
            self.magvar_dec = result.d
            if result.d > 0:
                self.magvar_direct = 'E'
            else:
                self.magvar_direct = 'W'
        except Exception as error:
            print('Magnetic variation calculation error! Setting value to 0°E')
            self.magvar_dec = 0
            self.magvar_direct = 'E'

    @staticmethod
    def check_sum(data: str):
        """
        Function changes ASCII char to decimal representation, perform XOR operation of
        all the bytes between the $ and the * (not including the delimiters themselves),
        and returns NMEA check-sum in hexadecimal notation.

        :param str data: NMEA data string to create checksum for
        :return: Checksum
        :rtype: str
        """
        check_sum: int = 0
        for char in data:
            num = bytearray(char, encoding='utf-8')[0]
            # XOR operation.
            check_sum = (check_sum ^ num)
        # Returns only hex digits string without leading 0x.
        hex_str: str = str(hex(check_sum))[2:]
        if len(hex_str) == 2:
            return hex_str.upper()
        return f'0{hex_str}'.upper()
    
    @property
    def get_latitude(self) -> float:
        """ Property getter for latitude variable
        
        :return: float latitude value
        :rtype: float
        """
        return self.position['lat']

    @property
    def get_longitude(self) -> float:
        """ Property getter for longitude variable
        
        :return: float longitude value
        :rtype: float
        """
        return self.position['lng']

    @property
    def get_speed(self) -> float:
        """ Property getter for speed variable
        
        :return: float speed value
        :rtype: float
        """
        return self.speed

    @property
    def get_heading(self) -> float:
        """ Property getter for heading variable
        
        :return: float heading value
        :rtype: float
        """
        return self.heading

    @property
    def get_altitude(self) -> float:
        """ Property getter for altitude variable
        
        :return: float altitude value
        :rtype: float
        """
        return self.altitude
    
    @property
    def get_targetspeed(self) -> float:
        """ Property getter for target speed variable
        
        :return: float speed value
        :rtype: float
        """
        return self.speed_targeted
    
    @property
    def get_targetheading(self) -> float:
        """ Property getter for target heading variable
        
        :return: float heading value
        :rtype: float
        """
        return self.heading_targeted
    
    @property
    def get_targetaltitudedef(self) -> float:
        """ Property getter for target altitude variable
        
        :return: float altitude value
        :rtype: float
        """
        return self.altitude_targeted

class Gpgga:
    """
    Global Positioning System Fix Data
    Example: $GPGGA,140041.00,5436.70976,N,01839.98065,E,1,09,0.87,21.7,M,32.5,M,,*60\r\n

    0 	Message ID $GPGGA
    1 	UTC of position fix
    2 	Latitude
    3 	Direction of latitude:
        N: North
        S: South
    4 	Longitude
    5 	Direction of longitude:
        E: East
        W: West
    6 	GPS Quality indicator:
        0: Fix not valid
        1: GPS fix
        2: Differential GPS fix (DGNSS), SBAS, OmniSTAR VBS, Beacon,
           RTX in GVBS mode
        3: Not applicable
        4: RTK Fixed, xFill
        5: RTK Float, OmniSTAR XP/HP, Location RTK, RTX
        6: INS Dead reckoning
    7 	Number of SVs in use, range from 00 through to 24+
    8 	HDOP, Horizontal Dilution of Precision
    9 	Orthometric height (MSL reference)
    10 	M: unit of measure for orthometric height is meters
    11 	Geoid separation
    12 	M: geoid separation measured in meters
    13 	Age of differential GPS data record, Type 1 or Type 9.
        Null field when DGPS is not used.
    14 	Reference station ID, range 0000 to 4095. A null field when any
        reference station ID is selected and no corrections are received.
    15 	The checksum data, always begins with *
    """
    sentence_id: str = 'GPGGA'

    def __init__(self, sats_count: int, utc_date_time: datetime,
                 position: dict, altitude: float, 
                 antenna_altitude_above_msl: float=32.5, 
                 fix_quality: int=1, hdop: float=0.92, 
                 dgps_last_update: str='', dgps_ref_station_id: str=''):
        """ GPGGA Class Constructor.

        Initiates the GGA message object
        
        :param int sats_count: number of satellites in use
        :param datetime utc_date_time: UTC datetime object
        :param dict position: position dictionary
        :param float altitude: altitude msl
        :param float antenna_altitude_above_msl: altitude msl of antenna, defaults to 32.5
        :param int fix_quality: GPS fix quality indicator, defaults to 1
        :param float hdop: horizontal dilution of precision, defaults to 0.92
        :param str dgps_last_update: age of DGPS data record in seconds
        :param str dgps_ref_station_id: reference station ID, range 0000 to 4095, defaults to empty string
        """
        self.sats_count = sats_count
        self.utc_time = utc_date_time
        self.position = position
        self.fix_quality = fix_quality
        self.hdop = hdop
        self.altitude = altitude
        self.antenna_altitude_above_msl = antenna_altitude_above_msl
        self.dgps_last_update = dgps_last_update
        self.dgps_ref_station_id = dgps_ref_station_id

    @property
    def utc_time(self) -> str:
        return self._utc_time

    @utc_time.setter
    def utc_time(self, value) -> None:
        self._utc_time = value.strftime('%H%M%S')

    def __str__(self) -> str:
        nmea_output = f'{self.sentence_id},{self.utc_time}.00,{self.position["lat_nmea"]},' \
                      f'{self.position["lat_dir"]},{self.position["lng_nmea"]},' \
                      f'{self.position["lng_dir"]},{self.fix_quality},' \
                      f'{self.sats_count:02d},{self.hdop},{self.altitude},M,' \
                      f'{self.antenna_altitude_above_msl},M,{self.dgps_last_update},' \
                      f'{self.dgps_ref_station_id}'
        return f'${nmea_output}*{NmeaMsg.check_sum(nmea_output)}\r\n'


class Gpgll:
    """
    Position data: position fix, time of position fix, and status
    Example: $GPGLL,5432.216118,N,01832.663994,E,095942.000,A,A*58

    0 	Message ID $GPGLL
    1 	Latitude in dd mm,mmmm format (0-7 decimal places)
    2 	Direction of latitude N: North S: South
    3 	Longitude in ddd mm,mmmm format (0-7 decimal places)
    4 	Direction of longitude E: East W: West
    5 	UTC of position in hhmmss.ss format
    6 	Status indicator:
        A: Data valid
        V: Data not valid
        This value is set to V (Data not valid) for all Mode Indicator values except A (Autonomous) and D (Differential)
    7 	The checksum data, always begins with *

    Mode indicator:
        A: Autonomous mode
        D: Differential mode
        E: Estimated (dead reckoning) mode
        M: Manual input mode
        S: Simulator mode
        N: Data not valid
    """
    sentence_id: str = 'GPGLL'

    def __init__(self, utc_date_time, position, data_status='A', faa_mode='A'):
        """ GPGLL Class Constructor.

        Initiates the GLL message object
        
        :param datetime utc_date_time: UTC datetime object
        :param dict position: position dictionary
        :param str data_status: data status, defaults to A = valid
        :param str faa_mode: FAA Mode option
        """
        # UTC time in format: 211250
        self.utc_time = utc_date_time
        self.position = position
        self.data_status = data_status
        # FAA Mode option in NMEA 2.3 and later
        self.faa_mode = faa_mode

    @property
    def utc_time(self) -> str:
        return self._utc_time

    @utc_time.setter
    def utc_time(self, value) -> None:
        self._utc_time = value.strftime('%H%M%S')

    def __str__(self):
        nmea_output = f'{self.sentence_id},{self.position["lat_nmea"]},' \
                      f'{self.position["lat_dir"]},{self.position["lng_nmea"]},' \
                      f'{self.position["lng_dir"]},{self.utc_time}.000,' \
                      f'{self.data_status},{self.faa_mode}'
        return f'${nmea_output}*{NmeaMsg.check_sum(nmea_output)}\r\n'

class Gprmc:
    """
    Recommended minimum specific GPS/Transit data
    Example: $GPRMC,095940.000,A,5432.216088,N,01832.664132,E,0.019,0.00,130720,,,A*59

    0 	Message ID $GPRMC
    1 	UTC of position fix
    2 	Status A=active or V=void
    3 	Latitude
    4 	Longitude
    5 	Speed over the ground in knots
    6 	Track angle in degrees (True)
    7 	Date
    8 	Magnetic variation, in degrees
    9 	The checksum data, always begins with *
    """
    sentence_id = 'GPRMC'

    def __init__(self, utc_date_time, position, sog, cmg, data_status='A', faa_mode='A',
                  magnetic_var_value=0.0, magnetic_var_direct='E'):
        """ GPRMC Class Constructor.

        Initiates the RMC message object
        
        :param datetime utc_date_time: UTC datetime object
        :param dict position: position dictionary
        :param float sog: speed over ground in knots
        :param float cmg: course made good
        :param str data_status: data status, defaults to A = valid
        :param str faa_mode: FAA Mode option
        :param float magnetic_var_value: magnetic variation value
        :param str magnetic_var_direct: direction of magnetic variation
        """
        # UTC time in format: 211250
        self.utc_time = utc_date_time
        # UTC date in format: 130720
        self.data_status = data_status
        self.position = position
        # Speed Over Ground
        self.sog = sog
        # Magnetic variance
        self.magnetic_var_value = magnetic_var_value
        self.magnetic_var_direct = magnetic_var_direct
        # Course Made Good
        self.cmg = cmg
        # FAA Mode option in NMEA 2.3 and later
        self.faa_mode = faa_mode

    @property
    def utc_time(self) -> str:
        return self._utc_time

    @utc_time.setter
    def utc_time(self, value) -> None:
        self._utc_time = value.strftime('%H%M%S')
        self._utc_date = value.strftime('%d%m%y')

    @property
    def utc_date(self) -> str:
        return self._utc_date

    @utc_date.setter
    def utc_date(self, value) -> None:
        self._utc_date = value.strftime('%d%m%y')

    def __str__(self):
        nmea_output = f'{self.sentence_id},{self.utc_time}.000,{self.data_status},' \
                      f'{self.position["lat_nmea"]},{self.position["lat_dir"]},' \
                      f'{self.position["lng_nmea"]},{self.position["lng_dir"]},' \
                      f'{self.sog:.3f},{self.cmg},{self.utc_date},' \
                      f'{self.magnetic_var_value:06.2f},{self.magnetic_var_direct},{self.faa_mode}'
        return f'${nmea_output}*{NmeaMsg.check_sum(nmea_output)}\r\n'

class Gpgsa:
    """
    GPS DOP and active satellites
    Example: $GPGSA,A,3,19,28,14,18,27,22,31,39,,,,,1.7,1.0,1.3*35

    0 	Message ID $GNGSA
    1 	Mode 1:
        M = Manual
        A = Automatic
    2 	Mode 2: Fix type:
        1 = not available
        2 = 2D
        3 = 3D
    3 	PRN number:
        01 to 32 for GPS
        33 to 64 for SBAS
        64+ for GLONASS
    4 	PDOP: 0.5 to 99.9
    5 	HDOP: 0.5 to 99.9
    6 	VDOP: 0.5 to 99.9
    7 	The checksum data, always begins with *
    """
    sentence_id: str = 'GPGSA'

    def __init__(self, gpgsv_group, select_mode: str='A', mode: int=3, pdop: float=1.56, hdop: float=0.92, vdop: float=1.25):
        """ GPGSA Class Constructor.

        Initiates the GSA message object
        
        :param object gpgsv_group: reference to GPGSV object to use
        :param str select_mode: mode = M = Manual, A = Automatic, defaults to A
        :param int mode: mode fix type: 1 = not available, 2 = 2D, 3 = 3D, defaults to 3
        :param float pdop: position precision
        :param float hdop: horizontal precision
        :param float vdop: vertical precision
        """
        self.select_mode = select_mode
        self.mode = mode
        self.sats_ids = gpgsv_group.sats_ids
        self.pdop = pdop
        self.hdop = hdop
        self.vdop = vdop

    @property
    def sats_ids(self) -> list:
        return self._sats_ids

    @sats_ids.setter
    def sats_ids(self, value) -> None:
        self._sats_ids = random.sample(value, k=random.randint(4, 12))

    @property
    def sats_count(self) -> int:
        return len(self.sats_ids)

    def __str__(self) -> str:
        # IDs of sat used in position fix (12 fields), if less than 12 sats, fill fields with ''
        sats_ids_output = self.sats_ids[:]
        while len(sats_ids_output) < 12:
            sats_ids_output.append('')
        nmea_output = f'{self.sentence_id},{self.select_mode},{self.mode},' \
                      f'{",".join(sats_ids_output)},' \
                      f'{self.pdop},{self.hdop},{self.vdop}'
        return f'${nmea_output}*{NmeaMsg.check_sum(nmea_output)}\r\n'

class GpgsvGroup:
    """
    The class initializes the relevant number of GPGSV sentences depending
    on the specified number of satellites.
    """
    sats_in_sentence = 4

    def __init__(self, sats_total=15):
        """ GpgsvGroup Class Constructor.

        Collection of GPGSV messages
        
        :param int sats_total: number of satellites in use
        """
        self.gpgsv_instances = []
        self.sats_total = sats_total
        self.num_of_gsv_in_group = ceil(self.sats_total / self.sats_in_sentence)
        # List of satellites ids for all GPGSV sentences
        self.sats_ids = random.sample([f'{_:02d}' for _ in range(1,33)], k=self.sats_total)
        # Iterator for sentence sats IDs
        sats_ids_iter = iter(self.sats_ids)
        # Initialize GPGSV sentences
        for sentence_num in range(1, self.num_of_gsv_in_group + 1):
            if sentence_num == self.num_of_gsv_in_group and self.sats_total % self.sats_in_sentence != 0:
                self.sats_in_sentence = self.sats_total % self.sats_in_sentence
            sats_ids_sentence = [next(sats_ids_iter) for _ in range(self.sats_in_sentence)]
            gpgsv_sentence = Gpgsv(sats_total=self.sats_total,
                                   sats_in_sentence=self.sats_in_sentence,
                                   num_of_gsv_in_group=self.num_of_gsv_in_group,
                                   sentence_num=sentence_num,
                                   sats_ids=sats_ids_sentence)
            self.gpgsv_instances.append(gpgsv_sentence)

    @property
    def sats_total(self) -> int:
        return self._sats_total

    @sats_total.setter
    def sats_total(self, value) -> None:
        if int(value) < 4:
            self._sats_total = 4
        else:
            self._sats_total = value

    def __str__(self) -> str:
        gpgsv_group_str = ''
        for gpgsv in self.gpgsv_instances:
            gpgsv_group_str += f'{gpgsv}'
        return gpgsv_group_str

class Gpgsv:
    """
    GPS Satellites in view. During instance initialization will generate dummy (random) object's data.
    Example: $GPGSV,3,1,11,03,03,111,00,04,15,270,00,06,01,010,00,13,06,292,00*74

    0 	Message ID
    1 	Total number of messages of this type in this cycle
    2 	Message number
    3 	Total number of SVs visible
    4 	SV PRN number
    5 	Elevation, in degrees, 90° maximum
    6 	Azimuth, degrees from True North, 000° through 359°
    7 	SNR, 00 through 99 dB (null when not tracking)
    8 - 11 	Information about second SV, same format as fields 4 through 7
    12 - 15 Information about third SV, same format as fields 4 through 7
    16 - 19 Information about fourth SV, same format as fields 4 through 7
    20 	The checksum data, always begins with *
    """
    sentence_id: str = 'GPGSV'

    def __init__(self, num_of_gsv_in_group, sentence_num, sats_total, sats_in_sentence, sats_ids):
        """ GPGSV Class Constructor.

        Initiates the GSV message object. Creates random elevation, azimuth and S/N values for SV:s
        
        :param int num_of_gsv_in_group: Total number of messages of this type in this cycle
        :param int sentence_num: Message number
        :param int sats_total: Total number of SV:s visible
        :param int sats_in_sentence: Total number of SVs in this message
        :param int sats_ids: ID:s of SV:s
        """
        self.num_of_gsv_in_group = num_of_gsv_in_group
        self.sentence_num = sentence_num
        self.sats_total = sats_total
        self.sats_in_sentence = sats_in_sentence
        self.sats_ids = sats_ids
        self.sats_details = ''
        for sat in self.sats_ids:
            satellite_id: str = sat
            elevation: int = random.randint(0, 90)
            azimuth: int = random.randint(0, 359)
            snr: int = random.randint(0, 99)
            self.sats_details += f',{satellite_id},{elevation:02d},{azimuth:03d},{snr:02d}'

    def __str__(self) -> str:
        nmea_output = f'{self.sentence_id},{self.num_of_gsv_in_group},{self.sentence_num},' \
                      f'{self.sats_total}{self.sats_details}'
        return f'${nmea_output}*{NmeaMsg.check_sum(nmea_output)}\r\n'


class Gphdt:
    """
    Heading, True.
    Actual vessel heading in degrees true produced by any device or system producing true heading.
    Example: $GPHDT,274.07,T*03

    0 	Message ID $GPHDT
    1 	Heading in degrees
    2 	T: Indicates heading relative to True North
    3 	The checksum data, always begins with *
    """
    sentence_id = 'GPHDT'

    def __init__(self, heading):
        """ GPHDT Class Constructor.

        Initiates the HDT message object.
        
        :param float heading: Unit's heading
        """
        self.heading = heading

    def __str__(self):
        nmea_output = f'{self.sentence_id},{self.heading},T'
        return f'${nmea_output}*{NmeaMsg.check_sum(nmea_output)}\r\n'


class Gpvtg:
    """
    Track Made Good and Ground Speed.
    Example: $GPVTG,360.0,T,348.7,M,000.0,N,000.0,K*43

    0 	Message ID $GPVTG
    1 	Track made good (degrees true)
    2 	T: track made good is relative to true north
    3 	Track made good (degrees magnetic)
    4 	M: track made good is relative to magnetic north
    5 	Speed, in knots
    6 	N: speed is measured in knots
    7 	Speed over ground in kilometers/hour (kph)
    8 	K: speed over ground is measured in kph
    9 	Mode indicator:
        A: Autonomous mode
        D: Differential mode
        E: Estimated (dead reckoning) mode
        M: Manual Input mode
        S: Simulator mode
        N: Data not valid
    10 	The checksum data, always begins with *
    """
    sentence_id = 'GPVTG'

    def __init__(self, heading_true: float, sog_knots: float, heading_magnetic: float = 0.0) -> None:
        """ GPVTG Class Constructor.

        Initiates the VTG message object.
        
        :param float heading_true: Unit's heading true
        :param float sog_knots: Unit's speed
        :param float heading_magnetic: Unit's heading magnetic
        """
        self.heading_true = heading_true
        self.heading_magnetic = heading_magnetic
        self.sog_knots = sog_knots

    @property
    def sog_kmhr(self) -> float:
        """
        Return speed over ground is in kilometers/hour.
        """
        return round(self.sog_knots * 1.852, 1)

    def __str__(self) -> str:
        nmea_output = f'{self.sentence_id},{self.heading_true},T,{self.heading_magnetic},M,' \
                      f'{self.sog_knots},N,{self.sog_kmhr},K'
        return f'${nmea_output}*{NmeaMsg.check_sum(nmea_output)}\r\n'


class Gpzda:
    """
    GPZDA class

    Reference: https://receiverhelp.trimble.com/alloy-gnss/en-us/NMEA-0183messages_ZDA.html

    """
    sentence_id = 'GPZDA'

    def __init__(self, utc_date_time, offset_hrs:int=0, offset_min:int=0):
        """ GPZDA Class Constructor.

        Initiates the GPZDA message object.
        
        :param datetime utc_date_time: Datetime object to use
        """
        # UTC time in format: 211250
        self.utc_time = utc_date_time
        self.offset_hrs = offset_hrs
        self.offset_min = offset_min

    @property
    def utc_time(self) -> str:
        return self._utc_time

    @utc_time.setter
    def utc_time(self, value) -> None:
        self._utc_time = value.strftime('%H%M%S')
        self._utc_date = value.strftime('%d,%m,%Y')

    @property
    def utc_date(self) -> str:
        return self._utc_date

    @utc_date.setter
    def utc_date(self, value) -> None:
        self._utc_date = value.strftime('%d,%m,%Y')

    def __str__(self):
        # Local timezone is always the os timezone, not the position
        nmea_output = f'{self.sentence_id},{self.utc_time}.000,{self.utc_date},' \
                      f'{self.offset_hrs:+03},{self.offset_min:02}'
        return f'${nmea_output}*{NmeaMsg.check_sum(nmea_output)}\r\n'

