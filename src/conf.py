#!/usr/bin/env python3

import os
import logging
import codecs
from os import path
from PIL import ImageFont, Image
from datetime import timedelta
from coord import CoordinateSystem
from configparser import ConfigParser
from collections import OrderedDict

#constance util
def _tosymkey(sym):
    return sym.title()

def __readConfig(conf_path):
    conf = {}
    with open(conf_path) as conf_file:
        for line in conf_file:
            line = line.rstrip()

            #omit comments and space line
            if line.startswith('#') or line.isspace():
                continue

            #filter out invalid format
            tokens = line.split('=', 1)
            if len(tokens) != 2:
                logging.warning('invalid format for conf line: %s' % (line,))
                continue

            k, v = tokens
            conf[k] = v
    return conf

def __readConf(fpath):
    cp = ConfigParser()
    cp.optionxform = str #case sensitive
    cp.read(fpath, encoding='utf-8')
    return cp

def __writeConf(conf, fpath):
    with codecs.open(fpath, 'w', encoding='utf-8') as f:
        conf.write(f, space_around_delimiters=False)

def __parseUserMapLine(line):
    tokens = line.split(',')
    en = tokens[0] == "1"
    alpha = float(tokens[1])
    return en, alpha

def __genUserMapLine(item):
    en, alpha = item
    return "%d,%.2f" % (1 if en else 0, alpha)

def __readUserMaps(user_conf):
    maps = OrderedDict()

    if user_conf.has_section('maps'):
        for id, line in user_conf['maps'].items():
            maps[id] = __parseUserMapLine(line)
    return maps


#constance
__SRC_DIR = os.path.dirname(os.path.abspath(__file__))
__HOME_DIR = os.path.abspath(os.path.join(__SRC_DIR, ".."))
__CONF_DIR = os.path.join(__HOME_DIR, 'conf')
__DATA_DIR = os.path.join(__HOME_DIR, 'data')
__ICON_DIR = os.path.join(__HOME_DIR, 'icon')

__APP_CONF = os.path.join(__CONF_DIR, 'giseditor.conf')
__USER_CONF = os.path.join(__CONF_DIR, 'giseditor.user.conf')

DEF_SYMS_CONF = os.path.join(__CONF_DIR, 'def_syms.conf')
SYM_RULE_CONF = os.path.join(__CONF_DIR, 'sym_rule.conf')
EXE_ICON = os.path.join(__DATA_DIR, 'giseditor.ico')

# App conf ###########################################
__config = __readConfig(__APP_CONF)

__cache_dir = __config['cache_dir']
CACHE_DIR = __cache_dir if os.path.isabs(__cache_dir ) else os.path.join(__HOME_DIR, __cache_dir)

__gpsbabel_exe = __config['gpsbabel_exe']
GPSBABEL_EXE = __gpsbabel_exe if os.path.isabs(__gpsbabel_exe) else os.path.join(__HOME_DIR, __gpsbabel_exe)

IMG_FONT_SIZE = int(__config['img_font_size'])
IMG_FONT = ImageFont.truetype(__config['img_font'], IMG_FONT_SIZE) #global use font (Note: the operation is time wasting)
TZ = timedelta(hours=float(__config['tz']))
ICON_SIZE = int(__config['icon_size'])
DEF_SYMBOL = _tosymkey(__config['def_symbol'])
MAX_SUPP_LEVEL = int(__config['max_supp_level'])
MIN_SUPP_LEVEL = int(__config['min_supp_level'])
DB_SCHEMA = __config['db_schema']

SPLIT_TIME_GAP = timedelta(hours=float(__config['split_time_gap']))
SPLIT_DIST_GAP = float(__config['split_dist_gap']) #unit:km
SELECT_AREA_X = float(__config['select_area_x'])
SELECT_AREA_Y = float(__config['select_area_y'])
SELECT_AREA_ALIGN = __config['select_area_align'] == 'y'
SELECT_AREA_FIXED = __config['select_area_fixed'] == 'y'
SELECT_AREA_LEVEL = int(__config['select_area_level'])

