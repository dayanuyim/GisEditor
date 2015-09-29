#!/usr/bin/env python3

import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
#my modules
import conf
from tile import TileSystem
from coord import CoordinateSystem

class AreaSelector:
    @property
    def size(self):
        return self.__size

    @property
    def pos(self):
        return self.__pos

    def __init__(self, canvas, size=None, pos=None, pos_limitor=None):
        self.__canvas = canvas
        self.__button_side = 20
        self.__cv_items = []
        self.__done = tk.BooleanVar(value=False)
        self.__state = None
        self.__pos_limitor = pos_limitor

        canvas_w = canvas.winfo_width()
        canvas_h = canvas.winfo_height()

        #size
        self.__size = size if size is not None else (round(canvas_w/2), round(canvas_h/2))
        w = self.__size[0]
        h = self.__size[1]
        #pos
        self.__pos = pos if pos is not None else (round((canvas_w-w)/2), round((canvas_h-h)/2))
        if pos_limitor is not None:
            dx, dy = pos_limitor(self.pos)
            self.__pos = (self.pos[0]+dx, self.pos[1]+dy)

        #ceate items
        self.__cv_area = self.genAreaImage()
        self.__cv_items.append(self.__cv_area)

        self.__cv_ok = self.genOKButton()
        self.__cv_items.append(self.__cv_ok)

        self.__cv_cancel = self.genCancelButton()
        self.__cv_items.append(self.__cv_cancel)

        self.__cv_setting = self.genSettingButton()
        self.__cv_items.append(self.__cv_setting)

        #bind
        canvas.tag_bind(self.__cv_area, "<Button-1>", self.onSelectAreaClick)
        canvas.tag_bind(self.__cv_area, "<Button1-ButtonRelease>", self.onSelectAreaRelease)
        canvas.tag_bind(self.__cv_area, "<Button1-Motion>", self.onSelectAreaMotion)

        canvas.tag_bind(self.__cv_ok, "<Button-1>", self.onOkClick)
        canvas.tag_bind(self.__cv_cancel, "<Button-1>", self.onCancelClick)
        canvas.tag_bind(self.__cv_setting, "<Button-1>", self.onSettingClick)
        #for item in self.__cv_items:
            #canvas.tag_bind(item, "<Button-1>", self.onSelectAreaClick)
            #canvas.tag_bind(item, "<Button1-ButtonRelease>", self.onSelectAreaRelease)
            #canvas.tag_bind(item, "<Button1-Motion>", self.onSelectAreaMotion)

    #{{ interface
    def wait(self, parent):
        parent.wait_variable(self.__done)
        return self.__state

    def exit(self):
        for item in self.__cv_items:
            self.__canvas.delete(item)
        self.__done.set(True)
    #}} interface

    #{{ general operations
    def move(self, dx, dy):
        #move
        for item in self.__cv_items:
            self.__canvas.move(item, dx, dy)
        #update pos
        cpos = self.__canvas.coords(self.__cv_area)
        self.__pos = (int(cpos[0]), int(cpos[1]))

    def limitPos(self):
        if self.__pos_limitor is not None:
            dx, dy = self.__pos_limitor(self.pos)
            self.move(dx, dy)

    #}} general operations

    #{{ events
    def onOkClick(self, e):
        self.__state = 'OK'
        self.exit()

    def onCancelClick(self, e):
        self.__state = 'Cancel'
        self.exit()

    def onSettingClick(self, e):
        print('setting')

    #bind motion events
    def onSelectAreaClick(self, e):
        self.__mousepos = (e.x, e.y)

    def onSelectAreaRelease(self, e):
        self.limitPos()
        self.__mousepos = None

    def onSelectAreaMotion(self, e):
        #move
        dx = e.x - self.__mousepos[0]
        dy = e.y - self.__mousepos[1]
        self.move(dx, dy)
        self.__mousepos = (e.x, e.y)

    #}}

    #{{ canvas items
    def genAreaImage(self):
        img = Image.new('RGBA', self.__size, (255,255,0, 128))  #yellow 
        pimg = ImageTk.PhotoImage(img)
        self.__cv_area_img = pimg   #keep refg
        return self.__canvas.create_image(self.pos, image=pimg, anchor='nw')

    def genOKButton(self, order=1):
        x = self.pos[0] + self.__size[0] - self.__button_side*order #x of upper-left
        y = self.pos[1]  #y of upper-left
        return self.__canvas.create_oval(x, y, x+self.__button_side, y+self.__button_side, fill='green')

    def genCancelButton(self, order=2):
        n = int(self.__button_side/4)
        x = self.pos[0] + self.__size[0] - self.__button_side*order + 2*n  #x of center
        y = self.pos[1] + 2*n #y of center
        cross = ((0,n), (n,2*n), (2*n,n), (n,0), (2*n,-n), (n,-2*n), (0,-n), (-n,-2*n), (-2*n,-n), (-n,0), (-2*n,n), (-n, 2*n))
        cancel_cross = []
        for pt in cross:
            cancel_cross.append((pt[0]+x, pt[1]+y))
        return self.__canvas.create_polygon(cancel_cross, fill='red')

    def genSettingButton(self, order=3):
        n = int(self.__button_side/2)
        x = self.pos[0] + self.__size[0] - self.__button_side*order + n  #x of center
        y = self.pos[1] + n #y of center
        return self.__canvas.create_text(x, y, font='Arialuni 16 bold', text='S', fill='#404040')

    #}}

# The class represent a unique geographic point, and designed to be 'immutable'.
# 'level' is the 'granularity' needed to init px/py and access px/py.
class GeoPoint:
    MAX_LEVEL = 23

    def __init__(self, lat=None, lon=None, px=None, py=None, level=None, twd67_x=None, twd67_y=None, twd97_x=None, twd97_y=None):
        if lat is not None and lon is not None:
            self.__initFields(lat=lat, lon=lon)
        elif px is not None and py is not None and level is not None:
            self.__initFields(px=px, py=py, level=level)
        elif twd67_x is not None and twd67_y is not None:
            self.__initFields(twd67_x=twd67_x, twd67_y=twd67_y)
        elif twd97_x is not None and twd97_y is not None:
            self.__initFields(twd97_x=twd97_x, twd97_y=twd97_y)
        else:
            raise ValueError("Not propriate init")

    # Fileds init ===================
    def __initFields(self, lat=None, lon=None, px=None, py=None, level=None, twd67_x=None, twd67_y=None, twd97_x=None, twd97_y=None):
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

    def incPixel(self, px, py, level):
        px = self.px(level) + px
        py = self.py(level) + py
        return GeoPoint(px=px, py=py, level=level)

    def diffPixel(self, geo, level):
        dpx = self.px(level) - geo.px(level)
        dpy = self.py(level) - geo.py(level)
        return (dpx, dpy)

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


