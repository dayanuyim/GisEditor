#!/usr/bin/env python3

""" handle pic """

from PIL import Image, ExifTags
from tile import GeoPoint
from gpx import WayPoint
from datetime import datetime
import conf

class PicDocument(WayPoint):
    @property
    def img(self): return self.__img

    def __init__(self, path, tz=None):
        self.__tz = tz
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
        self.sym = conf.getSymbol(self.name)

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

    def exifToDateTime(self, time_str):
        time = datetime.strptime(time_str, "%Y:%m:%d %H:%M:%S")
        if self.__tz is not None:
            time -= self.__tz  #to utc
        return time

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
