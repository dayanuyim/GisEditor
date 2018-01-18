#!/usr/bin/env python3
import os
import platform
import tkinter as tk
import xml.dom.minidom
import logging
import tempfile
import urllib.request
from tkinter import messagebox
from xml.etree import ElementTree as ET
from threading import Timer
from PIL import Image, ImageTk, ImageDraw, ImageColor
from uuid import uuid4
from src.raw import *

import pytz
from timezonefinder import TimezoneFinder

#my modules
import src.conf as conf
from src.coord import TileSystem, CoordinateSystem

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

# business utils ==========================
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

def getPtTimezone(pt):
    return getLocTimezone(lat=pt.lat, lon=pt.lon)

def getPtLocaltime(pt, tz=None):
    if tz is None:
        tz = getLocTimezone(lat=pt.lat, lon=pt.lon)
    if pt is not None and pt.time is not None:
        #assume time is localized by pytz.utc
        return pt.time.astimezone(tz)
    return None

def getPtTimeText(wpt, tz=None):
    time = getPtLocaltime(wpt, tz)

    return "N/A" if time is None else \
            time.strftime("%Y-%m-%d %H:%M:%S")

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

def bindCanvasDragEvents(canvas, item, cb, cursor='', enter_cb=None, leave_cb=None, release_cb=None):
    def setCursor(c):
        canvas['cursor'] = c
    def onClick(e):
        canvas.__canvas_mpos = (e.x, e.y)
    def onClickRelease(e):
        canvas.__canvas_mpos = None
        if release_cb:
            release_cb(e)
    def onClickMotion(e):
        x, y = canvas.__canvas_mpos
        dx, dy = e.x-x, e.y-y
        canvas.__canvas_mpos = (e.x, e.y)
        cb(e, dx, dy)

    if enter_cb is None: enter_cb = lambda e: setCursor(cursor)
    if leave_cb is None: leave_cb = lambda e: setCursor('')

    canvas.tag_bind(item, "<Enter>", enter_cb)
    canvas.tag_bind(item, "<Leave>", leave_cb)
    canvas.tag_bind(item, "<Button-1>", onClick)
    canvas.tag_bind(item, "<Button1-ButtonRelease>", onClickRelease)
    canvas.tag_bind(item, "<Button1-Motion>", onClickMotion)

def unbindCanvasDragEvents(canvas, item):
    canvas.tag_unbind(item, "<Enter>")
    canvas.tag_unbind(item, "<Leave>")
    canvas.tag_unbind(item, "<Button-1>")
    canvas.tag_unbind(item, "<Button1-ButtonRelease>")
    canvas.tag_unbind(item, "<Button1-Motion>")

#if 'autorepeat' is enabled, KeyRelease will be triggered even if the key is NOT physically released.
#using timer to trigger the release event only if we think the key is actually released.
def bindWidgetKeyMoveEvents(w, cb=None, ctrl_cb=None, shift_cb=None, release_cb=None, release_delay=0.3):
    def onKeyPress(cb_, e, dx, dy):
        if release_cb:
            #cancel the recent release event, if press time is closed to relase time
            if w.__move_key_release_timer and (e.time - w.__move_key_release_time)/1000 < release_delay:
                w.__move_key_release_timer.cancel()

        cb_(e, dx, dy)

    def onKeyRelease(e):
        w.__move_key_release_time = e.time
        w.__move_key_release_timer = Timer(release_delay, release_cb, (e,))
        w.__move_key_release_timer.start()

    if cb:
        w.bind('<Up>', lambda e: onKeyPress(cb, e, 0, -1))
        w.bind('<Down>', lambda e: onKeyPress(cb, e, 0, 1))
        w.bind('<Left>', lambda e: onKeyPress(cb, e, -1, 0))
        w.bind('<Right>', lambda e: onKeyPress(cb, e, 1, 0))

    if ctrl_cb:
        w.bind('<Control-Up>', lambda e: onKeyPress(ctrl_cb, e, 0, -1))
        w.bind('<Control-Down>', lambda e: onKeyPress(ctrl_cb, e, 0, 1))
        w.bind('<Control-Left>', lambda e: onKeyPress(ctrl_cb, e, -1, 0))
        w.bind('<Control-Right>', lambda e: onKeyPress(ctrl_cb, e, 1, 0))

    if shift_cb:
        w.bind('<Shift-Up>', lambda e: onKeyPress(shift_cb, e, 0, -1))
        w.bind('<Shift-Down>', lambda e: onKeyPress(shift_cb, e, 0, 1))
        w.bind('<Shift-Left>', lambda e: onKeyPress(shift_cb, e, -1, 0))
        w.bind('<Shift-Right>', lambda e: onKeyPress(shift_cb, e, 1, 0))

    if release_cb:
        w.__move_key_release_timer = None
        w.__move_key_release_time = 0
        w.bind('<KeyRelease-Up>', onKeyRelease)
        w.bind('<KeyRelease-Down>', onKeyRelease)
        w.bind('<KeyRelease-Left>', onKeyRelease)
        w.bind('<KeyRelease-Right>', onKeyRelease)


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

