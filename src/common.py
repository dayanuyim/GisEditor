#!/usr/bin/env python3
'''
business-logic tools
'''

import re
from src.util import GeoPoint
from src.util import getLocTimezone

def fmtPtPosText(pt, fmt='(%.3f, %.3f)'):
    text = fmt % (pt.twd67_x/1000, pt.twd67_y/1000)
    return text

def fmtPtEleText(pt, fmt="%.1f m"):
    if pt is not None and pt.ele is not None:
        return fmt % pt.ele
    return "N/A"

def fmtPtTimezone(pt):
    return getLocTimezone(lat=pt.lat, lon=pt.lon)

def fmtPtLocaltime(pt, tz=None):
    if tz is None:
        tz = getLocTimezone(lat=pt.lat, lon=pt.lon)
    if pt is not None and pt.time is not None:
        #assume time is localized by pytz.utc
        return pt.time.astimezone(tz)
    return None

def fmtPtTimeText(pt, tz=None):
    time = fmtPtLocaltime(pt, tz)

    return "N/A" if time is None else \
            time.strftime("%Y-%m-%d %H:%M:%S")


# @ref_geo for 6-code coord
def textToGeo(txt, coord_sys, ref_geo=None):
    valid_coords = ['TWD67TM2', 'TWD97TM2', 'TWD97LatLon']
    if coord_sys not in valid_coords:
        raise ValueError('the valid coord_sys should in %s' % valid_coords)

    def sixCoord(val, flag):
        if ref_geo is None:
            raise ValueError('ref-geo is necessary to infer for six-code coord')

        ref = ref_geo.twd67_x if coord_sys == 'TWD67TM2' and flag == 'x' else \
              ref_geo.twd67_y if coord_sys == 'TWD67TM2' and flag == 'y' else \
              ref_geo.twd97_x if coord_sys == 'TWD97TM2' and flag == 'x' else \
              ref_geo.twd97_y if coord_sys == 'TWD97TM2' and flag == 'y' else \
              None

        return max(0, round(ref - val, -5)) + val  # get the most closed hundred-KM, then plus @val

    #if val_txt is :
    #   float: float with unit 'kilimeter'
    # 3-digit: int with unit 'hundred-meter', need to prefix
    #   digit: int with unit 'meter'
    def __toTM2(val_txt, flag):
        return int(float(val_txt)*1000) if not val_txt.isdigit() else \
               sixCoord(int(val_txt)*100, flag) if len(val_txt) == 3 else \
               int(val_txt)

    def toTM2x(val_txt):
        return __toTM2(val_txt, 'x')

    def toTM2y(val_txt):
        return __toTM2(val_txt, 'y')

    def toDegree(val_txt):
        return float(val_txt)

    pos = txt.strip()
    if len(pos) == 6 and pos.isdigit(): # six-digit-coord, without split
        n1, n2 = pos[0:3], pos[3:6]
    else:
        n1, n2 = filter(None, re.split('[^\d\.]', pos)) #split by not 'digit' or '.'. Removing empty string.
        n1, n2 = n1.strip(), n2.strip()

    #make geo according to the coordinate
    if coord_sys == 'TWD67TM2':
        return GeoPoint(twd67_x=toTM2x(n1), twd67_y=toTM2y(n2))

    if coord_sys == 'TWD97TM2':
        return GeoPoint(twd97_x=toTM2x(n1), twd97_y=toTM2y(n2))

    elif coord_sys == 'TWD97LatLon':
        return GeoPoint(lat=toDegree(n1), lon=toDegree(n2))

    raise ValueError("Code flow error to set location") #should not happen

