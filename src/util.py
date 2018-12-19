#!/usr/bin/env python3
'''
Non business-logic utils
'''

import os
import platform
import re
import xml.dom.minidom
import logging
import tempfile
import urllib.request
import tkinter as tk
from xml.etree import ElementTree as ET
from threading import Timer
from PIL import Image, ImageDraw
from uuid import uuid4

import pytz
from timezonefinder import TimezoneFinder

#my modules
from src.raw import *
from src.coord import TileSystem, CoordinateSystem

def isValidFloat(txt):
    try:
        v = float(txt)
        return True
    except:
        return False

# classify according to @cond between two consequence elements.
def subgroup(list, cond):
    if not list:
        return []

    buckets = [ [list[0]] ]

    for elem in list[1:]:
        if cond(buckets[-1][-1], elem):
            buckets[-1].append(elem)
        else:
            buckets.append([elem])

    return buckets


def filterOutIndex(list, idxes):
    idxes = set(idxes)
    return [elem for i, elem in enumerate(list) if i not in idxes]

def swaplist(list, i1, i2):
    e1 = list[i1]
    e2 = list[i2]
    list[i1] = e2
    list[i2] = e1

def rotateLeft(list, first, last, step):
    tmp = None
    for i in range(first, last+1, step):
        if tmp is None:
            tmp = list[i]
        else:
            list[i-step] = list[i]

    list[last] = tmp

def rotateRight(list, first, last, step):
    tmp =  None
    for i in range(last, first-1, -step):
        if tmp is None:
            tmp = list[i];
        else:
            list[i+step] = list[i]

    list[first] = tmp

def getLocTimezone(lat, lon):
    tz_loc = TimezoneFinder().timezone_at(lat=lat, lng=lon)  #ex: Asia/Taipei
    return pytz.timezone(tz_loc)

def downloadAsTemp(url):
    ext = url.split('.')[-1]
    tmp_path = os.path.join(tempfile.gettempdir(),  "giseditor-%s.%s" % (str(uuid4()), ext))
    print(tmp_path)

    with urllib.request.urlopen(url, timeout=30) as response, open(tmp_path, 'wb') as tmp_file:
        tmp_file.write(response.read())

    return tmp_path

# PIL utils ===================================
class DrawGuard:
    def __init__(self, img):
        self.__img = img

    def __enter__(self):
        self.__draw = ImageDraw.Draw(self.__img)
        return self.__draw

    def __exit__(self, type, value, traceback):
        if self.__draw is not None:
            del self.__draw

'''
Draw Text with Shadow
'''
def drawTextShadow(draw, xy, text, fill, font, shadow_fill="white", shadow_size=2):
    #shadow
    px, py = xy
    for i in range(-shadow_size, shadow_size + 1):
        if i:
            draw.text((px + i, py + i), text, fill=shadow_fill, font=font);
    #text
    draw.text(xy, text, fill=fill, font=font)

'''
Draw Text with Color-filled Bounding-Box
'''
def drawTextBg(draw, xy, text, fill, font, bg_fill="white"):
    x, y = xy
    w, h = font.getsize(text)
    #bg
    draw.rectangle((x, y, x + w, y + h), fill=bg_fill)
    #text
    draw.text(xy, text, fill=fill, font=font)

# using screntone to walkaround for tranparent,
# beacuase PIL only support 0/255 alpha value on MAC, ref:
#   https://stackoverflow.com/questions/41576637/are-rgba-pngs-unsupported-in-python-3-5-pillow
def screentone(img):

    w, h = img.size

    transp = (0,) * w
    opaque = (255,) * w

    alpha = []
    for i in range(h):
        if i % 2:
            alpha.extend(opaque)
        else:
            alpha.extend(transp)

    mask = Image.frombytes('L', img.size, bytes(alpha))
    img.putalpha(mask)
    return img

# Notice: 'accelerator string' may not a perfect guess, need more heuristic improvement
def __guessAccelerator(event):
    return event.strip('<>').replace('Control', 'Ctrl').replace('-', '+')

# Bind widget's event and menu's accelerator
def bindMenuCmdAccelerator(widget, event, menu, label, command):
    widget.bind(event, lambda e: command())
    menu.add_command(label=label, command=command, accelerator=__guessAccelerator(event))