# User conf ###########################################
__user_conf = __readConf(__USER_CONF)

USER_MAPS = __readUserMaps(__user_conf)


# Save ###########################################
def writeUserConf():
    maps = OrderedDict()
    for id, item in USER_MAPS.items():
        maps[id] = __genUserMapLine(item)
    __user_conf['maps'] = maps

    __writeConf(__user_conf, __USER_CONF)

def writeAppConf():
    __writeConf(app_conf, __USER_CONF)


#save conf
def save(path=__APP_CONF):
    with open(path, 'w') as f:
        f.write("cache_dir=%s\n" % (__config['cache_dir'],))
        f.write("gpsbabel_exe=%s\n" % (__config['gpsbabel_exe'],))
        #f.write("img_font=%s\n" % (IMG_FONT.getname(),))
        f.write("img_font=%s\n" % (__config['img_font'],))  #workaround to get font name
        f.write("img_font_size=%d\n" % (IMG_FONT_SIZE,))
        f.write("tz=%f\n" % (TZ.total_seconds()/3600,))
        f.write("icon_size=%d\n" % (ICON_SIZE,))
        f.write("def_symbol=%s\n" % (DEF_SYMBOL,))
        f.write("max_supp_level=%d\n" % (MAX_SUPP_LEVEL,))
        f.write("min_supp_level=%d\n" % (MIN_SUPP_LEVEL,))
        f.write("db_schema=%s\n" % (DB_SCHEMA,))
        f.write("split_time_gap=%f\n" % (SPLIT_TIME_GAP.total_seconds()/3600,))
        f.write("split_dist_gap=%f\n" % (SPLIT_DIST_GAP,))
        f.write("select_area_x=%f\n" % (SELECT_AREA_X,))
        f.write("select_area_y=%f\n" % (SELECT_AREA_Y,))
        f.write("select_area_align=%s\n" % ('y' if SELECT_AREA_ALIGN else 'n',))
        f.write("select_area_fixed=%s\n" % ('y' if SELECT_AREA_FIXED else 'n',))
        f.write("select_area_level=%d\n" % (SELECT_AREA_LEVEL,))

#ext -> fmorat supported by gpsbabel
gpsbabel_ext_fmt = {
        ".gpx" : ("gpx",),        #GPX XML
        ".gdb" : ("gdb",),        #Garmin Mapsource
        ".mps" : ("mapsource",),  #Garmin Mapsource
        ".gtm" : ("gtm",),        #GPS TrackMaker
        ".trl" : ("alantrl", "gnav_trl", "dmtlog"),
        ".wpr" : ("alanwpr",),
        ".cst" : ("cst",),
        ".csv" : ("csv, v900, iblue747, iblue757",),
        ".wpt" : ("compegps, xmap, xmapwpt",),
        ".trk" : ("compegps", "gopal", "igo8"),
        ".rte" : ("compegps", "nmn4"),
        ".an1" : ("an1",),
        ".gpl" : ("gpl",),
        ".txt" : ("xmap2006", "garmin_txt", "pocketfms_wp", "text"),
        ".dat" : ("destinator_itn, destinator_trl, destinator_poi",),
        ".jpg" : ("exif",),      #be careful this! 
        ".ert" : ("enigma",),
        ".fit" : ("garmin_fit",),
        ".g7t" : ("g7towin",),
        ".pcx" : ("pcx",),
        ".poi" : ("garmin_goi",),
        ".gpi" : ("garmin_gpi",),
        ".tcx" : ("gtrnctr",),
        ".xml" : ("gtrnctr", "pocketfms_fp"),
        ".loc" : ("geo",),
        ".ovl" : ("ggv_ovl",),
        ".log" : ("ggv_log",),
        ".gns" : ("geonet",),
        ".kml" : ("kml",),
        ".arc" : ("arc",),
        ".wpo" : ("holux",),
        ".vpl" : ("vpl",),
        ".html": ("html",),
        ".ht"  : ("humminbird_ht",),
        ".hwr" : ("humminbird",),
        ".upoi": ("igo2008_poi",),
        ".tk"  : ("kompass_tk",),
        ".wp"  : ("kompass_wp",),
        ".ikt" : ("ik3d",),
        ".tef" : ("tef",),
        ".tr7" : ("mapasia_tr7",),
        ".mmo" : ("mmo",),
        ".bcr" : ("bcr",),
        ".mtk" : ("mtk",),
        ".tpg" : ("tpg",),
        ".tpo" : ("tpo2", "tpo3"),
        ".sbp" : ("sbp",),
        ".sbn" : ("sbn",),
        ".twl" : ("naviguide",),
        ".bin" : ("navitel_trk",),
        ".dna" : ("dna",),
        ".lmx" : ("lmx",),
        ".osm" : ("ozi",),
        ".rwf" : ("raymarine",),
        ".srt" : ("subrip",),        #SubRip subtitles for video mapping
        ".sdf" : ("stmsdf",),
        ".xol" : ("xol",),
        ".itn" : ("tomtom_itn", "tomtom_itn_places"),
        ".asc" : ("tomtom_asc",),
        ".ov2" : ("tomtom",),
        ".gpb" : ("vidaone",),
        ".vtt" : ("vitovtt",),
        ".wbt" : ("wbt",),
    }

