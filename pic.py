#!/usr/bin/env python3

""" handle pic """

from PIL import Image, ExifTags
from tile import GeoPoint
from gpx import WayPoint
from datetime import datetime
from sym import SymRule

class PicDocument(WayPoint):
    @property
    def img(self): return self.__img

    def __init__(self, path):
        self.__path = path
        self.__img = Image.open(path)
        self.__exif = self.getExif(self.__img)
        #for k, v in self.__exif.items(): #print(k, v)

        super().__init__(
            lat = self.exifToDegree(self.__exif['GPSLatitudeRef'], self.__exif['GPSLatitude']),
            lon = self.exifToDegree(self.__exif['GPSLongitudeRef'], self.__exif['GPSLongitude']))

        if 'ImageDescription' in self.__exif.keys():
            self.name = self.__exif['ImageDescription'].encode('latin-1').decode('utf-8') #PIL use latin-1 by default
        self.ele = self.exifToAltitude(self.__exif['GPSAltitudeRef'], self.__exif['GPSAltitude'])
        self.time = self.exifToDateTime(self.__exif['DateTimeOriginal'])

    @staticmethod
    def exifToDateTime(time_str):
        return datetime.strptime(time_str, "%Y:%m:%d %H:%M:%S")

    @staticmethod
    def exifToDegree(ref, degree):
        (d, m, s) = degree
        dec = d[0]/d[1] + m[0]/m[1]/60 + s[0]/s[1]/3600
        if ref == 'S' or ref == 'W':
            return -dec
        return dec

    @staticmethod
    def exifToAltitude(ref, alt):
        return ref + alt[0]/alt[1]

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