# @command: a function accept a boolean argument
# @return: return the check variable
def bindMenuCheckAccelerator(widget, event, menu, label, command):
    var = tk.BooleanVar()

    #keep variable
    attrname = "accelerator_" + event
    setattr(widget, attrname, var)

    def event_cb(e):
        var.set(not var.get()) #trigger
        command(var.get())

    def menu_cb():
        command(var.get())

    widget.bind(event, event_cb)
    menu.add_checkbutton(label=label, command=menu_cb, accelerator=__guessAccelerator(event),
            onvalue=True, offvalue=False, variable=var)

    return var

#be quiet to wait to show
def quietenTopLevel(toplevel):
    toplevel.withdraw()  #hidden
    toplevel._visible = tk.BooleanVar(value=False)

#for show
def showToplevel(toplevel):
    toplevel.update()  #update window size

    toplevel.deiconify() #show
    toplevel._visible.set(True)

    #toplevel.attributes("-topmost", 1) #topmost
    toplevel.lift()
    toplevel.focus_set()  #prevent key-press sent back to parent
    toplevel.grab_set()   #disalbe interact of parent
    toplevel.master.wait_variable(toplevel._visible)

#for hide or close
def hideToplevel(toplevel):
    toplevel.master.focus_set()
    toplevel.grab_release()

    toplevel.withdraw()
    toplevel._visible.set(False)

def imageIsTransparent(img):
    if img is None:
        raise ValueError("img is None for transparent detect")
    if img.mode == 'RGBA' and img.getextrema()[3][0] != 255:
        return True
    if img.mode == 'LA':
        return True
    if img.mode == 'P' and 'transparency' in img.info:
        return True
    return False

def saveXml(xml_root, filepath, enc="UTF-8"):
    #no fromat
    #tree = ET.ElementTree(element=root)
    #tree.write(filepath, encoding=enc, xml_declaration=True)

    #pretty format
    txt = ET.tostring(xml_root, method='xml', encoding=enc)
    txt = xml.dom.minidom.parseString(txt).toprettyxml(encoding=enc) #the encoding is for xml-declaration
    with open(filepath, 'wb') as f:
        f.write(txt)

def listdiff(list1, list2):
    list2 = set(list2)
    return [e for e in list1 if e not in list2]

def mkdirSafely(path, is_recursive=True):
    if not os.path.exists(path):
        if is_recursive:
            os.makedirs(path)
        else:
            os.mkdir(path)

'''
import Xlib.display as display
import Xlib.X as X
def autorepeat(enabled):
    if platform.system() == 'Linux':
        #mode = X.AutoRepeatModeOn if enabled else X.AutoRepeatModeOff
        #d = display.Display()    
        #d.change_keyboard_control(auto_repeat_mode=mode)
        #x = d.get_keyboard_control()    
        if enabled:
            os.system('xset r on')
        else:
            os.system('xset r off')
'''

def getPrefCornerPos(widget, pos):
    sw = widget.winfo_screenwidth()
    sh = widget.winfo_screenheight()
    ww = widget.winfo_width()
    wh = widget.winfo_height()
    if isinstance(widget, tk.Toplevel): wh += 30  #@@ height of title bar
    x, y = pos

    #print('screen:', (sw, sh), 'window:', (ww, wh), 'pos:', pos)
    if ww > (sw-x):
        if ww <= x:         #pop left
            x -= ww
        elif (sw-x) >= x:  #pop right, but adjust
            x = max(0, sw-ww)
        else:              #pop left, but adjust
            x = 0
    if wh > (sh-y):
        if wh <= y:         #pop up
            y -= wh
        elif (sh-y) >= y:  #pop down, but adjust
            y = max(0, sh-wh)
        else:              #pop up, but adjust
            y = 0
    return (x, y)

def equalsLine(coords, coords2):
    dx = coords[2] - coords[0]
    dy = coords[3] - coords[1]
    dx2 = coords2[2] - coords2[0]
    dy2 = coords2[3] - coords2[1]
    return dx == dx2 and dy == dy2


class GeoInfo:
    @classmethod
    def get(cls, coord_sys, ref_geo, level):
        if coord_sys == TWD67:
            return TWD67GeoInfo(ref_geo, level)
        elif coord_sys == TWD97:
            return TWD97GeoInfo(ref_geo, level)
        elif coord_sys == 'virtual':
            return VirtualGeoInfo(ref_geo, level)
        else:
            raise ValueError("Unknown coord system '%s'" % coord_sys)

    def __init__(self, ref_geo, level):
        raise ValueError("private ctor")

    def getNearbyGridPoint(self, pos, grid_sz=(1000,1000)):
        pass

    def toPixelLength(self, km):
        pass

    def getCoordByPixel(self, px, py):
        pass

    def getPixelByCoord(self, x, y):
        pass

