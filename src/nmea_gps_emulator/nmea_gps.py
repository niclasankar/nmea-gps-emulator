import random
from math import ceil
import datetime
from datetime import timezone 
from typing import Union

from pyproj import Geod
from pygeomag import GeoMag

class NmeaMsg:
    """
    The class represent a group of NMEA sentences.
    """
    def __init__(self, position: dict, altitude: float, speed: float, heading: float):
        # Instance attributes
        self.utc_date_time = datetime.datetime.utcnow()
        print(self.utc_date_time)
        self.utc_date_time = datetime.datetime.now(timezone.utc)
        print(self.utc_date_time)
        self.position = position

        # The unit's speed provided by the user during the operation of the script
        self.speed = speed
        self.speed_targeted = speed

        # The unit's heading provided by the user during the operation of the script
        self.heading = heading
        self.heading_targeted = heading

        # The unit's altitude provided by the user during the operation of the script
        self.altitude = altitude
        self.altitude_targeted = altitude

        # The magnetic variation is set to dmmy values
        self.magvar = 0
        self.magvar_direct = 'E'
        self._magvar_update()

        # NMEA sentences initialization - by default with 15 sats
        self.gpgsv_group = GpgsvGroup()
        # DOP and active satellites
        self.gpgsa = Gpgsa(gpgsv_group=self.gpgsv_group)
        # Fix data message
        self.gpgga = Gpgga(sats_count=self.gpgsa.sats_count,
                         utc_date_time=self.utc_date_time,
                         position=position,
                         altitude=altitude,
                         antenna_altitude_above_msl=altitude+2.5)
        # Position data: position fix, time of position fix, and status
        self.gpgll = Gpgll(utc_date_time=self.utc_date_time,
                           position=position)
        # Recommended minimum specific GPS/Transit data
        self.gprmc = Gprmc(utc_date_time=self.utc_date_time,
                           position=position,
                           sog=speed,
                           cmg=heading,
                           magnetic_var_value=self.magvar,
                           magnetic_var_direct=self.magvar_direct)
        # True heading
        self.gphdt = Gphdt(heading=heading)
        # Track Made Good and Ground Speed
        self.gpvtg = Gpvtg(heading_true=heading, sog_knots=speed)
        # Time and zone
        self.gpzda = Gpzda(utc_date_time=self.utc_date_time)
        # All sentences
        self.nmea_sentences = [self.gpgga,
                               self.gpgsa,
                               *[gpgsv for gpgsv in self.gpgsv_group.gpgsv_instances],
                               self.gpgll,
                               self.gprmc,
                               self.gphdt,
                               self.gpvtg,
                               self.gpzda,]

    def __next__(self):
        utc_date_time_prev = self.utc_date_time
        self.utc_date_time = datetime.datetime.utcnow()
        if self.speed > 0:
            self.position_update(utc_date_time_prev)
        self._magvar_update()
        if self.heading != self.heading_targeted:
            self._heading_update()
        if self.speed != self.speed_targeted:
            self._speed_update()
        if self.altitude != self.altitude_targeted:
            self._altitude_update()
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
    
    @staticmethod
    def to_nmea_position(lat, lon) -> tuple:
        # Convert decimal position to NMEA format position for messages
        lat_degrees = int(lat)
        try:
            lat_minutes = round(lat % int(lat) * 60, 3)
        except ZeroDivisionError:
            lat_minutes = round(lat * 60, 3)
        if lat_minutes == 60:
            lat_degrees += 1
            lat_minutes = 0
        lon_degrees = int(lon)
        try:
            lon_minutes = round(lon % int(lon) * 60, 3)
        except ZeroDivisionError:
            lon_minutes = round(lon * 60, 3)
        if lon_minutes == 60:
            lon_degrees += 1
            lon_minutes = 0 
        return f'{lat_degrees:02}{lat_minutes:06.3f}', f'{lon_degrees:03}{lon_minutes:06.3f}'

    def position_update(self, utc_date_time_prev: datetime):
        """
        Update position when unit in move.
        """
        # The time that has elapsed since the last fix
        time_delta = (self.utc_date_time - utc_date_time_prev).total_seconds()
        # Knots to m/s conversion.
        speed_ms = self.speed * 0.514444
        # Distance in meters.
        distance = speed_ms * time_delta
        
        # Assignment of coords.
        lat_a = self.position['latitude_value']
        lat_direction = self.position['latitude_direction']
        lon_a = self.position['longitude_value']
        lon_direction = self.position['longitude_direction']
        
        # Use WGS84 ellipsoid
        g = Geod(ellps='WGS84')

        # Forward transformation - returns longitude, latitude, back azimuth of terminus points
        lon_end, lat_end, back_azimuth = g.fwd(lon_a, lat_a, self.heading, distance)

        # Change direction when cross the equator or prime meridian (Greenwich)
        if lat_end >= 0:
            lat_direction = 'N'
        else:
            lat_direction = 'S'
        if lon_end >= 0:
            lon_direction = 'E'
        else:
            lon_direction = 'W'
        lon_end, lat_end = abs(lon_end), abs(lat_end)

        # Convert the new position to NMEA form and store
        nmea_pos_lat, nmea_pos_lon = self.to_nmea_position(lat_end,lon_end)
        self.position['latitude_nmea_value'] = nmea_pos_lat
        self.position['longitude_nmea_value'] = nmea_pos_lon

        # Store the new position
        self.position['latitude_value'] = lat_end 
        self.position['latitude_direction'] = f'{lat_direction.upper()}'
        self.position['longitude_value'] = lon_end
        self.position['longitude_direction'] = f'{lon_direction.upper()}'

    def _heading_update(self):
        """
        Updates the unit's heading (course) in case of changes performed by the user.
        """
        head_target = self.heading_targeted
        head_current = self.heading
        turn_angle = head_target - head_current
        # Heading increment in each position update
        head_increment = 3
        # Immediate change of course when the increment <= turn_angle
        if abs(turn_angle) <= head_increment:
            head_current = head_target
        else:
            # The unit's heading is increased gradually (with 'head_increment')
            if head_target > head_current:
                if abs(turn_angle) > 180:
                    if turn_angle > 0:
                        head_current -= head_increment
                    else:
                        head_current += head_increment
                else:
                    if turn_angle > 0:
                        head_current += head_increment
                    else:
                        head_current -= head_increment
            else:
                if abs(turn_angle) > 180:
                    if turn_angle > 0:
                        head_current -= head_increment
                    else:
                        head_current += head_increment
                else:
                    if turn_angle > 0:
                        head_current += head_increment
                    else:
                        head_current -= head_increment
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
        """
        speed_target = self.speed_targeted
        speed_current = self.speed
        speed_diff = speed_target - speed_current
        # Heading increment in each position update
        speed_increment = 3
        # Immediate change of course when the increment <= turn_angle
        if abs(speed_diff) <= speed_increment:
            speed_current = speed_target
        elif speed_target > speed_current:
            speed_current += speed_increment
        else:
            speed_current -= speed_increment
        self.speed = round(speed_current, 3)

    def _altitude_update(self):
        """
        Updates the unit's altitude in case of changes performed by the user.
        """
        altitude_target = self.altitude_targeted
        altitude_current = self.altitude
        altitude_diff = altitude_target - altitude_current
        # Altitude increment in each position update
        altitude_increment = 0.5
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
        Updates the magnetic variation from WMM in pygeomag
        """
        datedec = round(int(self.utc_date_time.year) + int(self.utc_date_time.month)/12 + int(self.utc_date_time.day)/365.25, 2)

        lat = self.position['latitude_value']
        lon = self.position['longitude_value']
        alt = self.altitude

        gm = GeoMag()
        result = gm.calculate(glat=lat, glon=lon, alt=alt, time=datedec)
        self.magvar = result.d
        #print(result.d)
        #print(f'{result.d:06.2f}')

        if result.d > 0:
            self.magvar_direct = 'E'
        else:
            self.magvar_direct = 'W'

    @staticmethod
    def check_sum(data: str):
        """
        Function changes ASCII char to decimal representation, perform XOR operation of
        all the bytes between the $ and the * (not including the delimiters themselves),
        and returns NMEA check-sum in hexadecimal notation.
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
        return self.position['latitude_value']

    @property
    def get_longitude(self) -> float:
        return self.position['latitude_value']

    @property
    def get_speed(self) -> float:
        return self.speed

    @property
    def get_heading(self) -> float:
        return self.heading

    @property
    def get_altitude(self) -> float:
        return self.altitude
    
    @property
    def get_targetspeed(self) -> float:
        return self.speed_targeted
    
    @property
    def get_targetheading(self) -> float:
        return self.heading_targeted
    
    @property
    def get_targetaltitude(self) -> float:
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
        2: Differential GPS fix (DGNSS), SBAS, OmniSTAR VBS, Beacon, RTX in GVBS mode
        3: Not applicable
        4: RTK Fixed, xFill
        5: RTK Float, OmniSTAR XP/HP, Location RTK, RTX
        6: INS Dead reckoning
    7 	Number of SVs in use, range from 00 through to 24+
    8 	HDOP
    9 	Orthometric height (MSL reference)
    10 	M: unit of measure for orthometric height is meters
    11 	Geoid separation
    12 	M: geoid separation measured in meters
    13 	Age of differential GPS data record, Type 1 or Type 9. Null field when DGPS is not used.
    14 	Reference station ID, range 0000 to 4095. A null field when any reference station ID is selected and no corrections are received.
    15 	The checksum data, always begins with *
    """
    sentence_id: str = 'GPGGA'

    def __init__(self, sats_count, utc_date_time, position, altitude, antenna_altitude_above_msl=32.5, fix_quality=1,
                 hdop=0.92, dgps_last_update='', dgps_ref_station_id=''):
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
        nmea_lat, nmea_lon = NmeaMsg.to_nmea_position(56.9, 12.7)
        nmea_output = f'{self.sentence_id},{self.utc_time}.00,{self.position["latitude_nmea_value"]},' \
                      f'{self.position["latitude_direction"]},{self.position["longitude_nmea_value"]},' \
                      f'{self.position["longitude_direction"]},{self.fix_quality},' \
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
        nmea_lat, nmea_lon = NmeaMsg.to_nmea_position(56.9, 12.7)
        nmea_output = f'{self.sentence_id},{self.position["latitude_nmea_value"]},' \
                      f'{self.position["latitude_direction"]},{self.position["longitude_nmea_value"]},' \
                      f'{self.position["longitude_direction"]},{self.utc_time}.000,' \
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

    def __init__(self, utc_date_time, position, sog, cmg, data_status='A', faa_mode='A', magnetic_var_value='',
                 magnetic_var_direct=''):
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
        self.magnetic_var_value = magnetic_var_value
        self.magnetic_var_direct = magnetic_var_direct
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
                      f'{self.position["latitude_nmea_value"]},{self.position["latitude_direction"]},' \
                      f'{self.position["longitude_nmea_value"]},{self.position["longitude_direction"]},' \
                      f'{self.sog:.3f},{self.cmg},{self.utc_date},' \
                      f'{self.magnetic_var_value:06.2f},{self.magnetic_var_direct},{self.faa_mode}'
        return f'${nmea_output}*{NmeaMsg.check_sum(nmea_output)}\r\n'


