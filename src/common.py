#!/usr/bin/env python3
'''
business-logic tools
'''

from util import GeoPoint, getLocTimezone
import conf

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

