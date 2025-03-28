#!/usr/bin/env python3

"""
Main test module of NMEA-GPS-EMULATOR.

Created in 2024
Based on the works of luk-kop

:author: ankars
:copyright: Ankars.se © 2024
:license: MIT

$GPGGA,083840.00,5002.31537,N,00833.57615,E,1,06,0.92,150,M,152.5,M,,*73
$GPGSA,A,3,19,14,23,08,32,20,,,,,,,1.56,0.92,1.25*0A
$GPGSV,4,1,15,04,48,327,97,30,38,247,10,06,71,325,41,18,38,143,73*71
$GPGSV,4,2,15,19,04,097,74,20,32,250,24,23,57,273,88,24,28,051,46*77
$GPGSV,4,3,15,28,88,126,15,14,24,087,32,13,58,119,15,29,67,331,77*75
$GPGSV,4,4,15,08,61,202,29,32,73,298,36,05,69,004,14*41
$GPGLL,5002.31537,N,00833.57615,E,083840.000,A,A*52
$GPRMC,083840.000,A,5002.31537,N,00833.57615,E,0.000,90.0,060924,003.27,E,A*08
$GPHDT,90.0,T*0C
$GPVTG,90.0,T,86.7,M,0,N,0.0,K*50
$GPZDA,083840.855497,06,09,2024,+01,00*70
"""
 
import unittest
from unittest import mock
from datetime import datetime

from nmea_gps import NmeaMsg, Gprmc, Gpgga, Gpzda, Gphdt, Gpgll, GpgsvGroup

class TestNmeaGps(unittest.TestCase):
    """
    Tests for NMEA sentences.
    """
    def setUp(self):
        #self.time = datetime(2021, 3, 9, 12, 9, 44, 855497)
        self.time = datetime(2024, 9, 6, 8, 38, 40, 855497)
        self.speed = 0
        self.course = 90.0
        self.altitude = 15.2
        self.position = {
            'lat': 50.03858955064544,
            'lat_dir': 'N',
            'lat_nmea': '5002.31537',
            'lng': 8.559602450767759,
            'lng_dir': 'E',
            'lng_nmea': '00833.57615'
        }

    def test_checksum(self):
        test_data = 'GPRMC,083840.000,A,5002.31537,N,00833.57615,E,0.000,90.0,060924,003.27,E,A'
        check_sum = NmeaMsg.check_sum(test_data)
        self.assertEqual(check_sum, "08")

    def test_gprmc_str(self):
        expected = '$GPRMC,083840.000,A,5002.31537,N,00833.57615,E,0.000,90.0,060924,000.00,E,A*0E\r\n'
        test_obj = Gprmc(utc_date_time=self.time,
                         position=self.position,
                         sog=self.speed,
                         cmg=self.course)
        self.assertEqual(test_obj.__str__(), expected)

    def test_gpgga_str(self):
        expected = '$GPGGA,083840.00,5002.31537,N,00833.57615,E,1,12,0.92,15.2,M,32.5,M,,*6D\r\n'
        test_obj = Gpgga(sats_count=12,
                         utc_date_time=self.time,
                         position=self.position,
                         altitude=self.altitude)
        self.assertEqual(test_obj.__str__(), expected)

    def test_gpzda_str(self):
        expected = '$GPZDA,083840.000,06,09,2024,+00,00*71\r\n'
        test_obj = Gpzda(utc_date_time=self.time)
        self.assertEqual(test_obj.__str__(), expected)

    def test_gphdt_str(self):
        expected = '$GPHDT,90.0,T*0C\r\n'
        test_obj = Gphdt(heading=self.course)
        self.assertEqual(test_obj.__str__(), expected)

    def test_gpgll_str(self):
        expected = '$GPGLL,5002.31537,N,00833.57615,E,083840.000,A,A*52\r\n'
        test_obj = Gpgll(utc_date_time=self.time,
                         position=self.position)
        self.assertEqual(test_obj.__str__(), expected)

    @mock.patch('random.randint')
    @mock.patch('random.sample')
    def test_gpgsv_group(self, mock_random_sample, mock_random_randint):

        expected = '$GPGSV,4,1,15,20,80,349,89,30,80,349,89,10,80,349,89,21,80,349,89*7B\r\n' \
                   '$GPGSV,4,2,15,03,80,349,89,02,80,349,89,19,80,349,89,08,80,349,89*7A\r\n' \
                   '$GPGSV,4,3,15,12,80,349,89,26,80,349,89,24,80,349,89,22,80,349,89*7B\r\n' \
                   '$GPGSV,4,4,15,09,80,349,89,01,80,349,89,25,80,349,89*45\r\n'

        mock_random_sample.return_value = ['20', '30', '10', '21', '03', '02', '19', '08', '12', '26', '24', '22', '09', '01', '25']
        mock_random_randint.side_effect = lambda x, y: y - 10

        test_obj = GpgsvGroup()
        print(test_obj.__str__())
        self.assertEqual(test_obj.__str__(), expected)


if __name__ == '__main__':
    unittest.main()