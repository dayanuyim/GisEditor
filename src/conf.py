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

def __readUserMaps(conf):
    maps = OrderedDict()

    if conf.has_section('maps'):
        for id, line in conf['maps'].items():
            try:
                maps[id] = __parseUserMapLine(line)
            except Exception as ex:
                logging.warning("parsing user maps for line '%s' error: %s" % (line, str(ex)))
    return maps

__trk_colors = ('White', 'Cyan', 'Magenta', 'Blue', 'Yellow', 'Green', 'Red',
                'DarkGray', 'LightGray', 'DarkCyan', 'DarkMagenta', 'DarkBlue', 'DarkGreen', 'DarkRed', 'Black')

def __readTrkColors(conf):
    if not conf.has_section('trk_colors'):
        return __trk_colors
    else:
        #return conf['trk_colors'].values()
        return [v for k, v in conf['trk_colors'].items()]


def abspath(path, related_home):
    return path if os.path.isabs(path) else os.path.join(related_home, path)


# buitin conf ###########################################
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
__app_conf = __readConf(__APP_CONF)

MAPCACHE_DIR    = abspath(__app_conf.get('settings', 'mapcache_dir', fallback='mapcache'), __HOME_DIR)
GPSBABEL_EXE = abspath(__app_conf.get('settings', 'gpsbabel_exe'), __HOME_DIR)  #no fallback

IMG_FONT_SIZE = __app_conf.getint('settings', 'img_font_size', fallback=18)
#global use font (Note: the operation is time wasting)
IMG_FONT = ImageFont.truetype(__app_conf.get('settings', 'img_font'), IMG_FONT_SIZE)  #no fallback

ICON_SIZE = __app_conf.getint('settings', 'icon_size', fallback=32)
DEF_SYMBOL = _tosymkey(__app_conf.get('settings', 'def_symbol', fallback='Waypoint'))

DB_SCHEMA = __app_conf.get('settings', 'db_schema', fallback='tms') #valid value is 'tms' or 'zyx'
TZ = timedelta(hours=__app_conf.getfloat('settings', 'tz', fallback=8.0))  #todo: get the info from system of geo location

TRK_COLORS = __readTrkColors(__app_conf)

def writeAppConf():
    '''
    f.write("mapcache_dir=%s\n" % (__config['mapcache_dir'],))
    f.write("gpsbabel_exe=%s\n" % (__config['gpsbabel_exe'],))
    #f.write("img_font=%s\n" % (IMG_FONT.getname(),))
    f.write("img_font=%s\n" % (__config['img_font'],))  #workaround to get font name
    f.write("img_font_size=%d\n" % (IMG_FONT_SIZE,))
    f.write("tz=%f\n" % (TZ.total_seconds()/3600,))
    f.write("icon_size=%d\n" % (ICON_SIZE,))
    f.write("def_symbol=%s\n" % (DEF_SYMBOL,))
    f.write("db_schema=%s\n" % (DB_SCHEMA,))
    '''

    __app_conf['trk_colors'] = OrderedDict()
    for i in range(len(TRK_COLORS)):
        __app_conf['trk_colors']['trk_colors.' + str(i)] = TRK_COLORS[i]

    __writeConf(__app_conf, __APP_CONF)

# User conf ###########################################
__user_conf = __readConf(__USER_CONF)

MIN_SUPP_LEVEL = __user_conf.getint('settings', 'min_supp_level', fallback=7)
MAX_SUPP_LEVEL = __user_conf.getint('settings', 'max_supp_level', fallback=18)

SPLIT_TIME_GAP = timedelta(hours=__user_conf.getfloat('settings', 'split_time_gap_hr', fallback=5.0))
SPLIT_DIST_GAP = __user_conf.getfloat('settings', 'split_dist_gap_km', fallback=100.0)

SELECT_AREA_X = __user_conf.getfloat('image', 'select_area_x', fallback=7.0)
SELECT_AREA_Y = __user_conf.getfloat('image', 'select_area_y', fallback=5.0)
SELECT_AREA_ALIGN = __user_conf.getboolean('image', 'select_area_align', fallback=True)
SELECT_AREA_FIXED = __user_conf.getboolean('image', 'select_area_fixed', fallback=True)
SELECT_AREA_LEVEL = __user_conf.getint('image', 'select_area_level', fallback=16)

USER_MAPS = __readUserMaps(__user_conf)

def writeUserConf():
    #settings
    __user_conf["settings"] = OrderedDict()
    __user_conf["settings"]["min_supp_level"] = "%d" % (MIN_SUPP_LEVEL,)
    __user_conf["settings"]["max_supp_level"] = "%d" % (MAX_SUPP_LEVEL,)
    __user_conf["settings"]["split_time_gap"] = "%f" % (SPLIT_TIME_GAP.total_seconds()/3600,)
    __user_conf["settings"]["split_dist_gap"] = "%f" % (SPLIT_DIST_GAP,)

    #image
    __user_conf["image"] = OrderedDict()
    __user_conf["image"]["select_area_x"] = "%f" % (SELECT_AREA_X,)
    __user_conf["image"]["select_area_y"] = "%f" % (SELECT_AREA_Y,)
    __user_conf["image"]["select_area_align"] = "%s" % ('True' if SELECT_AREA_ALIGN else 'False',)
    __user_conf["image"]["select_area_fixed"] = "%s" % ('True' if SELECT_AREA_FIXED else 'False',)
    __user_conf["image"]["select_area_level"] = "%d" % (SELECT_AREA_LEVEL,)

    #maps
    __user_conf['maps'] = OrderedDict()
    for id, item in USER_MAPS.items():
        __user_conf['maps'][id] = __genUserMapLine(item)

    #write
    __writeConf(__user_conf, __USER_CONF)



# gpsbabel supported file extention/format mappings #########################
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
    writeAppConf()