class TWD67GeoInfo(GeoInfo):
    def __init__(self, ref_geo, level):
        self.__ref_geo = ref_geo
        self.__level = level

    def getNearbyGridPoint(self, pos, grid_sz=(1000,1000)):
        geo = self.__ref_geo.addPixel(pos[0], pos[1], self.__level)
        grid_x, grid_y = grid_sz

        x = round(geo.twd67_x/grid_x) * grid_x
        y = round(geo.twd67_y/grid_y) * grid_y
        grid_geo = GeoPoint(twd67_x=x, twd67_y=y)
        return grid_geo.diffPixel(self.__ref_geo, self.__level)

    def toPixelLength(self, km):
        x = self.__ref_geo.twd67_x + km*1000
        y = self.__ref_geo.twd67_y
        geo = GeoPoint(twd67_x=x, twd67_y=y)
        return geo.diffPixel(self.__ref_geo, self.__level)[0]

    def getCoordByPixel(self, px, py):
        geo = GeoPoint(px=px, py=py, level=self.__level)
        return (geo.twd67_x, geo.twd67_y)

    def getPixelByCoord(self, x, y):
        geo = GeoPoint(twd67_x=x, twd67_y=y)
        return geo.pixel(self.__level)

class TWD97GeoInfo(GeoInfo):
    def __init__(self, ref_geo, level):
        self.__ref_geo = ref_geo
        self.__level = level

    def getNearbyGridPoint(self, pos, grid_sz=(1000,1000)):
        geo = self.__ref_geo.addPixel(pos[0], pos[1], self.__level)
        grid_x, grid_y = grid_sz

        x = round(geo.twd97_x/grid_x) * grid_x
        y = round(geo.twd97_y/grid_y) * grid_y
        grid_geo = GeoPoint(twd97_x=x, twd97_y=y)
        return grid_geo.diffPixel(self.__ref_geo, self.__level)

    def toPixelLength(self, km):
        x = self.__ref_geo.twd97_x + km*1000
        y = self.__ref_geo.twd97_y
        geo = GeoPoint(twd97_x=x, twd97_y=y)
        return geo.diffPixel(self.__ref_geo, self.__level)[0]

    def getCoordByPixel(self, px, py):
        geo = GeoPoint(px=px, py=py, level=self.__level)
        return (geo.twd97_x, geo.twd97_y)

    def getPixelByCoord(self, x, y):
        geo = GeoPoint(twd97_x=x, twd97_y=y)
        return geo.pixel(self.__level)

# The special case, only support km length convertion.
class VirtualGeoInfo(GeoInfo):
    def __init__(self, ref_geo, level):
        self.__ref_geo = ref_geo
        self.__level = level

    def toPixelLength(self, km):
        x = self.__ref_geo.twd67_x + km*1000
        y = self.__ref_geo.twd67_y
        geo = GeoPoint(twd67_x=x, twd67_y=y)
        return geo.diffPixel(self.__ref_geo, self.__level)[0]


