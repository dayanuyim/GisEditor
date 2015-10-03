#!/usr/bin/env python3

import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
#my modules
import conf
from tile import TileSystem
from coord import CoordinateSystem

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

class Dialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self._result = 'Unknown' #need subclass to set

        self.title('')
        self.resizable(0, 0)
        self.bind('<Escape>', lambda e: self.exit())
        self.protocol('WM_DELETE_WINDOW', self.exit)

        self.withdraw()  #for silent update
        self.visible = tk.BooleanVar(value=False)

        #update window size
        self.update()  

    def exit(self):
        self.master.focus_set()
        self.grab_release()
        self.destroy()
        self.visible.set(False)

    def show(self, pos=None):
        self.setPos(pos)

        #UI
        self.transient(self.master)  #remove max/min buttons
        self.focus_set()  #prevent key-press sent back to parent
        
        self.deiconify() #show
        self.visible.set(True)

        self.grab_set()   #disalbe interact of parent
        self.master.wait_variable(self.visible)

        return self._result

    def setPos(self, pos):
        pos = (0,0) if pos is None else getPrefCornerPos(self, pos)
        self.geometry('+%d+%d' % pos)

#The UI for the user to access conf
class AreaSelectorSettings(Dialog):
    def __init__(self, master):
        super().__init__(master)

        self.__size_widgets = []

        #settings by conf
        self.var_level = tk.IntVar(value=conf.SELECT_AREA_LEVEL)
        self.var_align = tk.BooleanVar(value=conf.SELECT_AREA_ALIGN)
        self.var_fixed = tk.BooleanVar(value=conf.SELECT_AREA_FIXED)
        self.var_w = tk.DoubleVar(value=conf.SELECT_AREA_X)
        self.var_h = tk.DoubleVar(value=conf.SELECT_AREA_Y)
        
        #level
        row = 0
        f = tk.Frame(self)
        f.grid(row=row, column=0, sticky='w')
        tk.Label(f, text='level:', anchor='e').pack(side='left', expand=1, fill='both')
        tk.Spinbox(f, from_=13, to=16, width=2, textvariable=self.var_level).pack(side='left', expand=1, fill='both')

        #align
        row += 1
        f = tk.Frame(self)
        f.grid(row=row, column=0, sticky='w')
        tk.Checkbutton(f, text='Align grid', variable=self.var_align)\
                .pack(side='left', expand=1, fill='both')

        #fixed
        row += 1
        def onFixedChanged():
            for w in self.__size_widgets:
                s = 'normal' if self.var_fixed.get() else 'disabled'
                w.config(state=s)
        f = tk.Frame(self)
        f.grid(row=row, column=0, sticky='w')
        tk.Checkbutton(f, text='Fixed size', variable=self.var_fixed, command=onFixedChanged)\
                .pack(side='left', expand=1, fill='both')
        
        #size
        w = tk.Entry(f, textvariable=self.var_w, width=5)
        w.pack(side='left', expand=1, fill='both')
        self.__size_widgets.append(w)

        w = tk.Label(f, text='X')
        w.pack(side='left', expand=1, fill='both')
        self.__size_widgets.append(w)

        w = tk.Entry(f, textvariable=self.var_h, width=5)
        w.pack(side='left', expand=1, fill='both')
        self.__size_widgets.append(w)

    #override
    def exit(self):
        if self.isModified():
            self.modify()
            self._result = 'OK'
        else:
            self._result = 'Cancel'
        super().exit()

    def isModified(self):
        return conf.SELECT_AREA_LEVEL != self.var_level.get() or\
               conf.SELECT_AREA_ALIGN != self.var_align.get() or\
               conf.SELECT_AREA_FIXED != self.var_fixed.get() or\
               conf.SELECT_AREA_X != self.var_w.get() or\
               conf.SELECT_AREA_Y != self.var_h.get()

    def modify(self):
        conf.SELECT_AREA_LEVEL = self.var_level.get()
        conf.SELECT_AREA_ALIGN = self.var_align.get()
        conf.SELECT_AREA_FIXED = self.var_fixed.get()
        conf.SELECT_AREA_X = self.var_w.get()
        conf.SELECT_AREA_Y = self.var_h.get()
        conf.save()