class GeoInfo:
    def __init__(self, ref_geo, level, coord_sys):
        self.__ref_geo = ref_geo
        self.__level = level
        self.__coord_sys = coord_sys

    def getNearbyGridPoint(self, pos, grid_sz=(1000,1000)):
        if self.__coord_sys not in SUPP_COORD_SYSTEMS:
            raise ValueError("Cannot get near by grid point for coordinate system '%s'" % (self.__coord_sys,))

        geo = self.__ref_geo.addPixel(pos[0], pos[1], self.__level)
        grid_x, grid_y = grid_sz

        grid_geo = None
        if self.__coord_sys == TWD67:
            x = round(geo.twd67_x/grid_x) * grid_x
            y = round(geo.twd67_y/grid_y) * grid_y
            grid_geo = GeoPoint(twd67_x=x, twd67_y=y)
        elif self.__coord_sys == TWD97:
            x = round(geo.twd97_x/grid_x) * grid_x
            y = round(geo.twd97_y/grid_y) * grid_y
            grid_geo = GeoPoint(twd97_x=x, twd97_y=y)
        else:
            raise ValueError("Unknown coord system '%s'" % (self.__coord_sys,))

        return grid_geo.diffPixel(self.__ref_geo, self.__level)

    def toPixelLength(self, km):
        geo2 = None
        if self.__coord_sys == TWD67:
            x = self.__ref_geo.twd67_x + km*1000
            y = self.__ref_geo.twd67_y
            geo2 = GeoPoint(twd67_x=x, twd67_y=y)
        elif self.__coord_sys == TWD97:
            x = self.__ref_geo.twd97_x + km*1000
            y = self.__ref_geo.twd97_y
            geo2 = GeoPoint(twd97_x=x, twd97_y=y)
        else:
            raise ValueError("Unknown coord system '%s'" % (self.__coord_sys,))

        return geo2.diffPixel(self.__ref_geo, self.__level)[0]

    def getCoordByPixel(self, px, py):
        geo = GeoPoint(px=px, py=py, level=self.__level)
        if self.__coord_sys == TWD67:
            return (geo.twd67_x, geo.twd67_y)
        if self.__coord_sys == TWD97:
            return (geo.twd97_x, geo.twd97_y)
        else:
            raise ValueError("Unknown coord system '%s'" % (self.__coord_sys,))

    def getPixelByCoord(self, x, y):
        geo = None
        if self.__coord_sys == TWD67:
            geo = GeoPoint(twd67_x=x, twd67_y=y)
        elif self.__coord_sys == TWD97:
            geo = GeoPoint(twd97_x=x, twd97_y=y)
        else:
            raise ValueError("Unknown coord system '%s'" % (self.__coord_sys,))
        return geo.pixel(self.__level)

