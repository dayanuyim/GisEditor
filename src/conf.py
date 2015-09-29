#!/usr/bin/env python3

import os
import platform
from os import path
from PIL import ImageFont, Image
from sym import SymbolRules
from datetime import timedelta
from coord import CoordinateSystem

#constance util
def _tosymkey(sym):
    return sym.title()

def __readConfig(conf_path):
    conf = {}
    with open(conf_path) as conf_file:
        for line in conf_file:
            k, v = line.rstrip().split('=', 1)
            conf[k] = v
    return conf

#constance
OS = platform.system()
GISEDITOR_CONF = './giseditor.conf'

#constance from conf
__config = __readConfig(GISEDITOR_CONF)
DEF_SYMS_CONF = __config['def_syms_conf']
SYM_RULE_CONF = __config['sym_rule_conf']
CACHE_DIR = __config['cache_dir']
GPSBABEL_EXE = __config['gpsbabel_exe']
IMG_FONT_SIZE = int(__config['img_font_size'])
IMG_FONT = ImageFont.truetype(__config['img_font'], IMG_FONT_SIZE) #global use font (Note: the operation is time wasting)
TZ = timedelta(hours=float(__config['tz']))
ICON_DIR = __config['icon_dir']
ICON_SIZE = int(__config['icon_size'])
DEF_SYMBOL = _tosymkey(__config['def_symbol'])
MAX_SUPP_LEVEL = int(__config['max_supp_level'])
MIN_SUPP_LEVEL = int(__config['min_supp_level'])
SPLIT_TIME_GAP = timedelta(hours=float(__config['split_time_gap']))
SPLIT_DIST_GAP = float(__config['split_dist_gap']) #unit:km
SELECT_AREA_W = float(__config['select_area_w'])
SELECT_AREA_H = float(__config['select_area_h'])
SELECT_AREA_ALIGN = __config['select_area_align'] == 'y'

#global variables
Sym_rules = SymbolRules(SYM_RULE_CONF)

def getSymbol(name):
    rule = Sym_rules.getMatchRule(name)
    sym = rule.symbol if rule is not None else DEF_SYMBOL
    return sym

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

__sym_paths = None  #sym->icon_path
def getIconPath():
    global __sym_paths
    if __sym_paths is None:
        __sym_paths = {}
        for f in os.listdir(ICON_DIR):
            p = path.join(ICON_DIR, f)
            if path.isfile(p):
                name, ext = path.splitext(f)
                sym = _tosymkey(name)
                __sym_paths[sym] = p
    return __sym_paths

def getIcon(sym):
    sym = _tosymkey(sym)
    icon = __getIcon(sym)
    if icon is None and sym != DEF_SYMBOL:
        icon = __getIcon(DEF_SYMBOL)
    return icon

__icons = {}   #sym->icon image
def __getIcon(sym):
    icon = __icons.get(sym)
    if icon is None:
        icon = __loadIcon(sym, ICON_SIZE)
        if icon is not None:
            __icons[sym] = icon  #cache
    return icon

def __loadIcon(sym, sz):
    path =  getIconPath().get(sym)
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