class Gpgsa:
    """
    GPS DOP and active satellites
    Example: $GPGSA,A,3,19,28,14,18,27,22,31,39,,,,,1.7,1.0,1.3*35
    """
    sentence_id: str = 'GPGSA'

    def __init__(self, gpgsv_group, select_mode='A', mode=3, pdop=1.56, hdop=0.92, vdop=1.25):
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
    The class initializes the relevant number of GPGSV sentences depending on the specified number of satellites.
    """
    sats_in_sentence = 4

    def __init__(self, sats_total=15):
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
    """
    sentence_id: str = 'GPGSV'

    def __init__(self, num_of_gsv_in_group, sentence_num, sats_total, sats_in_sentence, sats_ids):
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
    """
    sentence_id = 'GPHDT'

    def __init__(self, heading):
        self.heading = heading

    def __str__(self):
        nmea_output = f'{self.sentence_id},{self.heading},T'
        return f'${nmea_output}*{NmeaMsg.check_sum(nmea_output)}\r\n'


class Gpvtg:
    """
    Track Made Good and Ground Speed.
    Example: $GPVTG,360.0,T,348.7,M,000.0,N,000.0,K*43
    """
    sentence_id = 'GPVTG'

    def __init__(self, heading_true: float, sog_knots: float, heading_magnetic: Union[float, str] = '') -> None:
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
    Time and date - UTC and local Time Zone
    Example: $GPZDA,095942.000,13,07,2020,0,0*50
    """
    sentence_id = 'GPZDA'

    def __init__(self, utc_date_time):
        # UTC time in format: 211250
        self.utc_time = utc_date_time

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
        # Local Zone not used
        nmea_output = f'{self.sentence_id},{self.utc_time}.000,{self.utc_date},0,0'
        return f'${nmea_output}*{NmeaMsg.check_sum(nmea_output)}\r\n'

