#!/usr/bin/env python3

""" handle pic """

import logging
from PIL import Image, ExifTags
from datetime import datetime
import pytz
#my
from src.util import getLocTimezone
from src.gpx import WayPoint
import src.sym as sym

class PicDocument(WayPoint):
    @property
    def img(self): return self.__img

    def __init__(self, path):
        self.__path = path
        self.__img = Image.open(path)
        self.__exif = self.getExif(self.__img)
        #for k, v in self.__exif.items():
        #    if isinstance(v, str):
        #        v = v.encode('latin-1').decode('utf-8') #PIL use latin-1 by default

        super().__init__(
            lat = self.exifToDegree(self.__exif['GPSLatitudeRef'], self.__exif['GPSLatitude']),
            lon = self.exifToDegree(self.__exif['GPSLongitudeRef'], self.__exif['GPSLongitude']))

        self.name = "" if 'ImageDescription' not in self.__exif else \
                self.__exif['ImageDescription'].encode('latin-1').decode('utf-8') #PIL use latin-1 by default
        self.ele = self.exifToAltitude(self.__exif['GPSAltitudeRef'], self.__exif['GPSAltitude'], 0.0)
        self.time = self.exifToDateTime(self.__exif['DateTimeOriginal'])
        self.sym = sym.toSymbol(self.name)

        orientation = self.__exif['Orientation']
        if orientation is not None:
            self.__img = self.rotateImage(self.__img, int(orientation))

    def rotateImage(self, img, orientation):
        if orientation == 1:
            return img
        elif orientation == 3:
            return img.transpose(Image.ROTATE_180)
        elif orientation == 6:
            return img.transpose(Image.ROTATE_270)
        elif orientation == 8:
            return img.transpose(Image.ROTATE_90)
        else:
            return img

    def exifToDateTime(self, time_str, def_value=None):
        try:
            time = datetime.strptime(time_str, "%Y:%m:%d %H:%M:%S") #local time
            if self.lat and self.lon:
                tz = getLocTimezone(lat=self.lat, lon=self.lon)
                time = tz.localize(time, is_dst=None).astimezone(pytz.utc)
            return time
        except Exception as ex:
            logging.error('Parsing Exif DateTime Error: ' + str(ex))
            #not to raise exception, may return None
            return def_value

    @staticmethod
    def exifToDegree(ref, degree, def_value=None):
        try:
            (d, m, s) = degree
            dec = d[0]/d[1] + m[0]/m[1]/60 + s[0]/s[1]/3600
            if ref == 'S' or ref == 'W':
                return -dec
            return dec
        except Exception as ex:
            logging.error('Parsing Exif Degree Error: ' + str(ex))
            if def_value:
                return def_value
            raise ex

    @staticmethod
    def exifToAltitude(ref, alt, def_value=None):
        try:
            #some implement make the filed 'bytes'
            if isinstance(ref, bytes):
                import struct
                ref = struct.unpack('B', ref)[0]  #bytes -> unsigned int
            return ref + alt[0]/alt[1]
        except Exception as ex:
            logging.error('Parsing Exif Altitude Error: ' +  str(ex))
            if def_value:
                return def_value
            raise ex

    @staticmethod
    def getExif(img):
        exif = {}

        for k, v in img._getexif().items():
            #exif
            if k not in ExifTags.TAGS:
                continue
            name = ExifTags.TAGS[k]
            exif[name] = v

            #exif - GPS
            if name == 'GPSInfo':
                for gk, gv in v.items():
                    if gk not in ExifTags.GPSTAGS:
                        continue
                    gname = ExifTags.GPSTAGS[gk]
                    exif[gname] = gv

        return exif
