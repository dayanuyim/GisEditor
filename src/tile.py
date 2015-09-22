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
from coord import CoordinateSystem

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

    def __init__(self, cache_dir=None):
        #self.map_id = "TM25K_2001"
        #self.map_title = "2001-臺灣經建3版地形圖-1:25,000"
        #self.lower_corner = (117.84953432, 21.65607265)
        #self.upper_corner = (123.85924109, 25.64233621)
        #self.url_template = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2001-jpg-%d-%d-%d"
        #self.level_min = 7
        #self.level_max = 16

        self.__cache_dir = cache_dir if cache_dir is not None else './cache' 
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
        #print("File", path)

        if not os.path.exists(path):
            self.__downloadTile(level, x, y, path)
        return Image.open(path)

    def __downloadTile(self, level, x, y, file_path):
        url = self.url_template % (level, x, y)
        print("DL", url)

        #urllib.request.urlretrieve(url, file_path)
        with urllib.request.urlopen(url) as response, open(file_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)

def getTM25Kv3TileMap(cache_dir):
    tm = TileMap(cache_dir=cache_dir)
    tm.map_id = "TM25K_2001"
    tm.map_title = "2001-臺灣經建3版地形圖-1:25,000"
    tm.lower_corner = (117.84953432, 21.65607265)
    tm.upper_corner = (123.85924109, 25.64233621)
    tm.url_template = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2001-jpg-%d-%d-%d"
    tm.level_min = 7
    tm.level_max = 16
    return tm

def getTM25Kv4TileMap(cache_dir):
    tm = TileMap(cache_dir=cache_dir)
    tm.map_id = "TM25K_2003"
    tm.map_title = "2001-臺灣經建4版地形圖-1:25,000"
    tm.lower_corner = (117.84953432, 21.65607265)
    tm.upper_corner = (123.85924109, 25.64233621)
    tm.url_template = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2003-jpg-%d-%d-%d"
    tm.level_min = 5
    tm.level_max = 17
    return tm


# The class represent a unique geographic point, and designed to be 'immutable'.
# 'level' is the 'granularity' needed to init px/py and access px/py.
class GeoPoint:
    MAX_LEVEL = 23

    def __init__(self, lat=None, lon=None, px=None, py=None, level=None, tm2_67x=None, tm2_67y=None):
        if lat is not None and lon is not None:
            self.__setLatlon(lat, lon)
        elif px is not None and py is not None and level is not None:
            self.__setPixcel(px, py, level)
        elif tm2_67x is not None and tm2_67y is not None:
            self.__setTM2_67(tm2_67x, tm2_67y)
        else:
            raise ValueError("Not propriate init")

    # Fileds init ===================
    def __setLatlon(self, lat, lon):
        self.__lat = lat
        self.__lon = lon
        self.__px = None
        self.__py = None
        self.__tm2_67x = None
        self.__tm2_67y = None

    def __setPixcel(self, px, py, level):
        self.__lat = None
        self.__lon = None
        self.__px = px << (self.MAX_LEVEL - level)  #px of max level
        self.__py = py << (self.MAX_LEVEL - level)  #py of max level
        self.__tm2_67x = None
        self.__tm2_67y = None

    def __setTM2_67(self, tm2_67x, tm2_67y):
        self.__lat = None
        self.__lon = None
        self.__px = None
        self.__py = None
        self.__tm2_67x = tm2_67x
        self.__tm2_67y = tm2_67y

    # convert: All->TWD97/LatLon
    def __checkLatlon(self):
        if self.__lat is None or self.__lon is None:
            if self.__px is not None and self.__py is not None:
                self.__lat, self.__lon = TileSystem.getLatLonByPixcelXY(self.__px, self.__py, self.MAX_LEVEL)
            elif self.__tm2_67x is not None and self.__tm2_67y is not None:
                self.__lat, self.__lon = CoordinateSystem.TWD67_TM2ToTWD97_LatLon(self.__tm2_67x, self.__tm2_67y)
            else:
                raise ValueError("Not propriate init")

    # convert TWD97/LatLon -> each =========
    def __checkPixcel(self):
        if self.__px is None or self.__py is None:
            self.__checkLatlon()
            self.__px, self.__py = TileSystem.getPixcelXYByLatLon(self.__lat, self.__lon, self.MAX_LEVEL)

    def __checkTM2_67(self):
        if self.__tm2_67x is None or self.__tm2_67y is None:
            self.__checkLatlon()
            self.__tm2_67x, self.__tm2_67y = CoordinateSystem.TWD97_LatLonToTWD67_TM2(self.__lat, self.__lon)
    

    #accesor LatLon  ==========
    @property
    def lat(self):
        self.__checkLatlon()
        return self.__lat

    @property
    def lon(self):
        self.__checkLatlon()
        return self.__lon

    #accesor Pixel  ==========
    def px(self, level):
        self.__checkPixcel()
        return self.__px >> (self.MAX_LEVEL - level)

    def py(self, level):
        self.__checkPixcel()
        return self.__py >> (self.MAX_LEVEL - level)

    def pixcel(self, level):
        return (self.px(level), self.py(level))

    def incPixcel(self, px, py, level):
        px = self.px(level) + px
        py = self.py(level) + py
        return GeoPoint(px=px, py=py, level=level)

    #accesor TWD67 TM2 ==========
    @property
    def tm2_67x(self):
        self.__checkTM2_67()
        return self.__tm2_67x

    @property
    def tm2_67y(self):
        self.__checkTM2_67()
        return self.__tm2_67y

class GeoPoint2:
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

