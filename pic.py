#!/usr/bin/env python3

""" handle pic """

from PIL import Image, ExifTags
from tile import GeoPoint
from gpx import WayPoint

class PicDocument(WayPoint):
    def __init__(self, path=None):
        self.__path = path
        self.__img = Image.open(path)
        self.__exif = self.getExif(self.__img)

        super().__init__(
            lat = self.exifDegreeToDecimal(self.__exif['GPSLatitudeRef'], self.__exif['GPSLatitude']),
            lon = self.exifDegreeToDecimal(self.__exif['GPSLongitudeRef'], self.__exif['GPSLongitude']))
        self.ele = None
        self.time = None
        self.name = self.__exif['ImageDescription'].encode('latin-1').decode('utf-8') #PIL use latin-1 by default
        self.desc = None
        self.cmt = None
        self.sym = None

    @staticmethod
    def exifDegreeToDecimal(ref, degree):
        (d, m, s) = degree
        dec = d[0]/d[1] + m[0]/m[1]/60 + s[0]/s[1]/3600
        if ref == 'S' or ref == 'W':
            return -dec
        return dec

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
