"""
Module for utilities for NMEA message output in NMEA-GPS-EMULATOR.

Created in 2024

:author: ankars
:copyright: Ankars.se © 2024
:license: MIT
"""

from datetime import datetime

def nmeall2ddd(pos: str) -> float:
    """
    Convert NMEA lat/lon string to (unsigned) decimal degrees.

    :param str pos: (d)ddmm.mmmmm
    :return: pos as decimal degrees
    :rtype: float value or None if invalid

    """
    try:
        dpt = pos.find(".")
        if dpt < 4:
            raise ValueError()
        posdeg = float(pos[0 : dpt - 2])
        posmin = float(pos[dpt - 2 :])
        return round((posdeg + posmin / 60), 10)
    except (TypeError, ValueError):
        return None
    
def ddd2nmeall(degrees: float, att: str, hprec: bool = False) -> str:
    """
    Convert decimal degrees to NMEA degrees decimal minutes string

    :param float degrees: decimal degrees
    :param str att: 'lat' for latitude or 'lng' for longitude
    :param bool hprec: higher precision (7 decimals/5 decimals)
    :return: degrees as (d)ddmm.mmmmm(mm) formatted string
    :rtype: str or None if invalid

    """
    try:
        degrees = abs(degrees)
        degrees, minutes = divmod(degrees * 60, 60)
        degrees = int(degrees * 100)
        if hprec:
            if att == 'lat':
                dmm = f"{degrees + minutes:.7f}".zfill(12)
            else:  # Longitude lng
                dmm = f"{degrees + minutes:.7f}".zfill(13)
        else:
            if att == 'lat':
                dmm = f"{degrees + minutes:.5f}".zfill(10)
            else:  # Longitude lng
                dmm = f"{degrees + minutes:.5f}".zfill(11)
        return dmm
    except (TypeError, ValueError):
        return None

def date2utc(dates: str, format: str = 'dt') -> datetime.date:
    """
    Convert NMEA Date string to UTC datetime.

    :param str dates: NMEA date
    :param str form: date format 'dt' = ddmmyy, 'dm' = mmddyy
    :return: UTC datetime YYyy:mm:dd
    :rtype: datetime.date or None if invalid
    """
    try:
        dateform = '%m%d%y' if format == 'dm' else '%d%m%y'
        utc = datetime.strptime(dates, dateform)
        return utc.date()
    except (TypeError, ValueError):
        return None


def time2utc(times: str) -> datetime.time:
    """
    Convert NMEA Time to UTC datetime.

    :param str times: NMEA time hhmmss.ss
    :return: UTC time hh:mm:ss.ss
    :rtype: datetime.time
    """

    try:
        if len(times) == 6:  # decimal seconds is omitted
            times = times + ".00"
        utc = datetime.strptime(times, "%H%M%S.%f")
        return utc.time()
    except (TypeError, ValueError):
        return ""

def time2str(tim: datetime.time) -> str:
    """
    Convert datetime.time to NMEA formatted string.

    :param datetime.time tim: time
    :return: NMEA formatted time string hhmmss.ss
    :rtype: str
    """

    try:
        return tim.strftime("%H%M%S.%f")[0:9]
    except (AttributeError, TypeError, ValueError):
        return ""


def date2str(dat: datetime.date, form: str = 'dt') -> str:
    """
    Convert datetime.date to NMEA formatted string.

    :param datetime.date dat: date
    :param str form: date format DT = ddmmyy, DM = mmddyy (DT)
    :return: NMEA formatted date string
    :rtype: str
    """

    try:
        dform = "%m%d%y" if form == 'dm' else "%d%m%y"
        return dat.strftime(dform)
    except (AttributeError, TypeError, ValueError):
        return ""