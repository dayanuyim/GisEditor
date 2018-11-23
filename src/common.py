#!/usr/bin/env python3
'''
business-logic tools
'''

import re
from src.util import GeoPoint
from src.util import getLocTimezone
from src.coord import CoordinateSystem
import src.conf as conf

def __fmtPtPosText(pt, coord, digits):
    x, y = (pt.twd67_x/1000.0, pt.twd67_y/1000.0) if coord == 'twd67' else \
           (pt.twd97_x/1000.0, pt.twd97_y/1000.0) if coord == 'twd97' else \
           (pt.lat, pt.lon)
    text = '{0:.{2}f}, {1:.{2}f}'.format(x, y, digits)
    return text

def fmtPtPosText(pt):
    return __fmtPtPosText(pt, conf.FMT_PT_POS_COORD, conf.FMT_PT_POS_DIGITS)

def fmtPtPosCoord():
    if conf.FMT_PT_POS_COORD == 'twd67':
        return 'TWD67/TM2'
    elif conf.FMT_PT_POS_COORD == 'twd97':
        return 'TWD97/TM2'
    else:
        return 'Lat/Lon'

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

def __is_float(s):
    try:
        float(s)
        return True
    except:
        return False

__electric_pattern = re.compile('^[A-HJ-Z]\d{4}[A-H][A-E]\d{2}(\d{2})?$')

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
    def toTM2(val_txt, flag):
        return int(float(val_txt)*1000) if not val_txt.isdigit() else \
               sixCoord(int(val_txt)*100, flag) if len(val_txt) == 3 else \
               int(val_txt)

    pos = txt.strip()

    # electric coord
    if coord_sys == 'TWD67TM2' and __electric_pattern.match(pos):
        x, y = CoordinateSystem.electricToTWD67_TM2(pos)
        return GeoPoint(twd67_x=x, twd67_y=y)

    #split number
    if len(pos) == 6 and pos.isdigit(): # six-digit-coord, without split
        n1, n2 = pos[0:3], pos[3:6]
    else:
        n1, n2 = filter(__is_float, re.split('[^-\d\.]', pos)) #split by un-number chars, remove un-float literal
        n1, n2 = n1.strip(), n2.strip()

    #make geo according to the coordinate
    if coord_sys == 'TWD67TM2':
        return GeoPoint(twd67_x=toTM2(n1, 'x'), twd67_y=toTM2(n2, 'y'))

    if coord_sys == 'TWD97TM2':
        return GeoPoint(twd97_x=toTM2(n1, 'x'), twd97_y=toTM2(n2, 'y'))

    elif coord_sys == 'TWD97LatLon':
        return GeoPoint(lat=float(n1), lon=float(n2))

    raise ValueError("Code flow error to set location") #should not happen

