#!/usr/bin/env python3
# -*- coding: utf8 -*-

"""handle for tile system, especially WMTS"""

import os
import math
import tkinter as tk
import urllib.request
import shutil
from os import listdir
from os.path import isdir, isfile, exists
from PIL import Image, ImageTk, ImageDraw
from math import tan, sin, cos, radians, degrees

class TileSystem:
    EARTH_RADIUS = 6378137
    MIN_LATITUDE = -85.05112878
    MAX_LATITUDE = 85.05112878
    MIN_LONGITUDE = -180
    MAX_LONGITUDE = 180

    @staticmethod
    def crop(val, min_val, max_val):
        return min(max(val, min_val), max_val)

    @staticmethod
    def getMapSize(level):
        return 256 << level

    @classmethod
    def getValidLatitude(C, latitude):
        return C.crop(latitude, C.MIN_LATITUDE, C.MAX_LATITUDE)

    @classmethod
    def getValidLongitude(C, latitude):
        return C.crop(latitude, C.MIN_LONGITUDE, C.MAX_LONGITUDE)

    @classmethod
    def getGroundResolution(C, latitude, level):
        return math.cos(latitude * math.pi / 180) * 2 * math.pi * C.EARTH_RADIUS / C.getMapSize(level)

    @classmethod
    def getMapScale(C, latitude, level, screen_dpi):
        return C.getGroundResolution(latitude, level) * screen_dpi / 0.0254

    @classmethod
    def getPixcelXYByLatLon(C, latitude, longitude, level):
        latitude = C.crop(latitude, C.MIN_LATITUDE, C.MAX_LATITUDE)
        longitude = C.crop(longitude, C.MIN_LONGITUDE, C.MAX_LONGITUDE)

        x = (longitude + 180) / 360 
        sin_latitude = math.sin(latitude * math.pi / 180)
        y = 0.5 - math.log((1 + sin_latitude) / (1 - sin_latitude)) / (4 * math.pi)

        map_size = C.getMapSize(level)
        pixel_x = int(C.crop(x * map_size + 0.5, 0, map_size - 1))
        pixel_y = int(C.crop(y * map_size + 0.5, 0, map_size - 1))

        return (pixel_x, pixel_y)
    

    @classmethod
    def getLatLonByPixcelXY(C, pixel_x, pixel_y, level):
        map_size = C.getMapSize(level)
        x = (C.crop(pixel_x , 0, map_size - 1) / map_size) - 0.5
        y = 0.5 - (C.crop(pixel_y , 0, map_size - 1) / map_size)

        lat = 90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi
        lon = x * 360
        return (lat, lon)

    @staticmethod
    def getTileXYByPixcelXY(pixel_x, pixel_y):
        tile_x = int(pixel_x / 256)
        tile_y = int(pixel_y / 256)
        return (tile_x, tile_y)

    @staticmethod
    def getPixcelXYByTileXY(tile_x, tile_y):
        pixel_x = tile_x * 256
        pixel_y = tile_y * 256
        return (pixel_x, pixel_y)

    @classmethod
    def getTileXYByLatLon(C, latitude, longitude, level):
        (px, py) = C.getPixcelXYByLatLon(latitude, longitude, level)
        return C.getTileXYByPixcelXY(px, py)