class AreaSelector:
    @property
    def size(self):
        return self.__cv_area_img.width(), self.__cv_area_img.height()

    @property
    def pos(self):
        if self.__last_pos is not None:
            return self.__last_pos
        return self.__getpos()

    def __init__(self, canvas, size=None, pos=None, pos_adjuster=None, geo_scaler=None):
        self.__canvas = canvas
        self.__button_side = 20
        self.__cv_items = []
        self.__done = tk.BooleanVar(value=False)
        self.__state = None
        self.__pos_adjuster = pos_adjuster
        self.__geo_scaler = geo_scaler
        self.__last_pos = None

        canvas_w = canvas.winfo_width()
        canvas_h = canvas.winfo_height()

        #size
        if size is None:
            size = (round(canvas_w/2), round(canvas_h/2))
        w, h = size
        #pos
        if pos is None:
            pos = (round((canvas_w-w)/2), round((canvas_h-h)/2))

        #size = 1, 1
        #pos = 0, 0

        #ceate items
        self.__cv_area = self.genArea(pos, size)
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

        #apply
        self.applySettings()

    #{{ interface
    def wait(self, parent):
        parent.wait_variable(self.__done)
        return self.__state

    def exit(self):
        #rec the last pos
        self.__last_pos = self.__getpos()
        #delete item
        for item in self.__cv_items:
            self.__canvas.delete(item)
        self.__done.set(True)
    #}} interface

    #{{ internal operations
    def __getpos(self):
        x, y = self.__canvas.coords(self.__cv_area)
        return int(x), int(y)

    def move(self, dx, dy):
        for item in self.__cv_items:
            self.__canvas.move(item, dx, dy)

    def lift(self):
        for item in self.__cv_items:
            self.__canvas.tag_raise(item)

    def resize(self, size):
        #rec needed info before deleting
        org_pos = self.pos
        org_size = self.size
        #delte old
        self.__cv_items.remove(self.__cv_area)
        self.__canvas.delete(self.__cv_area)
        #gen new
        self.__cv_area = self.genArea(org_pos, size)
        #move&lift other items
        dx = size[0] - org_size[0]
        dy = size[1] - org_size[1]
        self.move(dx, dy)
        self.lift()
        #add new
        self.__cv_items.append(self.__cv_area)

    def adjustPos(self):
        if conf.SELECT_AREA_ALIGN and self.__pos_adjuster is not None:
            dx, dy = self.__pos_adjuster(self.pos)
            self.move(dx, dy)

    def scaleGeo(self):
        if conf.SELECT_AREA_FIXED and self.__geo_scaler is not None:
            geo_xy = (conf.SELECT_AREA_X, conf.SELECT_AREA_Y)
            sz = self.__geo_scaler(self.pos, geo_xy)
            self.resize(sz)
    
    def applySettings(self):
        self.scaleGeo()
        self.adjustPos()

    #}} general operations

    #{{ events
    def onOkClick(self, e):
        self.__state = 'OK'
        self.exit()

    def onCancelClick(self, e):
        self.__state = 'Cancel'
        self.exit()

    def onSettingClick(self, e):
        settings = AreaSelectorSettings(self.__canvas)
        if settings.show((e.x_root, e.y_root)) == 'OK':
            self.applySettings()

    #bind motion events
    def onSelectAreaClick(self, e):
        self.__mousepos = (e.x, e.y)

    def onSelectAreaRelease(self, e):
        self.adjustPos()
        self.__mousepos = None

    def onSelectAreaMotion(self, e):
        #move
        dx = e.x - self.__mousepos[0]
        dy = e.y - self.__mousepos[1]
        self.move(dx, dy)
        self.__mousepos = (e.x, e.y)

    #}}

    #{{ canvas items
    def genArea(self, pos, size):
        img = Image.new('RGBA', size, (255,255,0,128))  #yellow 
        self.__cv_area_img = ImageTk.PhotoImage(img) #keep refg
        return self.__canvas.create_image(pos, image=self.__cv_area_img, anchor='nw')

    def genOKButton(self, order=1):
        x = self.pos[0] + self.size[0] - self.__button_side*order #x of upper-left
        y = self.pos[1]  #y of upper-left
        return self.__canvas.create_oval(x, y, x+self.__button_side, y+self.__button_side, fill='green')

    def genCancelButton(self, order=2):
        n = int(self.__button_side/4)
        x = self.pos[0] + self.size[0] - self.__button_side*order + 2*n  #x of center
        y = self.pos[1] + 2*n #y of center
        cross = ((0,n), (n,2*n), (2*n,n), (n,0), (2*n,-n), (n,-2*n), (0,-n), (-n,-2*n), (-2*n,-n), (-n,0), (-2*n,n), (-n, 2*n))
        cancel_cross = []
        for pt in cross:
            cancel_cross.append((pt[0]+x, pt[1]+y))
        return self.__canvas.create_polygon(cancel_cross, fill='red')

    def genSettingButton(self, order=3):
        n = int(self.__button_side/2)
        x = self.pos[0] + self.size[0] - self.__button_side*order + n  #x of center
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


