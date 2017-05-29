#!/usr/bin/env python3

import os
import logging
import codecs
import platform
from os import path
from PIL import ImageFont, Image
from datetime import timedelta
from src.coord import CoordinateSystem
from configparser import ConfigParser
from collections import OrderedDict
from matplotlib import font_manager

#default raw data
import src.raw as raw

#constance util
def _tosymkey(sym):
    return sym.title()

def __readConf(fpath):
    parser = ConfigParser()
    parser.optionxform = str #case sensitive
    if os.path.exists(fpath):
        parser.read(fpath, encoding='utf-8')
    return parser

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

def __readTrkColors(conf):
    if not conf.has_section('trk_colors'):
        return raw.trk_colors
    else:
        #return conf['trk_colors'].values()
        return [v for k, v in conf['trk_colors'].items()]

def __readAppSyms(conf):
    if not conf.has_section('app_syms'):
        return [_tosymkey(sym) for sym in raw.app_syms]
    else:
        return [_tosymkey(v) for k, v in conf['app_syms'].items()]

def __defaultGpsbabelExe():
    system = platform.system()
    if system == "Linux":
        return "/usr/bin/gpsbabel"
    if system == "Windows":
        if os.path.exists("C:\\Program Files (x86)"):
            return "C:\\Program Files (x86)\\GPSBabel\\gpsbabel.exe"
        else:
            return "C:\\Program Files\\GPSBabel\\gpsbabel.exe"
    return "gpsbabel"

def __defaultImgFont():
    preferreds = ("msjh.ttc",     #winxp
            "arialuni.ttf",       #win7
            "ukai.ttc",           #ubuntu
            "arial unicode.ttf")  #mac

    def is_preferred(name):
        name = os.path.basename(name).lower()
        return name in preferreds

    # NOTICE! need patch font_manager.py to let ttf support ttc format
    fonts = font_manager.findSystemFonts(fontpaths=None, fontext='ttf')
    #for font in fonts:
        #print(font)
    pref_fonts = [ font for font in fonts if is_preferred(font)]
    font = pref_fonts[0] if pref_fonts else fonts[0]

    logging.info("Default Image Font: %s" % font)
    return font

def abspath(path, related_home):
    return path if os.path.isabs(path) else os.path.join(related_home, path)

def preferOrigIfEql(path, orig_path, related_home):
    p1 = path if os.path.isabs(path) else os.path.join(related_home, path)
    p2 = orig_path if os.path.isabs(orig_path) else os.path.join(related_home, orig_path)
    if p1 == p2:
        return orig_path
    return path

# buitin conf ###########################################
__SRC_DIR = os.path.dirname(os.path.abspath(__file__))
__HOME_DIR = os.path.abspath(os.path.join(__SRC_DIR, ".."))
__CONF_DIR = os.path.join(__HOME_DIR, 'conf')
__DATA_DIR = os.path.join(__HOME_DIR, 'data')
ICON_DIR = os.path.join(__HOME_DIR, 'icon')

__APP_CONF = os.path.join(__CONF_DIR, 'giseditor.conf')
__USER_CONF = os.path.join(__CONF_DIR, 'giseditor.user.conf')

SYM_RULE_CONF = os.path.join(__CONF_DIR, 'sym_rule.conf')
EXE_ICON = os.path.join(__DATA_DIR, 'giseditor.ico')
DEL_ICON = os.path.join(__DATA_DIR, 'delete_icon.png')

GPSBABEL_EXT_FMT = raw.gpsbabel_ext_fmt

MAP_UPDATE_PERIOD = timedelta(seconds=1)

DEF_COLOR = "DarkMagenta"

# App conf ###########################################
__app_conf = __readConf(__APP_CONF)

#original conf
__mapcache_dir  = __app_conf.get('settings', 'mapcache_dir', fallback='mapcache')
__gpsbabel_exe  = __app_conf.get('settings', 'gpsbabel_exe', fallback=__defaultGpsbabelExe())
__db_schema     = __app_conf.get('settings', 'db_schema', fallback='tms')
__tz            = __app_conf.getfloat('settings', 'tz', fallback=8.0)

#publish conf
MAPCACHE_DIR  = abspath(__mapcache_dir, __HOME_DIR)
GPSBABEL_EXE  = abspath(__gpsbabel_exe, __HOME_DIR)
DB_SCHEMA     = __db_schema            #valid value is 'tms' or 'zyx'
TZ            = timedelta(hours=__tz)  #todo: get the info from system of geo location
TRK_COLORS    = __readTrkColors(__app_conf)
APP_SYMS      = __readAppSyms(__app_conf)

