#!/usr/bin/env python3

""" handle pic """

import logging
from PIL import Image, ExifTags
from datetime import datetime
import pytz
#my
from util import localToUtcTime, correctOrien, interpList
from gpx import WayPoint
import sym


def is_subscriptable(v):
    try:
        v[0]
        return True
    except TypeError:
        return False

class ExifParser:

    @classmethod
    def parse(cls, img):
        return cls.__exif_to_data(cls.__get_exif(img))

    @staticmethod
    def __get_exif(img):
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

    @classmethod
    def __exif_to_data(cls, exif):
        #for k, v in exif.items():
        #    if isinstance(v, str):
        #        v = v.encode('latin-1').decode('utf-8') #PIL use latin-1 by default

        data = {}

        ref = exif.get('GPSLatitudeRef')
        degree = exif.get('GPSLatitude')
        if ref is not None and degree is not None:
            data['lat'] = cls.__exifDegree(ref, degree)

        ref = exif.get('GPSLongitudeRef')
        degree = exif.get('GPSLongitude')
        if ref is not None and degree is not None:
            data['lon'] = cls.__exifDegree(ref, degree)

        desc = exif.get('ImageDescription')
        if desc is not None:
            data['desc'] = desc.encode('latin-1').decode('utf-8') #PIL use latin-1 by default

        ref = exif.get('GPSAltitudeRef')
        alt = exif.get('GPSAltitude')
        if ref is not None and alt is not None:
            data['alt'] = cls.__exifAltitude(ref, alt)

        timestr = exif.get('DateTimeOriginal')
        if timestr is not None:
            data['time'] = cls.__exifDatetime(timestr) #localtime

        orien = exif.get('Orientation')
        if orien is not None:
            data['orien'] = int(orien)

        return data


    @staticmethod
    def __exifDatetime(time_str):
        return datetime.strptime(time_str, "%Y:%m:%d %H:%M:%S") #local time

    @staticmethod
    def __exifDegree(ref, degree):
        (d, m, s) = degree

        dec = d[0]/d[1] + m[0]/m[1]/60 + s[0]/s[1]/3600 if is_subscriptable(d) else \
              d + m/60 + s/3600

        if ref == 'S' or ref == 'W':
            return -dec
        return dec

    @staticmethod
    def __exifAltitude(ref, alt):
        print(ref, alt)
        #some implement make the filed 'bytes'
        if isinstance(ref, bytes):
            import struct
            ref = struct.unpack('B', ref)[0]  #bytes -> unsigned int
        return ref + alt[0]/alt[1] if is_subscriptable(alt) else \
               ref + alt


# @loctable: the list of tuple (utctime, lat, lon, ele), ordered by time
def lookupLoc(loctable, time, islocal=False):
    if not loctable:
        return (None, None, None, None)

    if islocal:
        _, lat, lon, _ = loctable[0]
        time = localToUtcTime(time, lat, lon)

    for i in range(len(loctable)):
        if loctable[i][0] >= time:
            break

    loc2 = loctable[i]
    if loc2[0] == time:
        return loc2
    if i == 0:
        return (None, None, None, None)
    loc1 = loctable[i-1]

    return interpList(time, loc1, loc2)


class PicDocument(WayPoint):

    @property
    def img(self): return self.__img

    def __init__(self, path, loctable=None):
        img = Image.open(path)
        exif = ExifParser.parse(img)

        # exif info
        localtime = exif.get('time')
        time = None
        ele = None
        lat = exif.get('lat')
        lon = exif.get('lon')

        # 2nd chane to get lat/lon
        if lat is None or lon is None:
            if loctable and localtime:
                time, lat, lon, ele = lookupLoc(loctable, localtime, islocal=True)

        if lat is None or lon is None:
            raise ValueError("No Location Info")

        # set properties
        super().__init__(lat, lon)

        self.time = localToUtcTime(localtime, lat, lon) if localtime else \
                    time # maybe None

        self.ele = exif.get('alt') if exif.get('alt') else \
                   ele if ele else \
                   0.0

        self.name = exif.get('desc', "")
        self.sym = sym.toSymbol(self.name)
        self.__img = correctOrien(img, exif.get('orien', 1))  #assert orientation exist

