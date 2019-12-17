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
from raw import *
from coord import TileSystem, CoordinateSystem

# Workaround before python3.8 to provide condition assignment
class DataHolder:
    def __init__(self, value=None):
        self.value = value

    def set(self, value):
        self.value = value
        return value

    def get(self):
        return self.value


def isValidFloat(txt):
    try:
        v = float(txt)
        return True
    except:
        return False

############################################################################
# List Utils
############################################################################

def listdiff(list1, list2):
    list2 = set(list2)
    return [e for e in list1 if e not in list2]

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

def interp(x, x1, x2, y1, y2):
    return y1 + (x-x1) / (x2-x1) * (y2-y1)

def interpList(x, list1, list2, idx=0):
    lst = []
    for i in range(len(list1)):
        v = x if i == idx else \
            interp(x, list1[idx], list2[idx], list1[i], list2[i])
        lst.append(v)
    return lst

def getLocTimezone(lat, lon):
    tz_loc = TimezoneFinder().timezone_at(lat=lat, lng=lon)  #ex: Asia/Taipei
    return pytz.timezone(tz_loc)

def localToUtcTime(time, lat, lon):
    tz = getLocTimezone(lat, lon)
    return tz.localize(time, is_dst=None).astimezone(pytz.utc)

def downloadAsTemp(url):
    ext = url.split('.')[-1]
    tmp_path = os.path.join(tempfile.gettempdir(),  "giseditor-%s.%s" % (str(uuid4()), ext))
    print(tmp_path)

    with urllib.request.urlopen(url, timeout=30) as response, open(tmp_path, 'wb') as tmp_file:
        tmp_file.write(response.read())

    return tmp_path

############################################################################
# PIL utils 
############################################################################
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

def correctOrien(img, orientation):
    trans_seq = [   # corresponding to the following
        None,
	[],
	[Image.FLIP_LEFT_RIGHT],
	[Image.ROTATE_180],
	[Image.FLIP_TOP_BOTTOM],
	[Image.FLIP_LEFT_RIGHT, Image.ROTATE_90],
	[Image.ROTATE_270],
	[Image.FLIP_TOP_BOTTOM, Image.ROTATE_90],
	[Image.ROTATE_90],
    ]

    import functools
    return functools.reduce(lambda img, op: img.transpose(op),
            trans_seq[orientation], img)

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

############################################################################
# Tkinter Utils
############################################################################

# Notice: 'accelerator string' may not a perfect guess, need more heuristic improvement
def __inferAccelerator(hotkey):
    return hotkey.strip('<>').replace('Control', 'Ctrl').replace('-', '+')

# Bind widget's event and menu's accelerator
def bindMenuCmdAccelerator(widget, hotkey, menu, label, command):
    widget.bind(hotkey, lambda e: command())
    menu.add_command(label=label, command=command, accelerator=__inferAccelerator(hotkey))

