#!/usr/bin/env python3

import os
from os import path
from PIL import ImageFont, Image
from sym import SymbolRules
from datetime import timedelta
from coord import CoordinateSystem

#constance
def __readConfig(conf_path):
    conf = {}
    with open(conf_path) as conf_file:
        for line in conf_file:
            k, v = line.rstrip().split('=', 1)
            conf[k] = v
    return conf
__config = __readConfig('./giseditor.conf')
CACHE_DIR = __config['cache_dir']
GPSBABEL_DIR = __config['gpsbabel_dir']

def _tosymkey(sym):
    return sym.title()

IMG_FONT = ImageFont.truetype("ARIALUNI.TTF", 18) #global use font (Note: the operation is time wasting)
TZ = timedelta(hours=8)
ICON_DIR = './icon'
ICON_SIZE = 32
DEF_SYMBOL = _tosymkey("Waypoint")
DEF_SYMS_CONF = "./def_sym.conf"

#global variables
Sym_rules = SymbolRules('./sym_rule.conf')

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

