#!/usr/bin/env python3

import math
from math import tan, sin, cos, radians, degrees, floor

class CoordinateSystem2:
    @staticmethod
    #經緯度度分秒 -> 經緯度十進位
    def LatLon_degreeToDecimal(lat, lon):
        (lat_d, lat_m, lat_s) = lat
        (lon_d, lon_m, lon_s) = lon

        lat = lat_d + lat_m/60 + lat_s/3600
        lon = lon_d + lon_m/60 + lon_s/3600
        return (lat, lon)

    @staticmethod
    #經緯度十進位 -> 經緯度度分秒
    def LatLon_decimalToDegree(lat, lon):
        lat_d = int(lat)
        lat_m = int( (lat - lat_d) * 60)
        lat_s = ((lat - lat_d) * 60 - lat_m) * 60

        lon_d = int(lon)
        lon_m = int( (lon - lon_d) * 60)
        lon_s = ((lon - lon_d) * 60 - lon_m) * 60

        return (lat_d, lat_m, lat_s), (lon_d, lon_m, lon_s)

    a = 6378137.0
    b = 6356752.3142451
    lon0 = radians(121)
    k0 = 0.9999
    dx = 250000
    dy = 0
    e = 1 - b**2 / a**2
    e2 = e / b**2 / a**2

    #TWD97, lat/lon -> tm2
    @classmethod
    def TWD97_LatLonToTWD97_TM2(cls, lat, lon):
        a = cls.a
        b = cls.b
        lon0 = cls.lon0
        k0 = cls.k0
        dx = cls.dx
        dy = cls.dy
        e = cls.e
        e2 = cls.e2

        lon = (lon - floor((lon + 180) / 360) * 360) * math.pi / 180
        lat = lat * math.pi / 180

        V = a / (1 - e * sin(lat)**2)**0.5
        T = tan(lat)**2
        C = e2 * cos(lat)** 2
        A = cos(lat) * (lon - lon0)
        e_2 = e**2
        e_3 = e**3
        M = a *((1.0 - e / 4.0 - 3.0 * e_2 / 64.0 - 5.0 * e_3 / 256.0) * lat -
          (3.0 * e / 8.0 + 3.0 * e_2 / 32.0 + 45.0 * e_3 / 1024.0) *
          sin(2.0 * lat) + (15.0 * e_2 / 256.0 + 45.0 * e_3 / 1024.0) *
          sin(4.0 * lat) - (35.0 * e_3 / 3072.0) * sin(6.0 * lat))

        x = dx + k0 * V * (A + (1 - T + C) * A**3 / 6 + (5 - 18 * T + T**2 + 72 * C - 58 * e2) * A**5 / 120)
        y = dy + k0 * (M + V * tan(lat) * (A**2 / 2 + (5 - T + 9 * C + 4 * C**2) * A**4/ 24 + ( 61 - 58 * T + T**2 + 600 * C - 330 * e2) * A**6 / 720))
        return (x, y)

    @classmethod
    def TWD97_TM2ToTWD97_LatLan(cls, x, y):
        a = cls.a
        b = cls.b
        lon0 = cls.lon0
        k0 = cls.k0
        dx = cls.dx
        dy = cls.dy
        e = cls.e
        e2 = cls.e2

        x -= dx
        y -= dy

        #Calculate the Meridional Arc
        M = y / k0

        #Calculate Footprint Latitude
        mu = M / (a * (1.0 - e / 4.0 - 3 * e**2 / 64.0 - 5 * e**3 / 256.0))
        e1 = (1.0 - (1.0 - e)**0.5) / (1.0 + (1.0 - e)**0.5)

        J1 = (3 * e1 / 2 - 27 * e1**3 / 32.0)
        J2 = (21 * e1**2 / 16 - 55 * e1**4 / 32.0)
        J3 = (151 * e1**3 / 96.0)
        J4 = (1097 * e1**4 / 512.0)

        fp = mu + J1 * sin(2 * mu) + J2 * sin(4 * mu) + J3 * sin(6 * mu) + J4 * sin(8 * mu)

        # Calculate Latitude and Longitude
        C1 = e2 * cos(fp)**2
        T1 = tan(fp)**2
        R1 = a * (1 - e) / (1 - e * sin(fp)**2)**(3.0 / 2.0)
        N1 = a / (1 - e * sin(fp)**2)**0.5

        D = x / (N1 * k0)

        # 計算緯度
        Q1 = N1 * tan(fp) / R1
        Q2 = D**2 / 2.0
        Q3 = (5 + 3 * T1 + 10 * C1 - 4 * C1**2 - 9 * e2) * D**4 / 24.0
        Q4 = (61 + 90 * T1 + 298 * C1 + 45 * T1**2 - 3 * (C1**2) - 252 * e2) * (D**6) / 720.0
        lat = fp - Q1 * (Q2 - Q3 + Q4)

        # 計算經度
        Q5 = D
        Q6 = (1 + 2 * T1 + C1) * (D**3) / 6
        Q7 = (5 - 2 * C1 + 28 * T1 - 3 * (C1**2) + 8 * e2 + 24 * (T1**2)) * (D**5) / 120.0
        lon = lon0 + (Q5 - Q6 + Q7) / cos(fp)

        lat = degrees(lat)
        lon = degrees(lon)

        return (lat, lon)

    TM2_A= 0.00001549
    TM2_B= 0.000006521

    @classmethod
    def TWD67_TM2ToTWD97_TM2(cls, x, y):
        x97 = x + 807.8 + cls.TM2_A * x + cls.TM2_B * y
        y97 = y - 248.6 + cls.TM2_A * y + cls.TM2_B * x
        return (x97, y97)

    @classmethod
    def TWD97_TM2ToTWD67_TM2(cls, x, y):
        x67 = x - 807.8 - cls.TM2_A * x - cls.TM2_B * y
        y67 = y + 248.6 - cls.TM2_A * y - cls.TM2_B * x
        return (x67, y67)

def testLatLonToTm2(sample):
    for (lat, lon, x, y) in sample:
        (tm_x, tm_y) = CoordinateSystem.TWD97_LatLonToTWD97_TM2(lat, lon)
        dx = tm_x - x
        dy = tm_y - y
        print( (lat, lon, x, y), "latlon to tm2=", (tm_x, tm_y), "diff=", (dx, dy))


if __name__ == "__main__":
    sample = (
        #    Latitude 	Longitude 	Easting 	Northing
        (70.57927709, 45.59941973, 1548706.792, 8451449.199),
        (10.01889371, 23.31332382, 2624150.741, 1204434.042),
        (19.47989559, 75.66204923, 9855841.233, 6145496.115),
        (21.07246482, 29.82868439, 3206390.692, 2650745.4),
        (5.458957393, 36.38523737, 4328154.084, 749647.6237),
        (70.1754537, 22.86535023, 847598.2665, 7947180.962),
        (61.96560497, 58.93137085, 2727657.338, 8283916.696),
        (11.11604988, 20.90106919, 2331001.752, 1313608.225),
        (32.21054315, 60.70584911, 6035557.239, 5791770.792),
        (79.1874509, 61.53238249, 1064553.126, 9417273.737))

    testLatLonToTm2(sample)