# The class represent a unique geographic point, and designed to be 'immutable'.
# 'level' is the 'granularity' needed to init px/py and access px/py.
class GeoPoint:
    MAX_LEVEL = 23

    def __init__(self, lat=None, lon=None, px=None, py=None, level=None, twd67_x=None, twd67_y=None, twd97_x=None, twd97_y=None):
        if lat is not None and lon is not None:
            self.resetPos(lat=lat, lon=lon)
        elif px is not None and py is not None and level is not None:
            self.resetPos(px=px, py=py, level=level)
        elif twd67_x is not None and twd67_y is not None:
            self.resetPos(twd67_x=twd67_x, twd67_y=twd67_y)
        elif twd97_x is not None and twd97_y is not None:
            self.resetPos(twd97_x=twd97_x, twd97_y=twd97_y)
        else:
            raise ValueError("Not propriate init")

    # Fileds init ===================
    def resetPos(self, lat=None, lon=None, px=None, py=None, level=None, twd67_x=None, twd67_y=None, twd97_x=None, twd97_y=None, geo=None):
        if geo is not None:
            self.__lat = geo.__lat
            self.__lon = geo.__lon
            self.__px = geo.__px
            self.__py = geo.__py
            self.__twd67_x = geo.__twd67_x
            self.__twd67_y = geo.__twd67_y
            self.__twd97_x = geo.__twd97_x
            self.__twd97_y = geo.__twd97_y
        else:
            self.__lat = lat
            self.__lon = lon
            self.__px = None if px is None else px << (self.MAX_LEVEL - level)  #px of max level
            self.__py = None if py is None else py << (self.MAX_LEVEL - level)  #py of max level
            self.__twd67_x = twd67_x
            self.__twd67_y = twd67_y
            self.__twd97_x = twd97_x
            self.__twd97_y = twd97_y

    # convert: All->WGS84/LatLon
    def __checkWGS84Latlon(self):
        if self.__lat is None or self.__lon is None:
            if self.__px is not None and self.__py is not None:
                self.__lat, self.__lon = TileSystem.getLatLonByPixcelXY(self.__px, self.__py, self.MAX_LEVEL)
            elif self.__twd67_x is not None and self.__twd67_y is not None:
                self.__lat, self.__lon = CoordinateSystem.TWD67_TM2ToTWD97_LatLon(self.__twd67_x, self.__twd67_y)
            elif self.__twd97_x is not None and self.__twd97_y is not None:
                self.__lat, self.__lon = CoordinateSystem.TWD97_TM2ToTWD97_LatLon(self.__twd97_x, self.__twd97_y)
            else:
                raise ValueError("Not propriate init")

    # convert TWD97/LatLon -> each =========
    def __checkPixcel(self):
        if self.__px is None or self.__py is None:
            self.__checkWGS84Latlon()
            self.__px, self.__py = TileSystem.getPixcelXYByLatLon(self.__lat, self.__lon, self.MAX_LEVEL)

    def __checkTWD67TM2(self):
        if self.__twd67_x is None or self.__twd67_y is None:
            self.__checkWGS84Latlon()
            self.__twd67_x, self.__twd67_y = CoordinateSystem.TWD97_LatLonToTWD67_TM2(self.__lat, self.__lon)

    def __checkTWD97TM2(self):
        if self.__twd97_x is None or self.__twd97_y is None:
            self.__checkWGS84Latlon()
            self.__twd97_x, self.__twd97_y = CoordinateSystem.TWD97_LatLonToTWD97_TM2(self.__lat, self.__lon)

    #accesor LatLon  ==========
    @property
    def lat(self):
        self.__checkWGS84Latlon()
        return self.__lat

    @property
    def lon(self):
        self.__checkWGS84Latlon()
        return self.__lon

    #accesor Pixel  ==========
    def px(self, level):
        self.__checkPixcel()
        return self.__px >> (self.MAX_LEVEL - level)

    def py(self, level):
        self.__checkPixcel()
        return self.__py >> (self.MAX_LEVEL - level)

    def pixel(self, level):
        return (self.px(level), self.py(level))

    #utility
    def addPixel(self, px, py, level):  # add (px, py) to get a GeoPoint
        px = self.px(level) + px
        py = self.py(level) + py
        return GeoPoint(px=px, py=py, level=level)

    def diffPixel(self, geo, level):    # minus a GeoPoint to get the diff of (px, py)
        dpx = self.px(level) - geo.px(level)
        dpy = self.py(level) - geo.py(level)
        return (dpx, dpy)

    def tile_xy(self, level):
        return TileSystem.getTileXYByPixcelXY(self.px(level), self.py(level))

    #accesor TWD67 TM2 ==========
    @property
    def twd67_x(self):
        self.__checkTWD67TM2()
        return self.__twd67_x

    @property
    def twd67_y(self):
        self.__checkTWD67TM2()
        return self.__twd67_y

    #accesor TWD97 TM2 ==========
    @property
    def twd97_x(self):
        self.__checkTWD97TM2()
        return self.__twd97_x

    @property
    def twd97_y(self):
        self.__checkTWD97TM2()
        return self.__twd97_y


__electric_pattern = re.compile('^[A-HJ-Z]\d{4}[A-H][A-E]\d{2}(\d{2})?$')

def __is_float(s):
    try:
        float(s)
        return True
    except:
        return False

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


def test_subgroup():
    eql = lambda x, y: x == y
    print(subgroup([], eql) == [])
    print(subgroup(None, eql) == [])
    print(subgroup([1], eql) == [[1]])
    print(subgroup([1, 1], eql) == [[1, 1]])
    print(subgroup([1, 1, 2, 3, 4, 4], eql) == [[1, 1], [2], [3], [4, 4]])

if __name__ == '__main__':
    #img = Image.new('RGBA', (400,300), (255, 255, 255, 96))  #transparent
    #with DrawGuard(img) as draw:
    #    print('...processing')
    test_subgroup()