def writeAppConf():
    __app_conf['settings'] = OrderedDict()
    __app_conf['settings']['mapcache_dir'] = preferOrigIfEql(MAPCACHE_DIR, __mapcache_dir, __HOME_DIR)
    __app_conf['settings']['gpsbabel_exe'] = preferOrigIfEql(GPSBABEL_EXE, __gpsbabel_exe, __HOME_DIR)
    __app_conf['settings']['db_schema'] = DB_SCHEMA
    __app_conf['settings']['tz'] = str(TZ.total_seconds()/3600)

    __app_conf['trk_colors'] = OrderedDict()
    for i in range(len(TRK_COLORS)):
        __app_conf['trk_colors']['trk_colors.' + str(i)] = TRK_COLORS[i]

    __app_conf['app_syms'] = OrderedDict()
    for i in range(len(APP_SYMS)):
        __app_conf['app_syms']['app_syms.' + str(i)] = APP_SYMS[i]

    __writeConf(__app_conf, __APP_CONF)

if not os.path.exists(__APP_CONF):
    writeAppConf()

# User conf ###########################################
__user_conf = __readConf(__USER_CONF)

IMG_FONT_SIZE = __user_conf.getint('settings', 'img_font_size', fallback=18)

__img_font      = __user_conf.get('settings', 'img_font', fallback=__defaultImgFont())
IMG_FONT      = ImageFont.truetype(__img_font, IMG_FONT_SIZE)  #global used font (Note: the operation is time wasting)

MIN_SUPP_LEVEL = __user_conf.getint('settings', 'min_supp_level', fallback=7)
MAX_SUPP_LEVEL = __user_conf.getint('settings', 'max_supp_level', fallback=18)

SPLIT_TIME_GAP = timedelta(hours=__user_conf.getfloat('settings', 'split_time_gap_hr', fallback=5.0))
SPLIT_DIST_GAP = __user_conf.getfloat('settings', 'split_dist_gap_km', fallback=100.0)

DEF_SYMBOL    = _tosymkey(__user_conf.get('settings', 'def_symbol', fallback='Waypoint'))
ICON_SIZE     = __user_conf.getint('settings', 'icon_size', fallback=32)

TRK_WIDTH = __user_conf.getint('settings', 'trk_width', fallback=3)
TRK_SET_FOCUS = __user_conf.getboolean('settings', 'trk_set_focus', fallback=True)
WPT_SET_FOCUS = __user_conf.getboolean('settings', 'wpt_set_focus', fallback=True)

SELECT_AREA_X = __user_conf.getfloat('image', 'select_area_x', fallback=7.0)
SELECT_AREA_Y = __user_conf.getfloat('image', 'select_area_y', fallback=5.0)
SELECT_AREA_ALIGN = __user_conf.getboolean('image', 'select_area_align', fallback=True)
SELECT_AREA_FIXED = __user_conf.getboolean('image', 'select_area_fixed', fallback=True)
SELECT_AREA_LEVEL = __user_conf.getint('image', 'select_area_level', fallback=16)

USER_MAPS = __readUserMaps(__user_conf)

def writeUserConf():
    #settings
    __user_conf["settings"] = OrderedDict()
    __user_conf['settings']['img_font_size']  = str(IMG_FONT_SIZE)
    __user_conf['settings']['img_font']       = __img_font  #the same as origin
    __user_conf["settings"]["min_supp_level"] = "%d" % (MIN_SUPP_LEVEL,)
    __user_conf["settings"]["max_supp_level"] = "%d" % (MAX_SUPP_LEVEL,)
    __user_conf["settings"]["split_time_gap"] = "%f" % (SPLIT_TIME_GAP.total_seconds()/3600,)
    __user_conf["settings"]["split_dist_gap"] = "%f" % (SPLIT_DIST_GAP,)
    __user_conf['settings']['def_symbol']     = DEF_SYMBOL
    __user_conf['settings']['icon_size']      = str(ICON_SIZE)
    __user_conf["settings"]["trk_width"]      = "%d" % (TRK_WIDTH,)
    __user_conf["settings"]["trk_set_focus"]  = "%s" % ('True' if TRK_SET_FOCUS else 'False',)
    __user_conf["settings"]["wpt_set_focus"]  = "%s" % ('True' if WPT_SET_FOCUS else 'False',)

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

if not os.path.exists(__USER_CONF):
    writeUserConf()

# utils ###########################################

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