# @command: a function accept a boolean argument
# @return: return the check variable
def bindMenuCheckAccelerator(widget, hotkey, menu, label, command):
    var = tk.BooleanVar()

    #keep variable
    attrname = "accelerator_" + hotkey
    setattr(widget, attrname, var)

    def event_cb(e):
        var.set(not var.get()) #trigger
        command(var.get())

    def menu_cb():
        command(var.get())

    widget.bind(hotkey, event_cb)
    menu.add_checkbutton(label=label, command=menu_cb, accelerator=__inferAccelerator(hotkey),
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

def saveXml(xml_root, filepath, enc="UTF-8"):
    #no fromat
    #tree = ET.ElementTree(element=root)
    #tree.write(filepath, encoding=enc, xml_declaration=True)

    #pretty format
    txt = ET.tostring(xml_root, method='xml', encoding=enc)
    txt = xml.dom.minidom.parseString(txt).toprettyxml(encoding=enc) #the encoding is for xml-declaration
    with open(filepath, 'wb') as f:
        f.write(txt)

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


class GeoParser:
    @staticmethod
    def get(coord_sys):
        valid_coords = ['TWD67TM2', 'TWD97TM2', 'TWD97LatLon']
        if coord_sys not in valid_coords:
            raise ValueError('the valid coord_sys should in %s' % valid_coords)

        if coord_sys == 'TWD67TM2': return TWD67TM2GeoParser()
        if coord_sys == 'TWD97TM2': return TWD97TM2GeoParser()
        if coord_sys == 'TWD97LatLon': return LatLonGeoParser()
        raise ValueError("Code flow error to set location") #should not happen

    @classmethod
    def _isFloat(cls, txt):
        try:
            float(txt)
            return True
        except:
            return False

    @classmethod
    def _toNumbers(cls, txt):
        return tuple(filter(cls._isFloat, re.split('[^-\d\.]', txt)))

    def __init__(self):
        self._ref_geo = None

    def ref(self, ref_geo):
        self._ref_geo = ref_geo
        return self

    def parse(self, txt):
        pass

class LatLonGeoParser(GeoParser):
    def _digitize(self, d, m, s):
        return d + m / 60.0 + s / 3600.0;

    def _textToCoords(self, txt):
        nums = [float(n) for n in self._toNumbers(txt)]
        if len(nums) == 6:
            return [ self._digitize(*dms) for dms in (nums[0:3], nums[3:6]) ]
        else:
            return nums

    def parse(self, txt):
        x, y = self._textToCoords(txt)
        return GeoPoint(lat=x, lon=y)

class TM2GeoParser(GeoParser):
    # @val_txt: int with unit 'hundred-meter'
    def _sixCoord(self, val_txt, attr):
        if self._ref_geo is None:
            raise ValueError('ref-geo is necessary to infer for six-code coord')
        ref_val = getattr(self._ref_geo, attr)
        val = int(val_txt) * 100
        return max(0, round(ref_val - val, -5)) + val  # get the most closed hundred-KM, then plus @val

    # @val_txt
    #   float: float with unit 'kilimeter'
    #   digit: int with unit 'meter'
    def _tm2(self, val_txt):
        return int(val_txt) if val_txt.isdigit() else \
               int(float(val_txt)*1000) 

    def _textToCoords(self, txt, attrs):
        txt = txt.strip()
        if len(txt) == 6 and txt.isdigit(): # six-digit-coord, without split
            nums = (txt[0:3], txt[3:6])
            return [ self._sixCoord(n, attr) for n, attr in zip(nums, attrs) ]
        else:
            return [ self._tm2(n) for n in self._toNumbers(txt) ]
        
class TWD97TM2GeoParser(TM2GeoParser):
    def parse(self, txt):
        x, y = self._textToCoords(txt, ('twd97_x', 'twd97_y'))
        return GeoPoint(twd97_x=x, twd97_y=y)

class TWD67TM2GeoParser(TM2GeoParser):
    __taipower_pattern = re.compile('^[A-HJ-Z]\d{4}[A-H][A-E]\d{2}(\d{2})?$')

    def parse(self, txt):
        # Taipower coordintate
        if TWD67TM2GeoParser.__taipower_pattern.match(txt):
            x, y = CoordinateSystem.electricToTWD67_TM2(txt)
            return GeoPoint(twd67_x=x, twd67_y=y)

        x, y = self._textToCoords(txt, ('twd67_x', 'twd67_y'))
        return GeoPoint(twd67_x=x, twd67_y=y)

def test_subgroup():
    eql = lambda x, y: x == y
    print(subgroup([], eql) == [])
    print(subgroup(None, eql) == [])
    print(subgroup([1], eql) == [[1]])
    print(subgroup([1, 1], eql) == [[1, 1]])
    print(subgroup([1, 1, 2, 3, 4, 4], eql) == [[1, 1], [2], [3], [4, 4]])

def test_drawguard():
    img = Image.new('RGBA', (400,300), (255, 255, 255, 96))  #transparent
    with DrawGuard(img) as draw:
        print('...processing')

def test_twd97tm2_int():
    geo = GeoParser.get('TWD97TM2').parse('293648 2776379')
    assert geo.twd97_x == 293648 and geo.twd97_y == 2776379

def test_twd97tm2_float():
    geo = GeoParser.get('TWD97TM2').parse('293.648 2776.379')
    assert geo.twd97_x == 293648 and geo.twd97_y == 2776379

def test_twd97tm2_sixcoord():
    ref = GeoPoint(twd97_x=293648, twd97_y=2776379)
    geo = GeoParser.get('TWD97TM2').ref(ref).parse('111666')
    assert geo.twd97_x == 311100 and geo.twd97_y == 2766600

def test_twd97tm2_sixcoord_no_ref_error():
    geo = GeoParser.get('TWD97TM2').parse('111666')

def test_twd67tm2_int():
    geo = GeoParser.get('TWD67TM2').parse('293648 2776379')
    assert geo.twd67_x == 293648 and geo.twd67_y == 2776379

def test_twd67tm2_float():
    geo = GeoParser.get('TWD67TM2').parse('293.648 2776.379')
    assert geo.twd67_x == 293648 and geo.twd67_y == 2776379

def test_twd67tm2_sixcoord():
    ref = GeoPoint(twd67_x=293648, twd67_y=2776379)
    geo = GeoParser.get('TWD67TM2').ref(ref).parse('111666')
    assert geo.twd67_x == 311100 and geo.twd67_y == 2766600

def test_twd67tm2_sixcoord_no_ref_error():
    geo = GeoParser.get('TWD67TM2').parse('111666')

def test_twd67tm2_taipower():
    geo = GeoParser.get('TWD67TM2').parse('B8146CC5834')
    assert geo.twd67_x == 315053 and geo.twd67_y == 2773284

def test_latlon_number():
    geo = GeoParser.get('TWD67TM2').parse('24.987969, 121.334754')
    assert geo.twd67_x == 315053 and geo.twd67_y == 2773284

def test_latlon_number():
    from math import isclose
    geo = GeoParser.get('TWD97LatLon').parse('23.592444444, 120.977055556')
    assert isclose(geo.lat, 23.592444444) and isclose(geo.lon, 120.977055556)

def test_latlon_degree():
    from math import isclose
    geo = GeoParser.get('TWD97LatLon').parse('N23 35 32.8 E120 58 37.4')
    assert isclose(geo.lat, 23.592444444) and isclose(geo.lon, 120.977055556)

if __name__ == '__main__':
    test_twd97tm2_int()
    test_twd97tm2_float()
    test_twd97tm2_sixcoord()
    #test_twd97tm2_sixcoord_no_ref_error()
    test_twd67tm2_int()
    test_twd67tm2_float()
    test_twd67tm2_sixcoord()
    #test_twd67tm2_sixcoord_no_ref_error()
    test_twd67tm2_taipower()
    test_latlon_number()
    test_latlon_degree()
    pass