class TileMap:
    def getMapName(self): return self.map_title

    def __init__(self):
        #self.map_id = "TM25K_2001"
        #self.map_title = "2001-臺灣經建3版地形圖-1:25,000"
        #self.lower_corner = (117.84953432, 21.65607265)
        #self.upper_corner = (123.85924109, 25.64233621)
        #self.url_template = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2001-jpg-%d-%d-%d"
        #self.level_min = 7
        #self.level_max = 16

        self.__cache_dir = './cache'
        if not os.path.exists(self.__cache_dir):
            os.makedirs(self.__cache_dir)

        self.__img_repo = {}

    def isSupportedLevel(self, level):
        return self.level_min <= level and level <= self.level_max

    def genTileName(self, level, x, y):
        return "%s-%d-%d-%d.jpg" % (self.map_id, level, x, y)

    #return tkinter.PhotoImage
    def getTileByLonLat(self, level, longitude, latitude):
        (x, y) = TileSystem.getTileXYByLatLon(latitude, longitude, level)
        return self.getTileByTileXY(level, x, y)

    def getTileByTileXY(self, level, x, y):
        name = self.genTileName(level, x, y)

        img = self.__img_repo.get(name)
        if img is None:
            img = self.__readTile(level, x, y)
            self.__img_repo[name] = img
        return img

    def __readTile(self, level, x, y):
        path = "%s/%s" % (self.__cache_dir, self.genTileName(level, x, y))
        if not os.path.exists(path):
            self.__downloadTile(level, x, y, path)
        print(path)
        return Image.open(path)

    def __downloadTile(self, level, x, y, file_path):
        url = self.url_template % (level, x, y)

        #urllib.request.urlretrieve(url, file_path)
        with urllib.request.urlopen(url) as response, open(file_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print(url)

def getTM25Kv3TileMap():
    tm = TileMap()
    tm.map_id = "TM25K_2001"
    tm.map_title = "2001-臺灣經建3版地形圖-1:25,000"
    tm.lower_corner = (117.84953432, 21.65607265)
    tm.upper_corner = (123.85924109, 25.64233621)
    tm.url_template = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2001-jpg-%d-%d-%d"
    tm.level_min = 7
    tm.level_max = 16
    return tm

def getTM25Kv4TileMap():
    tm = TileMap()
    tm.map_id = "TM25K_2003"
    tm.map_title = "2001-臺灣經建4版地形圖-1:25,000"
    tm.lower_corner = (117.84953432, 21.65607265)
    tm.upper_corner = (123.85924109, 25.64233621)
    tm.url_template = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2003-jpg-%d-%d-%d"
    tm.level_min = 5
    tm.level_max = 17
    return tm

class GeoPoint:
    MAX_LEVEL = 23

    def __init__(self, lat=None, lon=None, px=None, py=None, level=None):
        if (lat is not None and lon is not None) and (px is None and py is None and level is None):
            self.__lat = lat
            self.__lon = lon
            self.__level = None
            self.__px = None
            self.__py = None
        elif (px is not None and py is not None and level is not None) and (lat is None and lon is None):
            self.__lat = None
            self.__lon = None
            self.__px = px << (self.MAX_LEVEL - level)
            self.__py = py << (self.MAX_LEVEL - level)
            self.__level = level
        else:
            raise ValueError("Not propriate init")

    @property
    def lat(self):
        if self.__lat is None:
            (self.__lat, self.__lon) = TileSystem.getLatLonByPixcelXY(self.__px, self.__py, self.MAX_LEVEL)
        return self.__lat
    @lat.setter
    def lat(self, lat):
        self.__lat = lat
        self.__px = None
        self.__py = None

    @property
    def lon(self):
        if self.__lon is None:
            (self.__lat, self.__lon) = TileSystem.getLatLonByPixcelXY(self.__px, self.__py, self.MAX_LEVEL)
        return self.__lon
    @lon.setter
    def lon(self, lon):
        self.__lon = lon
        self.__px = None
        self.__py = None

    @property
    def level(self): return self.__level   #Note: level maybe None

    @level.setter
    def level(self, level): self.__level = level

    @property
    def px(self):
        if self.__px is None:
            (self.__px, self.__py) = TileSystem.getPixcelXYByLatLon(self.__lat, self.__lon, self.MAX_LEVEL)
        return self.__px >> (self.MAX_LEVEL - self.level)
    @px.setter
    def px(self, px):
        self.__lat = None
        self.__lon = None
        self.__px = px << (self.MAX_LEVEL - self.level)

    @property
    def py(self):
        if self.__py is None:
            (self.__px, self.__py) = TileSystem.getPixcelXYByLatLon(self.__lat, self.__lon, self.MAX_LEVEL)
        return self.__py >> (self.MAX_LEVEL - self.level)
    @py.setter
    def py(self, py):
        self.__lat = None
        self.__lon = None
        self.__py = py << (self.MAX_LEVEL - self.level)


class CoordinateSystem:
    """This object provide method for converting lat/lon coordinate to TWD97
    coordinate

    the formula reference to
    http://www.uwgb.edu/dutchs/UsefulData/UTMFormulas.htm (there is lots of typo)
    http://www.offshorediver.com/software/utm/Converting UTM to Latitude and Longitude.doc

    Parameters reference to
    http://rskl.geog.ntu.edu.tw/team/gis/doc/ArcGIS/WGS84%20and%20TM2.htm
    http://blog.minstrel.idv.tw/2004/06/taiwan-datum-parameter.html
    """
    # Equatorial radius
    a = 6378137.0
    # Polar radius
    b = 6356752.314245
    # central meridian of zone
    long0 = radians(121)
    # scale along long0
    k0 = 0.9999
    # delta x in meter
    dx = 250000

    @classmethod
    def TWD97_LatLonToTWD97_TM2(cls, lat, lon):
        """Convert lat lon to twd97
        """
        lat = radians(lat)
        lon = radians(lon)

        a = cls.a
        b = cls.b
        long0 = cls.long0
        k0 = cls.k0
        dx = cls.dx

        e = (1-b**2/a**2)**0.5
        e2 = e**2/(1-e**2)
        n = (a-b)/(a+b)
        nu = a/(1-(e**2)*(sin(lat)**2))**0.5
        p = lon-long0

        A = a*(1 - n + (5/4.0)*(n**2 - n**3) + (81/64.0)*(n**4  - n**5))
        B = (3*a*n/2.0)*(1 - n + (7/8.0)*(n**2 - n**3) + (55/64.0)*(n**4 - n**5))
        C = (15*a*(n**2)/16.0)*(1 - n + (3/4.0)*(n**2 - n**3))
        D = (35*a*(n**3)/48.0)*(1 - n + (11/16.0)*(n**2 - n**3))
        E = (315*a*(n**4)/51.0)*(1 - n)

        S = A*lat - B*sin(2*lat) + C*sin(4*lat) - D*sin(6*lat) + E*sin(8*lat)

        K1 = S*k0
        K2 = k0*nu*sin(2*lat)/4.0
        K3 = (k0*nu*sin(lat)*(cos(lat)**3)/24.0) * (5 - tan(lat)**2 + 9*e2*(cos(lat)**2) + 4*(e2**2)*(cos(lat)**4))

        y = K1 + K2*(p**2) + K3*(p**4)

        K4 = k0*nu*cos(lat)
        K5 = (k0*nu*(cos(lat)**3)/6.0) * (1 - tan(lat)**2 + e2*(cos(lat)**2))

        x = K4*p + K5*(p**3) + cls.dx

        return (x, y)

#    public class TMToLatLon {
#	/**
#		@brief TM coordinate to lat lon formula
#
#		reference to http://www.uwgb.edu/dutchs/UsefulData/UTMFormulas.htm
#
#		@param TMParameter object
#		@param x
#		@param y
#	**/
#	static public double[] convert(TMParameter tm, double x, double y) {
#		double dx = tm.getDx();
#		double dy = tm.getDy();
#		double lon0 = tm.getLon0();
#		double k0 = tm.getK0();
#		double a = tm.getA();
#		double b = tm.getB();
#		double e = tm.getE();
#
#		x -= dx;
#		y -= dy;
#
#		// Calculate the Meridional Arc
#		double M = y/k0;
#
#		// Calculate Footprint Latitude
#		double mu = M/(a*(1.0 - Math.pow(e, 2)/4.0 - 3*Math.pow(e, 4)/64.0 - 5*Math.pow(e, 6)/256.0));
#		double e1 = (1.0 - Math.pow((1.0 - Math.pow(e, 2)), 0.5)) / (1.0 + Math.pow((1.0 - Math.pow(e, 2)), 0.5));
#
#		double J1 = (3*e1/2 - 27*Math.pow(e1, 3)/32.0);
#		double J2 = (21*Math.pow(e1, 2)/16 - 55*Math.pow(e1, 4)/32.0);
#		double J3 = (151*Math.pow(e1, 3)/96.0);
#		double J4 = (1097*Math.pow(e1, 4)/512.0);
#
#		double fp = mu + J1*Math.sin(2*mu) + J2*Math.sin(4*mu) + J3*Math.sin(6*mu) + J4*Math.sin(8*mu);
#
#		// Calculate Latitude and Longitude
#
#		double e2 = Math.pow((e*a/b), 2);
#		double C1 = Math.pow(e2*Math.cos(fp), 2);
#		double T1 = Math.pow(Math.tan(fp), 2);
#		double R1 = a*(1-Math.pow(e, 2))/Math.pow((1-Math.pow(e, 2)*Math.pow(Math.sin(fp), 2)), (3.0/2.0));
#		double N1 = a/Math.pow((1-Math.pow(e, 2)*Math.pow(Math.sin(fp), 2)), 0.5);
#
#		double D = x/(N1*k0);
#
#		// lat
#		double Q1 = N1*Math.tan(fp)/R1;
#		double Q2 = (Math.pow(D, 2)/2.0);
#		double Q3 = (5 + 3*T1 + 10*C1 - 4*Math.pow(C1, 2) - 9*e2)*Math.pow(D, 4)/24.0;
#		double Q4 = (61 + 90*T1 + 298*C1 + 45*Math.pow(T1, 2) - 3*Math.pow(C1, 2) - 252*e2)*Math.pow(D, 6)/720.0;
#		double lat = fp - Q1*(Q2 - Q3 + Q4);
#
#		// long
#		double Q5 = D;
#		double Q6 = (1 + 2*T1 + C1)*Math.pow(D, 3)/6;
#		double Q7 = (5 - 2*C1 + 28*T1 - 3*Math.pow(C1, 2) + 8*e2 + 24*Math.pow(T1, 2))*Math.pow(D, 5)/120.0;
#		double lon = lon0 + (Q5 - Q6 + Q7)/Math.cos(fp);
#
#		return new double[] {Math.toDegrees(lat), Math.toDegrees(lon)};
#	}
#}

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

if __name__ == '__main__':
    lat = float(input('lat:'))
    lon = float(input('lon:'))
    print( 'input lat/lon', lat, lon)
    x, y = CoordinateSystem.TWD97_LatLonToTWD97_TM2(lat, lon)
    print (x, y)