__def_syms = None
def getDefSymList():
    global __def_syms
    if __def_syms is None:
        __def_syms = []
        with open(DEF_SYMS_CONF) as def_sym:
            for line in def_sym:
                if not line.startswith('#'):
                    sym = _tosymkey(line.rstrip())
                    __def_syms.append(sym)
    return __def_syms


def __getSymIcons():
    sym_icons = {}
    try:
        for f in os.listdir(__ICON_DIR):
            p = path.join(__ICON_DIR, f)
            if path.isfile(p):
                name, ext = path.splitext(f)
                sym = _tosymkey(name)
                sym_icons[sym] = (p, None)
    except Exception as ex:
        logging.error('read icons error: ' + str(ex))
    return sym_icons

#sym->icon_path, icon_image
__sym_icons = __getSymIcons()

def getTotalSymbols():
    return __sym_icons.keys()

def getIcon(sym):
    sym = _tosymkey(sym)
    icon = __getIcon(sym)
    if not icon and sym != DEF_SYMBOL:
        return __getIcon(DEF_SYMBOL) #return default
    return icon

def __getIcon(sym):
    icon = __sym_icons.get(sym)
    if not icon:
        return None
    path, img = icon
    if img is None:
        img = __readIcon(path, ICON_SIZE)
        if img:
            __sym_icons[sym] = (path, img)
    return img

def __readIcon(path, sz):
    if path is None:
        return None
    icon = Image.open(path)
    icon = icon.resize((sz, sz))
    return icon

def _getWptPos(wpt):
    x_tm2_97, y_tm2_97 = CoordinateSystem.TWD97_LatLonToTWD97_TM2(wpt.lat, wpt.lon)
    x_tm2_67, y_tm2_67 = CoordinateSystem.TWD97_TM2ToTWD67_TM2(x_tm2_97, y_tm2_97)
    return (x_tm2_67, y_tm2_67)

def getPtPosText(wpt, fmt='(%.3f, %.3f)'):
    x, y = _getWptPos(wpt)
    text = fmt % (x/1000, y/1000)
    return text

def getPtEleText(wpt):
    if wpt is not None and wpt.ele is not None:
        return "%.1f m" % (wpt.ele) 
    return "N/A"

def getPtTimeText(wpt):
    if wpt is not None and wpt.time is not None:
        time = wpt.time + TZ
        return  time.strftime("%Y-%m-%d %H:%M:%S")
    return "N/A"


if __name__ == "__main__":

    for k, v in __user_conf['maps'].items():
        print(k + '=' + v)