#The UI of settings to access conf
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
        tk.Label(f, text='precision: level', anchor='e').pack(side='left', expand=1, fill='both')
        tk.Spinbox(f, from_=conf.MIN_SUPP_LEVEL, to=conf.MAX_SUPP_LEVEL, width=2, textvariable=self.var_level)\
                .pack(side='left', expand=1, fill='both')

        #align
        row += 1
        f = tk.Frame(self)
        f.grid(row=row, column=0, sticky='w')
        tk.Checkbutton(f, text='Align grid', variable=self.var_align)\
                .pack(side='left', expand=1, fill='both')

        #fixed
        row += 1
        def checkSizeWidgets():
            for w in self.__size_widgets:
                s = 'normal' if self.var_fixed.get() else 'disabled'
                w.config(state=s)
        f = tk.Frame(self)
        f.grid(row=row, column=0, sticky='w')
        tk.Checkbutton(f, text='Fixed size (KM)', variable=self.var_fixed, command=checkSizeWidgets)\
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

        #init run
        checkSizeWidgets()

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
        conf.writeUserConf()

class AreaSizeTooLarge(Exception):
    pass

class AreaSelector:
    @property
    def size(self):
        return self.__cv_panel_img.width(), self.__cv_panel_img.height()

    @property
    def pos(self):
        if self.__done.get():
            return self.__last_pos
        else:
            return self.__getpos()

    def __init__(self, canvas, geo_info=None):
        self.__canvas = canvas
        self.__geo_info = geo_info
        self.__button_side = 20
        self.__resizer_side = 15
        self.__done = tk.BooleanVar(value=False)
        self.__state = None
        self.__last_pos = None
        self.__except = None
        self.__panel_color = 'yellow'

        canvas_w = canvas.winfo_width()
        canvas_h = canvas.winfo_height()

        #size
        size = self.getFixedSize()
        if size is None:
            size = (round(canvas_w/2), round(canvas_h/2))
        w, h = size
        #pos
        pos = (round((canvas_w-w)/2), round((canvas_h-h)/2))

        #ceate items
        self.makeAreaPanel(pos, size)
        self.makeAreaBorders(pos, size)
        self.genOKButton()
        self.genCancelButton()
        self.genSettingButton()

        #apply
        try:
            self.applySettings()
        except AreaSizeTooLarge as ex:
            self.exit()
            raise ex

    #{{ interface
    def wait(self, parent):
        parent.wait_variable(self.__done)
        if self.__except:
            raise self.__except
        return self.__state

    def exit(self):
        if self.__done.get():
            return
        #rec the last pos
        self.__last_pos = self.__getpos()
        #delete item
        self.__canvas.delete('AS')  #delete objects of 'AreaSelector'
        self.__canvas['cursor'] = ''
        self.__done.set(True)

    #}} interface


    #{{ canvas items
    def makeAreaPanel(self, pos, size):
        self.__makeAreaPanel('panel', pos, size)

    def __makeAreaPanel(self, name, pos, size):
        #if exist and the same
        item = self.__canvas.find_withtag(name)
        if item and self.size == size:
            dx = pos[0] - self.pos[0]
            dy = pos[1] - self.pos[1]
            self.__canvas.move(name, dx, dy)
            return
        self.__canvas.delete(name)
        self.__genPanel(name, pos, size)

    def __genPanel(self, name, pos, size):
        #area img
        r, g, b = ImageColor.getrgb(self.__panel_color)
        w = max(1, size[0])
        h = max(1, size[1])
        img = Image.new('RGBA', (w,h), (r, g, b, 96))  #transparent
        img = ImageTk.PhotoImage(img) #to photo image
        #area item
        item = self.__canvas.create_image(pos, image=img, anchor='nw', tag=('AS',name))
        #bind
        bindCanvasDragEvents(self.__canvas, item, self.onMove, cursor='hand2',
            release_cb=lambda e: self.adjustPos())
        bindWidgetKeyMoveEvents(self.__canvas, self.onMove,
            lambda e, dx, dy: self.onResize('ctrl-arrow', e, dx, dy),
            lambda e, dx, dy: self.onResize('shift-arrow', e, dx, dy),
            lambda e: self.adjustPos())
        #side effect to keep ref
        self.__cv_panel_img = img

    def makeAreaBorders(self, pos, size):
        gpname = 'border'
        x, y = pos
        w, h = size
        #gen
        self.__makeBorder(gpname, 'top',    (x,y,x+w,y))
        self.__makeBorder(gpname, 'bottom', (x,y+h,x+w,y+h))
        self.__makeBorder(gpname, 'left',   (x,y,x,y+h))
        self.__makeBorder(gpname, 'right',  (x+w,y,x+w,y+h))

    def __makeBorder(self, gpname, name, coords):
        #if exist and the same
        item = self.__canvas.find_withtag(name)
        if item:
            orig_coords = self.__canvas.coords(item)
            if equalsLine(orig_coords, coords):
                #print("resizing border '%s' by moving" % (name,))
                dx = coords[0] - orig_coords[0]
                dy = coords[1] - orig_coords[1]
                self.__canvas.move(item, dx, dy) #just move
                return

        self.__canvas.delete(name)   #delete old
        self.__genBorder(gpname, name, coords)  #gen new

    def __genBorder(self, gpname, name, coords):
        color = self.__panel_color
        cursor = name + '_side'

        def onBorderEnter(e):
            if not conf.SELECT_AREA_FIXED:
                self.__canvas['cursor'] = cursor

        def onBorderLeave(e):
            if not conf.SELECT_AREA_FIXED:
                self.__canvas['cursor'] = ''

        border = self.__canvas.create_line(coords, width=2, fill=color, tag=('AS', gpname, name))
        bindCanvasDragEvents(self.__canvas, border,
            lambda e, dx, dy: self.onResize(name, e, dx, dy),
            enter_cb=onBorderEnter,
            leave_cb=onBorderLeave,
            release_cb=lambda e: self.adjustPos())

    def genOKButton(self, order=1):
        n = self.__button_side
        x = self.pos[0] + self.size[0] - self.__button_side*order #x of upper-left
        y = self.pos[1]  #y of upper-left
        item = self.__canvas.create_oval(x, y, x+n, y+n, fill='green', activefill='lime green', tag=('AS','button', 'ok'))
        self.__canvas.tag_bind(item, "<Button-1>", self.onOkClick)

    def genCancelButton(self, order=2):
        n = int(self.__button_side/4)
        x = self.pos[0] + self.size[0] - self.__button_side*order + 2*n  #x of center
        y = self.pos[1] + 2*n #y of center
        cross = ((0,n), (n,2*n), (2*n,n), (n,0), (2*n,-n), (n,-2*n), (0,-n), (-n,-2*n), (-2*n,-n), (-n,0), (-2*n,n), (-n, 2*n))
        cancel_cross = []
        for pt in cross:
            cancel_cross.append((pt[0]+x, pt[1]+y))
        item = self.__canvas.create_polygon(cancel_cross, fill='red3', activefill='red', tag=('AS','button', 'cancel'))
        self.__canvas.tag_bind(item, "<Button-1>", self.onCancelClick)

    def genSettingButton(self, order=3):
        n = int(self.__button_side/2)
        x = self.pos[0] + self.size[0] - self.__button_side*order + n  #x of center
        y = self.pos[1] + n #y of center
        item = self.__canvas.create_text(x, y, text='S', font= 'Arialuni 16 bold', fill='gray25', activefill='gray40',
                tag=('AS','button', 'setting'))
        self.__canvas.tag_bind(item, "<Button-1>", self.onSettingClick)

    def genResizer(self):
        n = self.__resizer_side
        x = self.pos[0] + self.size[0]
        y = self.pos[1] + self.size[1]
        rect_triangle = (x, y, x-n, y, x, y-n)
        resizer = self.__canvas.create_polygon(rect_triangle, fill='green', activefill='lime', tag=('AS','resizer'))

        on_resize = lambda e, dx, dy: self.onResize('resizer', e, dx, dy)
        bindCanvasDragEvents(self.__canvas, resizer, on_resize, 'bottom_right_corner')
    #}}

    #{{ internal operations
    def __getpos(self):
        panel = self.__canvas.find_withtag('panel')
        x, y = self.__canvas.coords(panel)
        return int(x), int(y)

    def move(self, dx, dy):
        self.__canvas.move('AS', dx, dy)

    def lift(self):
        self.__canvas.tag_raise('button')
        self.__canvas.tag_raise('resizer')

    def adjustPos(self):
        if conf.SELECT_AREA_ALIGN and self.__geo_info is not None:
            try:
                grid_x, grid_y = self.__geo_info.getNearbyGridPoint(self.pos)
                dx = grid_x - self.pos[0]
                dy = grid_y - self.pos[1]
                self.move(dx, dy)
            except Exception as ex:
                messagebox.showwarning("Adjust pos error", str(ex))

    def applySettings(self):
        self.scaleGeo()
        self.adjustPos()
        self.checkResizer()

    def scaleGeo(self):
        sz = self.getFixedSize()
        if sz is not None:
            #chck size
            w, h = sz
            if w > self.__canvas.winfo_width() and h > self.__canvas.winfo_height():
                raise AreaSizeTooLarge("The specified size is too large")
            #pos
            pos = max(0, self.pos[0]), max(0, self.pos[1]) #avoid no seeing after resize
            #resize
            self.resize(sz, pos)

    def getFixedSize(self):
        if conf.SELECT_AREA_FIXED and self.__geo_info is not None:
            w = self.__geo_info.toPixelLength(conf.SELECT_AREA_X)
            h = self.__geo_info.toPixelLength(conf.SELECT_AREA_Y)
            return w, h
        return None

    def resize(self, size, pos=None):
        if self.size == size or \
           size[0] <= self.__button_side*len(self.__canvas.find_withtag('button')) or \
           size[1] <= self.__button_side+self.__resizer_side:
            return
        #bookkeeper
        orig_pos = self.pos
        orig_size = self.size
        if pos is None:
            pos = orig_pos
        dx = pos[0]-orig_pos[0]
        dy = pos[1]-orig_pos[1]
        dw = size[0]-orig_size[0]
        dh = size[1]-orig_size[1]
        #resize panel/borders
        self.makeAreaPanel(pos, size)
        self.makeAreaBorders(pos, size)
        #re-locate others
        self.__canvas.move('button', dx+dw, dy)
        self.__canvas.move('resizer', dx+dw, dy+dh)
        self.lift()

    def checkResizer(self):
        resizer = self.__canvas.find_withtag('resizer')
        if conf.SELECT_AREA_FIXED:
            if resizer:
                self.__canvas.delete(resizer)
        else:
            if not resizer:
                self.genResizer()


    #}} general operations

    #{{ events
    def onOkClick(self, e=None):
        self.__state = 'OK'
        self.exit()

    def onCancelClick(self, e=None):
        self.__state = 'Cancel'
        self.exit()

    def onSettingClick(self, e):
        setting = AreaSelectorSettings(self.__canvas)
        if setting.show((e.x_root, e.y_root)) == 'OK':
            try:
                self.applySettings()
            except AreaSizeTooLarge as ex:
                self.__except = ex
                self.exit()

    def onMove(self, e, dx, dy):
        self.move(dx, dy)

    def onResize(self, name, e, dx, dy):
        if not conf.SELECT_AREA_FIXED:
            SHIFT, CTRL = 1, 4

            x, y = self.pos
            w, h = self.size
            if e.state & SHIFT:  #reverse direction
                dx, dy = -dx, -dy

            if name == 'top' or e.keysym == 'Up':
                self.resize((w,h-dy), (x,y+dy))
            elif name == 'bottom' or e.keysym == 'Down':
                self.resize((w,h+dy))
            elif name == 'left' or e.keysym == 'Left':
                self.resize((w-dx,h), (x+dx,y))
            elif name == 'right' or e.keysym == 'Right':
                self.resize((w+dx,h))
            elif name == 'resizer':
                self.resize((w+dx,h+dy))
            else:
                raise ValueError("Unknown border '%s' to resize" % (name_,))

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

if __name__ == '__main__':
    img = Image.new('RGBA', (400,300), (255, 255, 255, 96))  #transparent
    with DrawGuard(img) as draw:
        print('...processing')
