#!/usr/bin/env python3
# -*- coding: utf8 -*-

import os
import subprocess
import sys
import tkinter as tk
import Pmw as pmw
import urllib.request
import shutil
import tempfile
import time
import logging
import argparse
import platform
import re
from os import path
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageColor
from math import floor, ceil, sqrt
from tkinter import messagebox, filedialog, ttk
from datetime import datetime, timedelta
from threading import Lock, Thread
from collections import OrderedDict

#my modules
import conf
import util
import sym
import coord
from ui import Dialog, MapSelectDialog, MapSelectFrame
from gpx import GpsDocument, WayPoint
from pic import PicDocument
from util import GeoPoint, getPrefCornerPos, DrawGuard, imageIsTransparent
from util import AreaSelector, AreaSizeTooLarge, GeoInfo  #should move to ui.py
from tile import TileAgent, MapDescriptor
from sym import askSym, toSymbol

to_pixel = coord.TileSystem.getPixcelXYByTileXY
to_tile = coord.TileSystem.getTileXYByPixcelXY

#print to console/log and messagebox (generalize this with LOG, moving to util.py)
def showmsg(msg):
    logging.error(msg)
    messagebox.showwarning('', msg)

#read pathes
def isGpsFile(path):
    (fname, ext) = os.path.splitext(path)
    ext = ext.lower()
    return ext in conf.GPSBABEL_EXT_FMT

def isPicFile(path):
    (fname, ext) = os.path.splitext(path)
    ext = ext.lower()

    if ext in ('.jpg', '.jpeg', '.tif', '.gif', '.png'):
        return True
    return False

def downloadAsTemp(url):
    ext = url.split('.')[-1]
    tmp_path = os.path.join(tempfile.gettempdir(),  "giseditor_dl." + ext)

    with urllib.request.urlopen(url, timeout=30) as response, open(tmp_path, 'wb') as tmp_file:
        tmp_file.write(response.read())

    return tmp_path


def getGpsDocument(path):
    try:
        #support http
        if path.startswith("http"):
            path = downloadAsTemp(path)

        (fname, ext) = os.path.splitext(path)
        ext = ext.lower()
        gps = GpsDocument(conf.TZ)

        if ext == '.gpx':
            gps.load(filename=path)
        else:
            gpx_path = toGpxFile(path)
            gps.load(filename=gpx_path)
            os.remove(gpx_path)        #remove tmp file
            #pythonW.exe seems causing pipe error, if we get output from stdout directly.
            #gpx_string = toGpxString(path)
            #gps.load(filestring=gpx_string)
        return gps
    except Exception as ex:
        showmsg("Error to open '%s': %s" % (path, str(ex)))
        return None

def getPicDocument(path):
    try:
        return PicDocument(path, conf.TZ)
    except Exception as ex:
        showmsg("cannot read the picture '%s': %s" % (path, str(ex)))
    return None

def __toGpx(src_path, flag):
    exe_file = conf.GPSBABEL_EXE

    #input format
    (fname, ext) = os.path.splitext(src_path)
    if ext == '':
        raise ValueError("cannot identify gps format deu to no file extension")
    input_fmt = conf.GPSBABEL_EXT_FMT.get(ext)
    if not input_fmt:
        raise ValueError("cannot identify gps format for the file extension: " + ext)
    if len(input_fmt) > 1:
        raise ValueError("cannot identify gps format, candidates are " + str(input_fmt))
    input_fmt = input_fmt[0]

    #input path: to work around the problem of gpsbabel connot read non-ascii filename
    input_tmp_path = os.path.join(tempfile.gettempdir(),  "giseditor_in.tmp")
    shutil.copyfile(src_path, input_tmp_path)  
    try:
        if flag == 'string':
            cmd = '"%s" -i %s -f "%s" -o gpx,gpxver=1.1 -F -' % (exe_file, input_fmt, input_tmp_path)
            logging.info(cmd)
            output = subprocess.check_output(cmd, shell=True)  #NOTICE: pythonW.exe caused 'WinError 6: the handler is invalid'
            result = output.decode("utf-8")
        elif flag == 'file':
            output_tmp_path = os.path.join(tempfile.gettempdir(),  "giseditor_out.tmp")
            cmd = '"%s" -i %s -f "%s" -o gpx,gpxver=1.1 -F "%s"' % (exe_file, input_fmt, input_tmp_path, output_tmp_path)
            logging.info(cmd)
            subprocess.call(cmd, shell=True)
            result = output_tmp_path
        else:
            raise ValueError('Unknow type to convert to gpx by ' + flag)
    finally:
        os.remove(input_tmp_path) #clean tmp file before return
    return result

def toGpxFile(src_path):
    return __toGpx(src_path, 'file')

def toGpxString(src_path):
    return __toGpx(src_path, 'string')

def __parsePath(path, gps_path, pic_path):
    if not path:
        return
    if os.path.isdir(path):
        for f in os.listdir(path):
            subpath = os.path.join(path, f)
            __parsePath(subpath, gps_path, pic_path)
    elif isPicFile(path):
        pic_path.append(path)
    elif isGpsFile(path):
        gps_path.append(path)
    else:
        logging.info("omit the file: " + path)

#may generalize the method, and moving to util.py
def parsePathes(pathes):
    gps_path = []
    pic_path = []
    for path in pathes:
        __parsePath(path, gps_path, pic_path)
    gps_path.sort()
    pic_path.sort()
    return gps_path, pic_path

#The Main board to display the map
class MapBoard(tk.Frame):
    @property
    def is_alter(self): return self.__alter_time is not None

    @property
    def alter_time(self): return self.__alter_time

    @property
    def version(self):
        return self.__version

    @version.setter
    def version(self, v):
        self.__version = v
        self.__ver_label['text'] = 'ver. ' + v

    @classmethod
    def __loadMapDescriptors(cls, dirpath):
        map_descs = []
        for f in os.listdir(dirpath):
            if os.path.splitext(f)[1].lower() == ".xml":
                try:
                    desc = MapDescriptor.parseXml(os.path.join(dirpath, f))
                    map_descs.append(desc)
                except Exception as ex:
                    logging.error("parse file '%s' error: %s" % (f, str(ex)))
        return sorted(map_descs, key=lambda d:d.map_title)

    @classmethod
    def __findMapDescriptor(cls, descs, id):
        for d in descs:
            if d.map_id == id:
                return d
        return None

    def __writeUserMapsConf(self):
        maps = OrderedDict()
        for desc in self.__map_descs:
            maps[desc.map_id] = (desc.enabled, desc.alpha)
        conf.USER_MAPS = maps
        conf.writeUserConf()

    @classmethod
    def __getUserMapDescriptors(cls):
        app_descs = cls.__loadMapDescriptors(conf.MAPCACHE_DIR)

        user_descs = []
        for id, (en, alpha) in conf.USER_MAPS.items():
            desc = cls.__findMapDescriptor(app_descs, id)
            if desc is not None:
                desc.enabled = en
                desc.alpha = alpha
                app_descs.remove(desc)
                user_descs.append(desc)

        user_descs.extend(app_descs)
        return user_descs

    def __init__(self, master):
        super().__init__(master)

        self.__map_descs = self.__getUserMapDescriptors()
        self.__map_ctrl = MapController(self)
        self.__map_ctrl.configMap(self.__map_descs)

        self.__map_sel_board = None

        #board
        self.__is_closed = False
        self.__bg_color=self['bg']
        self.__focused_wpt = None
        self.__focused_geo = None
        self.__map = None         #buffer disp image for restore map
        self.__map_attr = None
        self.__map_req_time = datetime.min
        self.__map_has_update = False
        self.__map_req_lock = Lock()
        self.__alter_time = None
        self.__pref_dir = None
        self.__pref_geo = None
        self.__some_geo = GeoPoint(lon=121.334754, lat=24.987969)
        self.__left_click_pos = None
        self.__right_click_pos = None
        self.__mouse_wheel_ts = datetime.min
        self.__version = ''

        Thread(target=self.__runMapUpdater).start()

        #canvas items
        self.__canvas_map = None
        self.__canvas_sel_area = None

        #info
        self.__info_frame = self.initMapInfo()
        self.__info_frame.pack(side='top', expand=0, fill='x', anchor='nw')
        self.setMapInfo()

        #status
        status_frame = self.initStatusBar()
        status_frame.pack(side='bottom', expand=0, fill='x', anchor='nw')

        #display area
        self.__init_w= 800  #deprecated
        self.__init_h = 600  #deprecated
        self.disp_canvas = tk.Canvas(self, bg='#808080')
        self.disp_canvas.pack(expand=1, fill='both', anchor='n')
        if platform.system() == "Linux":
            self.disp_canvas.bind('<Button-4>', lambda e: self.onMouseWheel(e, 1))  #roll up
            self.disp_canvas.bind('<Button-5>', lambda e: self.onMouseWheel(e, -1)) #roll down
        else:
            self.disp_canvas.bind('<MouseWheel>', lambda e: self.onMouseWheel(e, e.delta))
        self.disp_canvas.bind('<Motion>', self.onMotion)
        self.disp_canvas.bind("<Button-1>", lambda e: self.onClickDown(e, 'left'))
        self.disp_canvas.bind("<Button-3>", lambda e: self.onClickDown(e, 'right'))
        self.disp_canvas.bind("<Button1-Motion>", self.onClickMotion)
        self.disp_canvas.bind("<Button1-ButtonRelease>", lambda e: self.onClickUp(e, 'left'))
        self.disp_canvas.bind("<Button3-ButtonRelease>", lambda e: self.onClickUp(e, 'right'))
        self.disp_canvas.bind("<Configure>", self.onResize)

        #right-click menu
        self.__rclick_menu = tk.Menu(self.disp_canvas, tearoff=0)
        self.__rclick_menu.add_command(label='Add Files', underline=0, command=self.onAddFiles)
        self.__rclick_menu.add_separator()
        self.__rclick_menu.add_command(label='Add wpt', command=self.onAddWpt)
        '''
        edit_wpt_menu = tk.Menu(self.__rclick_menu, tearoff=0)
        edit_wpt_menu.add_command(label='Edit 1-by-1', underline=5, command=lambda:self.onEditWpt(mode='single'))
        edit_wpt_menu.add_command(label='Edit in list', underline=5, command=lambda:self.onEditWpt(mode='list'))
        self.__rclick_menu.add_cascade(label='Edit waypoints...', menu=edit_wpt_menu)
        '''
        self.__rclick_menu.add_command(label='Edit waypoints', underline=0, command=lambda:self.onEditWpt(mode='single'))
        self.__rclick_menu.add_command(label='Show waypoints list', underline=0, command=lambda:self.onEditWpt(mode='list'))

        num_wpt_menu = tk.Menu(self.__rclick_menu, tearoff=0)
        num_wpt_menu.add_command(label='By time order', command=lambda:self.onNumberWpt(time=1))
        num_wpt_menu.add_command(label='By name order', command=lambda:self.onNumberWpt(name=1))
        self.__rclick_menu.add_cascade(label='Numbering wpt...', menu=num_wpt_menu)
        self.__rclick_menu.add_command(label='UnNumbering wpt', underline=0, command=self.onUnnumberWpt)
        self.__rclick_menu.add_command(label='Toggle wpt name', underline=0, command=self.onToggleWptNmae)
        self.__rclick_menu.add_command(label='Apply symbol rules', underline=0, command=self.onApplySymbolRule)
        self.__rclick_menu.add_separator()
        '''
        edit_trk_menu = tk.Menu(self.__rclick_menu, tearoff=0)
        edit_trk_menu.add_command(label='Edit 1-by-1', underline=5, command=lambda:self.onEditTrk(mode='single'))
        edit_trk_menu.add_command(label='Edit in list', underline=5, command=lambda:self.onEditTrk(mode='list'))
        self.__rclick_menu.add_cascade(label='Edit tracks...', menu=edit_trk_menu)
        '''
        self.__rclick_menu.add_command(label='Edit tracks', underline=5, command=lambda:self.onEditTrk(mode='single'))
        split_trk_menu = tk.Menu(self.__rclick_menu, tearoff=0)
        split_trk_menu.add_command(label='By day', command=lambda:self.onSplitTrk(self.trkDiffDay))
        split_trk_menu.add_command(label='By time gap', command=lambda:self.onSplitTrk(self.trkTimeGap))
        split_trk_menu.add_command(label='By distance', command=lambda:self.onSplitTrk(self.trkDistGap))
        self.__rclick_menu.add_cascade(label='Split tracks...', menu=split_trk_menu)
        self.__rclick_menu.add_separator()
        self.__rclick_menu.add_command(label='Save to image...', underline=0, command=self.onImageSave)
        self.__rclick_menu.add_command(label='Save to gpx...', underline=0, command=self.onGpxSave)

        #wpt menu
        self.__wpt_rclick_menu = tk.Menu(self.disp_canvas, tearoff=0)
        self.__wpt_rclick_menu.add_command(label='Delete Wpt', underline=0, command=self.onWptDeleted)

    def initMapInfo(self):
        font = 'Arialuni 12'
        bfont = font + ' bold'
        bfont_10 = 'Arialuni 10 bold'

        frame = tk.Frame(self, relief='ridge', bd=1)

        #title
        self.__info_mapname = tk.Label(frame, font=bfont, anchor='nw', bg='lightgray')
        self.__info_mapname.pack(side='left', expand=0, anchor='nw')

        self.__map_btn = tk.Button(frame, text="▼", relief='groove', border=2, command=self.OnMapSelected)
        self.__map_btn.pack(side='left', expand=0, anchor='nw')

        #level
        self.__info_level = self.__genInfoWidgetNum(frame, font, 'Level', 2,
                conf.MIN_SUPP_LEVEL, conf.MAX_SUPP_LEVEL, self.onSetLevel)

        #pos
        self.__info_67tm2 = self.__genInfoWidget(frame, font, 'TM2/67', 16, self.onSetPos)
        self.__info_97tm2 = self.__genInfoWidget(frame, font, 'TM2/97', 16, self.onSetPos)
        self.__info_97latlon = self.__genInfoWidget(frame, font, 'LatLon/97', 20, self.onSetPos)

        return frame

    def __genInfoWidget(self, frame, font, title, width, cb=None):
        bfont = font + ' bold'

        label = tk.Label(frame, font=bfont, text=title)
        label.pack(side='left', expand=0, anchor='nw')

        var = tk.StringVar()
        entry = tk.Entry(frame, font=font, width=width, textvariable=var)
        entry.pack(side='left', expand=0, anchor='nw')
        entry.variable = var

        if cb is not None:
            entry.bind('<Return>', cb)

        return entry

    def __genInfoWidgetNum(self, frame, font, title, width, min_, max_, cb=None):

        bfont = font + ' bold'

        label = tk.Label(frame, font=bfont, text=title)
        label.pack(side='left', expand=0, anchor='nw')

        var = tk.IntVar()
        widget = tk.Spinbox(frame, font=font, width=width, textvariable=var, from_=min_, to=max_)
        widget.pack(side='left', expand=0, anchor='nw')
        widget.variable = var

        if cb is not None:
            var.trace('w', cb)

        return widget
        

    def initStatusBar(self):
        font = 'Arialuni 10'
        bg='lightgray'
        frame = tk.Frame(self, relief='ridge', bd=1, bg=bg)

        self.__ver_label = tk.Label(frame, font=font, bg=bg)
        self.__ver_label.pack(side='right', expand=0, anchor='ne')

        self.__status_prog = ttk.Progressbar(frame, mode='determinate', maximum=100)
        self.__status_prog.pack(side='right', expand=0, anchor='ne')

        self.__status_label = tk.Label(frame, font=font, bg=bg)
        self.__status_label.pack(side='left', expand=0, anchor='nw')

        return frame

    #{{{ operations
    def isSavingImage(self):
        return self.__canvas_sel_area is not None

    #release sources to exit
    def exit(self):
        self.__is_closed = True
        if self.isSavingImage():
            self.__canvas_sel_area.exit()
        self.__map_ctrl.close()

    #}}} operations

    
    #{{{ Events
    def __onMapEnableChanged(self, desc, old_val):
        logging.debug("desc %s's enable change from %s to %s" % (desc.map_id, old_val, desc.enabled))
        #re-config
        self.__map_descs = self.__map_sel_board.map_descriptors
        self.__map_ctrl.configMap(self.__map_descs)
        self.resetMap()

    def __onMapAlphaChanged(self, desc, old_val):
        logging.debug("desc %s's enable change from %f to %f" % (desc.map_id, old_val, desc.alpha))
        if desc.enabled:
            self.resetMap(force='all')

    def __triggerMapSelector(self):
        if self.__map_sel_board is None:
            #create
            self.__map_sel_board = MapSelectFrame(self, self.__map_descs)
            self.__map_sel_board.visible = False

            self.__map_sel_board.setEnableHandler(self.__onMapEnableChanged)
            self.__map_sel_board.setAlphaHandler(self.__onMapAlphaChanged)
            self.master.bind("<Escape>", lambda e: self.__hideMapSelector()) #ESC to hide
            
        #to show
        if not self.__map_sel_board.visible:
            self.__showMapSelector()
        #to hidden
        else:
            self.__hideMapSelector()

    def __showMapSelector(self):
        if self.__map_sel_board is not None:
            ref_w = self.__info_frame
            x = ref_w.winfo_x()
            y = ref_w.winfo_y() + ref_w.winfo_height()

            self.__map_sel_board.place(x=x, y=y)
            self.__map_sel_board.visible = True
            self.__map_btn['text'] = "▲"

    def __hideMapSelector(self):
        if self.__map_sel_board is not None:
            self.__map_sel_board.place_forget()
            self.__map_sel_board.visible = False
            self.__map_btn['text'] = "▼"

            self.setMapInfo()          #re-show map info
            self.__writeUserMapsConf() #save config

    def OnMapSelected(self):
        if self.isSavingImage():
            return

        self.__triggerMapSelector()

    def onSetLevel(self, *args):
        if self.isSavingImage():
            return

        try:
            level = self.__info_level.variable.get()
            if self.__map_ctrl.level != level:  #changed by user
                self.__map_ctrl.level = level
                self.setMapInfo()
                self.resetMap()
        except Exception as ex:
            errmsg = "set level error: %s" % (str(ex),)
            logging.error(errmsg)
            messagebox.showwarning('', errmsg)
            return

    def onSetPos(self, e):
        #if val_txt is digit, regarding as int with unit 'meter'
        #          otherwise, regarding as float with unit 'kilimeter'
        def toTM2(val_txt):
            val_txt = val_txt.strip()
            return int(val_txt) if val_txt.isdigit() else int(float(val_txt)*1000)

        def toDegree(val_txt):
            val_txt = val_txt.strip()
            return float(val_txt)

        #get geo point
        geo = None
        try:
            pos = e.widget.get()
            x, y = filter(None, re.split(',| ', pos)) #split by ',' and ' ', removing empty string

            #make geo according to the coordinate
            if e.widget == self.__info_67tm2:
                geo = GeoPoint(twd67_x=toTM2(x), twd67_y=toTM2(y))
            elif e.widget == self.__info_97tm2:
                geo = GeoPoint(twd97_x=toTM2(x), twd97_y=toTM2(y))
            elif e.widget == self.__info_97latlon:
                geo = GeoPoint(lat=toDegree(x), lon=toDegree(y))
            else:
                raise ValueError("Code flow error to set location") #should not happen
        except Exception as ex:
            messagebox.showwarning("Please use format '%d,%d'.", "get locatoin error: %s" % (str(ex),))
            return

        #check
        if not self.__map_ctrl.mapContainsPt(geo):
            messagebox.showwarning('Invalid Location', "The location is out of range of map")
            return

        #focus geo on map
        self.__map_ctrl.addMark(geo)
        self.setMapInfo(geo)
        self.resetMap(geo, force='wpt')

    def __getMapNameText(self):
        mapname_txt = ""
        map_enabled_count = 0

        for desc in self.__map_descs:
            if desc.enabled:
                map_enabled_count += 1
                if not mapname_txt:
                    mapname_txt = desc.map_title

        if map_enabled_count > 1:
            mapname_txt += "...(%d)" % (map_enabled_count,)

        return mapname_txt

    def setMapInfo(self, geo=None):
        self.__info_mapname['text'] = self.__getMapNameText()

        self.__info_level.variable.set(self.__map_ctrl.level)

        if geo is not None:
            self.__info_97latlon.variable.set("%f, %f" % (geo.lat, geo.lon))
            self.__info_97tm2.variable.set("%.3f, %.3f" % (geo.twd97_x/1000, geo.twd97_y/1000))
            self.__info_67tm2.variable.set("%.3f, %.3f" % (geo.twd67_x/1000, geo.twd67_y/1000))


    def __setStatus(self, txt = None, prog=None, is_immediate=False):
        txt_has_change = False
        if txt is not None and self.__status_label['text'] != txt:
            self.__status_label['text'] = txt
            txt_has_change = True

        prog = int(prog)
        prog_has_change = False
        if prog is not None and self.__status_prog['value'] != prog:
            self.__status_prog['value'] = prog
            prog_has_change = True

        if (txt_has_change or prog_has_change) and is_immediate:
            self.update()

    def addGpx(self, gpx):
        if gpx is not None:
            self.__map_ctrl.addGpxLayer(gpx)

    def addWpt(self, wpt):
        if wpt is not None:
            self.__map_ctrl.addWpt(wpt)

    def __getPrefGeoPt(self):
        #prefer track point
        for trk in self.__map_ctrl.getAllTrks():
            for pt in trk:
                return pt

        #wpt
        for wpt in self.__map_ctrl.getAllWpts():
            return wpt

        return None
        
    def onMouseWheel(self, event, delta):
        if self.isSavingImage():
            return

        if datetime.now() < (self.__mouse_wheel_ts + timedelta(milliseconds=500)):
            return

        self.__mouse_wheel_ts = datetime.now()

        ctrl = self.__map_ctrl
        level = ctrl.level + (1 if delta > 0 else -1)

        if conf.MIN_SUPP_LEVEL <= level and level <= conf.MAX_SUPP_LEVEL:
            ctrl.shiftGeoPixel(event.x, event.y) #make click point as focused geo
            ctrl.level = level
            ctrl.shiftGeoPixel(-event.x, -event.y) #shift to make click point at the same position

            self.setMapInfo()
            self.resetMap()
        else:
            messagebox.showwarning('Level Over Limit', 'The level should between %d ~ %d' % (conf.MIN_SUPP_LEVEL, conf.MAX_SUPP_LEVEL))

    def onClickDown(self, e, flag):
        #to grap key events
        e.widget.focus_set()

        #rec
        if flag == 'left':
            self.__left_click_pos = (e.x, e.y)
        elif flag == 'right':
            self.__right_click_pos = (e.x, e.y)

        #geo info
        geo = self.getGeoPointAt(e.x, e.y)
        self.setMapInfo(geo)

        if self.isSavingImage():
            return

        #wpt context, if any
        wpt = self.__map_ctrl.getWptAround(geo)
        if wpt:
            if flag == 'left':
                self.onEditWpt(mode='single', wpt=wpt)
            elif flag == 'right':
                self.__wpt_rclick_menu.post(e.x_root, e.y_root)  #right menu for wpt
        #general right menu
        elif flag == 'right':
            self.__rclick_menu.post(e.x_root, e.y_root)  #right menu
        #unpost, if any
        else:
            self.__right_click_pos = None
            self.__rclick_menu.unpost()
            self.__wpt_rclick_menu.unpost()

    #to handle preferred dir : no exist, success, or exception
    def withPreferredDir(self, action_cb):
        if self.__pref_dir and not os.path.exists(self.__pref_dir):
            self.__pref_dir = None
            
        try:
            result = action_cb(self.__pref_dir)
            if result:
                self.__pref_dir = None  #no init dir after successful saving
            return result
        except Exception as ex:
            self.__pref_dir = None  #no init dir if exception
            raise ex

    def addFiles(self, file_pathes):
        gps_path, pic_path = parsePathes(file_pathes)  
        for path in gps_path:
            self.addGpx(getGpsDocument(path))
        for path in pic_path:
            self.addWpt(getPicDocument(path))

        #also update preferred dir if needed
        def getPrefDir(pathes):
            return None if not len(pathes) else os.path.dirname(pathes[0])
        if not self.__pref_dir:
            self.__pref_dir = getPrefDir(gps_path)
        if not self.__pref_dir:
            self.__pref_dir = getPrefDir(pic_path)

    #{{ Right click actions
    def onAddFiles(self):
        def to_ask(init_dir):
            return filedialog.askopenfilenames(initialdir=init_dir)
        try:
            #add filenames
            filenames = self.withPreferredDir(to_ask)
            if not filenames:
                return
            self.addFiles(filenames)

            #show, may go to preffered geo
            if not self.__pref_geo:
                self.__pref_geo = self.__getPrefGeoPt()
                self.setMapInfo(self.__pref_geo)
                self.resetMap(self.__pref_geo)
            else:
                self.setAlter('all')
        except Exception as ex:
            showmsg('Add Files Error: %s' % (str(ex),))

    def onAddWpt(self):
        if not self.__right_click_pos:
            showmsg('Create Wpt Error: Cannot not get right click position')
            return

        #create wpt
        px, py = self.__right_click_pos
        geo = self.getGeoPointAt(px, py)
        wpt = WayPoint(geo.lat, geo.lon)
        wpt.time = datetime.now()

        #add wpt
        self.addWpt(wpt)
        self.setAlter('wpt')

    def onNumberWpt(self, name=None, time=None):
        wpt_list = self.__map_ctrl.getAllWpts()
        if name is not None:
            wpt_list = sorted(wpt_list, key=lambda wpt: wpt.name)
        elif time is not None:
            wpt_list = sorted(wpt_list, key=lambda wpt: wpt.time if wpt.time else datetime.min)

        sn = 0
        for wpt in wpt_list:
            sn += 1
            wpt.name = "%02d %s" % (sn, wpt.name)

        self.setAlter('wpt')

    def onUnnumberWpt(self):
        wpt_list = self.__map_ctrl.getAllWpts()
        for wpt in wpt_list:
            idx = wpt.name.find(' ')
            if idx >= 0 and wpt.name[:idx].isdigit():
                wpt.name = wpt.name[idx+1:]
        self.setAlter('wpt')

    def onToggleWptNmae(self):
        self.__map_ctrl.is_hide_text = not self.__map_ctrl.is_hide_text
        self.resetMap(force='wpt')

    def onApplySymbolRule(self):
        is_alter = False

        for wpt in self.__map_ctrl.getAllWpts():
            sym = toSymbol(wpt.name)
            if wpt.sym != sym:
                wpt.sym = sym
                is_alter = True

        if is_alter:
            self.setAlter('wpt')

    def onEditTrk(self, mode, trk=None):
        trk_list = self.__map_ctrl.getAllTrks()
        if not trk_list:
            messagebox.showwarning('', "No Tracks Found")
            return

        if mode == 'single':
            trk_board = TrkSingleBoard(self, trk_list, trk)
        else:
            trk_board = TrkListBoard(self, trk_list, trk)
        #trk_board.addAlteredHandler(self.setAlter)
        #trk_board.show()


    @staticmethod
    def trkDiffDay(pt1, pt2):
        t1 = pt1.time + conf.TZ
        t2 = pt2.time + conf.TZ
        return not (t1.year == t2.year and \
                    t1.month == t2.month and \
                    t1.day == t2.day)

    @staticmethod
    def trkTimeGap(pt1, pt2):
        return pt2.time - pt1.time > conf.SPLIT_TIME_GAP

    @staticmethod
    def trkDistGap(pt1, pt2):
        dx = pt2.twd97_x - pt1.twd97_x
        dy = pt2.twd97_y - pt1.twd97_y
        dist = sqrt(dx**2+dy**2)
        #print('dist', dist)
        return dist > conf.SPLIT_DIST_GAP

    def onSplitTrk(self, split_fn):
        is_alter = False
            
        for gpx in self.__map_ctrl.gpx_layers:
            if gpx.splitTrk(split_fn):
                is_alter = True

        if is_alter:
            self.setAlter('trk')

    def onEditWpt(self, mode, wpt=None):
        wpt_list = self.__map_ctrl.getAllWpts()
        if len(wpt_list) == 0:
            messagebox.showwarning('', 'No Waypoints to show')
            return
        if mode == 'single':
            wpt_board =  WptSingleBoard(self, wpt_list, wpt)
        elif mode == 'list':
            wpt_board =  WptListBoard(self, wpt_list, wpt)
        else:
            raise ValueError("WptBoade only supports mode: 'single' and 'list'")
        #print('after wptboard')
        #wpt_board.addAlteredHandler(self.setAlter)
        #wpt_board.show()
        self.__focused_wpt = None

    def __setMapProgress(self, rate, is_immediate=False):
        logging.critical("set map progress %f", rate)
        #set status
        if rate >= 1:
            self.__setStatus('', 0, is_immediate)
        else:
            prog = 100 * rate
            txt = "Map Loading...%.1f%%" % (prog,)
            self.__setStatus(txt, prog, is_immediate)

    def onImageSave(self):
        if self.isSavingImage():
            return

        enabled_maps = [desc for desc in self.__map_descs if desc.enabled]
        if not enabled_maps:
            messagebox.showwarning("Save Image Error", "No maps to save")
            return

        #get preferred coord system
        coord_sys = [desc.coord_sys for desc in self.__map_descs if desc.enabled and desc.coord_sys in ("TWD67", "TWD97")]
        if coord_sys:
            coord_sys = coord_sys[0]
        else:
            coord_sys = enabled_maps[0].coord_sys

        try:
            #select area
            geo_info = GeoInfo(self.__map_ctrl.geo, self.__map_ctrl.level, coord_sys)
            self.__canvas_sel_area = AreaSelector(self.disp_canvas, geo_info)
            if self.__canvas_sel_area.wait(self) != 'OK':
                return

            #get fpath
            def to_ask(init_dir):
                return filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=(("Portable Network Graphics", ".png"), ("All Files", "*.*")),
                    initialdir=init_dir)
            fpath = self.withPreferredDir(to_ask)
            if not fpath:
                return False

            #output
            out_level = conf.SELECT_AREA_LEVEL
            org_level = self.__map_ctrl.level
            w, h = self.__canvas_sel_area.size
            x, y = self.__canvas_sel_area.pos
            #bounding geo
            sel_geo = self.__map_ctrl.geo.addPixel(x, y, org_level)  #upper-left
            ext_geo = sel_geo.addPixel(w, h, org_level)            #lower-right
            dx, dy = ext_geo.diffPixel(sel_geo, out_level)

            #prepare map progress info
            img_area = TileArea(out_level, sel_geo.pixel(out_level), (dx, dy))
            img_ids = [d.map_id for d in enabled_maps]
            self.__prog_of_image_save = MapProgressRec(img_area, img_ids)
            self.__setMapProgress(0, is_immediate=True)

            def update_prog_cb(tile_info):
                prog = self.__prog_of_image_save
                if prog.update(tile_info):
                    self.__setMapProgress(prog.rate, is_immediate=True)

            #get and save
            map, attr = self.__map_ctrl.getMap(dx, dy, geo=sel_geo, level=out_level, req_type="sync", cb=update_prog_cb)
            map.save(fpath, format='png')

            #notify the saving is  done
            self.__setMapProgress(1, is_immediate=True)
            messagebox.showwarning('', 'The saving is OK!')

        except AreaSizeTooLarge as ex:
            messagebox.showwarning(str(ex), 'Please zoom out or resize the window to enlarge the map')
        finally:
            self.__canvas_sel_area = None

    def onGpxSave(self):
        def to_ask(init_dir):
            return filedialog.asksaveasfilename(
                defaultextension=".gpx",
                filetypes=(("GPS Excahnge Format", ".gpx"), ("All Files", "*.*")),
                initialdir=init_dir)
        fpath = self.withPreferredDir(to_ask)
        if not fpath:
            return False

        #gen gpx faile
        doc = GpsDocument()
        for gpx in self.__map_ctrl.gpx_layers:
            doc.merge(gpx)

        #save
        doc.save(fpath)
        self.__alter_time = None

        return True

    #}} Right click actions

    def setAlter(self, alter):
        logging.debug(alter + " is altered")
        self.__alter_time = datetime.now()
        self.resetMap(force=alter)

    def onClickMotion(self, event):
        if self.isSavingImage():
            return

        if self.__left_click_pos:
            label = event.widget

            #print("change from ", self.__left_click_pos, " to " , (event.x, event.y))
            (last_x, last_y) = self.__left_click_pos
            self.__map_ctrl.shiftGeoPixel(last_x - event.x, last_y - event.y)
            self.setMapInfo()
            self.resetMap()

            self.__left_click_pos = (event.x, event.y)

    def getGeoPointAt(self, px, py):
        px += self.__map_ctrl.px
        py += self.__map_ctrl.py
        return GeoPoint(px=px, py=py, level=self.__map_ctrl.level)

    def onMotion(self, event):
        if self.isSavingImage():
            return
        geo = self.getGeoPointAt(event.x, event.y)

        #draw point
        curr_wpt = self.__map_ctrl.getWptAround(geo)
        prev_wpt = self.__focused_wpt
        if curr_wpt != prev_wpt:
            self.highlightWpt(curr_wpt, prev_wpt)

        #rec
        self.__focused_geo = geo
        self.__focused_wpt = curr_wpt

    def highlightWpt(self, wpt, un_wpt=None):
        if wpt == un_wpt:
            return

        if wpt is None and un_wpt is not None:
            #print('unhighlight wpt', un_wpt.name)
            self.restore()

        #draw wpt
        if wpt is not None:
            #print('highlight wpt', wpt.name)
            map = self.__map.copy()
            self.__map_ctrl.drawWayPoint(map, self.__map_attr, wpt, 'red', 'white')
            self.__setMap(map)

    def highlightTrk(self, pts):
        if pts is None or len(pts) == 0:
            return
        map = self.__map.copy()
        self.__map_ctrl.drawTrkPoint(map, self.__map_attr, pts, 'orange', 'black', width=8)
        self.__setMap(map)

    def onWptDeleted(self, wpt=None, prompt=True):
        if prompt:
            if not messagebox.askyesno('Delete Waypoint', "Delete the Waypoint?"):
                return False

        if wpt is None:
            wpt = self.__focused_wpt
            self.__focused_wpt = None

        self.__map_ctrl.deleteWpt(wpt)
        self.setAlter('wpt')
        return True

    def onClickUp(self, event, flag):
        if flag == 'left':
            self.__left_click_pos = None

    def onResize(self, e):
        disp = self.disp_canvas
        if e.widget == disp:
            if not hasattr(disp, 'image'):  #init
                self.__pref_geo = self.__getPrefGeoPt()
                geo = self.__pref_geo if self.__pref_geo is not None else self.__some_geo
                self.setMapInfo(geo)
                self.resetMap(geo)
            elif e.width != disp.image.width() or e.height != disp.image.height():
                self.setMapInfo()
                self.resetMap()
            # raise AS, if any
            if self.isSavingImage():
                self.disp_canvas.tag_raise('AS')

    def __runMapUpdater(self):
        progress_rate = 0

        while not self.__is_closed:
            #check per second
            time.sleep(1)
            if self.__is_closed:
                break  #exit

            #detect
            should_update_map = False
            should_update_status = False
            update_ts = datetime.now() - conf.MAP_UPDATE_PERIOD
            with self.__map_req_lock:
                if self.__map_req_time <= update_ts:
                    if progress_rate != self.__prog_of_reset_map.rate:
                        progress_rate = self.__prog_of_reset_map.rate
                        should_update_status = True

                    if self.__map_has_update:
                        should_update_map = True

            if should_update_status:
                self.__setMapProgress(progress_rate)

            if should_update_map:
                logging.debug("map should auto update")
                try:
                    self.resetMap()
                except Exception as ex:
                    showmsg("Auto reset map error: ", str(ex))

    def __notifyTileReady(self, tile_info):
        logging.debug("tile (%s, %d, %d, %d) is ready" % tile_info)

        with self.__map_req_lock:
            if self.__prog_of_reset_map.update(tile_info): #need the lock due to access to data members
                self.__map_has_update = True
                logging.debug("has update")

    def resetMap(self, geo=None, w=None, h=None, force=None):
        if w is None: w = self.disp_canvas.winfo_width()
        if h is None: h = self.disp_canvas.winfo_height()

        level = self.__map_ctrl.level
        if geo is not None:
            self.__map_ctrl.geo = geo.addPixel(int(-w/2), int(-h/2), level)
        ref_geo = self.__map_ctrl.geo

        #prepare map progress info
        map_area = TileArea(level, ref_geo.pixel(level), (w, h))
        map_ids = [d.map_id for d in self.__map_descs if d.enabled]

        #request map
        now = datetime.now()
        with self.__map_req_lock:
            #for auto refresh
            self.__map_has_update = False #reset flag
            self.__map_req_time = now
            self.__map, self.__map_attr = self.__map_ctrl.getMap(w, h, force, cb=self.__notifyTileReady)  #buffer the image
            self.__prog_of_reset_map = MapProgressRec(map_area, map_ids,
                    needed_count = self.__map_attr.fail_tiles)

        #set map
        self.__setMap(self.__map)

    def restore(self):
        self.__setMap(self.__map)

    def __setMap(self, img):
        pimg = ImageTk.PhotoImage(img)
        self.disp_canvas.image = pimg #keep a ref
        
        #it seems the view is more smoothly if DISABLED...update...NORMAL
        #any better idea?
        self.disp_canvas['state'] = 'disabled'
        tmp = self.__canvas_map
        self.__canvas_map = self.disp_canvas.create_image((0,0), image=pimg, anchor='nw')
        if tmp:
            self.disp_canvas.tag_lower(tmp)
            self.disp_canvas.delete(tmp)
        self.disp_canvas['state'] = 'normal'

class MapAgent:
    #properties from map_desc
    @property
    def map_id(self): return self.__map_desc.map_id
    @property
    def map_title(self): return self.__map_desc.map_title
    @property
    def level_min(self): return self.__map_desc.level_min
    @property
    def level_max(self): return self.__map_desc.level_max
    @property
    def url_template(self): return self.__map_desc.url_template
    @property
    def lower_corner(self): return self.__map_desc.lower_corner
    @property
    def upper_corner(self): return self.__map_desc.upper_corner
    @property
    def tile_format(self): return self.__map_desc.tile_format
    @property
    def alpha(self): return self.__map_desc.alpha
    @property
    def enabled(self): return self.__map_desc.enabled

    def __init__(self, map_desc, tile_cache_dir):
        self.__map_desc = map_desc
        self.__cache_basemap = None
        self.__cache_attr = None
        self.__extra_p = 0
        self.__tile_agent = TileAgent(map_desc, tile_cache_dir, auto_start=True)

    def close(self):
        self.__tile_agent.close()

    def pause(self):
        self.__tile_agent.pause()

    def resume(self):
        self.__tile_agent.resume()

    def isRunning(self):
        return self.__tile_agent.state == TileAgent.ST_RUN

    #todo: refine this to reduce repeat
    def __isCacheValid(self, req_attr):
        cache_map = self.__cache_basemap
        cache_attr = self.__cache_attr
        return cache_map is not None and \
               cache_attr is not None and \
               not cache_attr.fail_tiles and \
               cache_attr.containsImgae(req_attr)

    # @cb is used to notify some tile is ready.
    # sync cb is handled by genMap, and async cb by getTile
    # which call cb(tile_info), tile_info = (map_id, level, x, y)
    def genMap(self, req_attr, req_type, cb=None):
        if self.__isCacheValid(req_attr):
            return (self.__cache_basemap, self.__cache_attr)

        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  gen base map")
        level = min(max(self.level_min, req_attr.level), self.level_max)

        if req_attr.level == level:
            tile_map = self.__genTileMap(req_attr, self.__extra_p, req_type, cb)
        else:
            #get approx map
            aprx_attr = req_attr.zoomToLevel(level)
            extra_p = self.__extra_p * 2**(level - req_attr.level)
            aprx_map, aprx_attr = self.__genTileMap(aprx_attr, extra_p, req_type, cb)

            #zoom to request level
            if aprx_map is not None:
                tile_map = self.__genZoomMap(aprx_map, aprx_attr, req_attr.level)
            else:
                tile_map = (None, aprx_attr.zoomToLevel(req_attr.level))

        #cache
        self.__cache_basemap, self.__cache_attr = tile_map
        return tile_map

    def __genZoomMap(self, map, attr, level):
        s = level - attr.level
        if s == 0:
            return (map, attr)
        elif s > 0:
            w = (attr.right_px - attr.left_px) << s
            h = (attr.low_py - attr.up_py) << s
        else:
            w = (attr.right_px - attr.left_px) >> (-s)
            h = (attr.low_py - attr.up_py) >> (-s)

        #Image.NEAREST, Image.BILINEAR, Image.BICUBIC, or Image.LANCZOS 
        zoom_img = map.resize((w,h), Image.BILINEAR)

        #the attr of resized image
        zoom_attr = attr.zoomToLevel(level)

        return (zoom_img, zoom_attr)

    #looks the method is not needed
    def __tileInAttr(self, level, x, y, attr):
        #handle psudo level beyond min level or max level
        crop_level = min(max(self.level_min, attr.level), self.level_max)
        if crop_level != attr.level:
            attr = attr.zoomToLevel(crop_level)

        #check range
        if level == attr.level:
            t_left, t_upper, t_right, t_lower = attr.boundTiles(self.__extra_p)
            return (t_left <= x and x <= t_right) and (t_upper <= y and y <= t_lower)
        return False

    @classmethod
    def isCompleteColor(cls, img):
        extrema = img.getextrema()
        #channels = min(len(extrema), 3)
        if img.mode == "P":
            _min, _max = extrema
            return _min == _max
        else:
            for _min, _max in extrema:
                if _min != _max:
                    return False
        return True

    def __notifyTileReady(self, level, x, y, cb):
        try:
            if cb is not None:
                cb(level, x, y)
        except Exception as ex:
            logging.error("invoke cb for tile ready error: %s" % (self.map_id, str(ex)))

    '''
    def __tileIsReady(self, level, x, y, map_attr, cb):
        logging.info("[%s] tile(%d,%d,%d) is ready" % (self.map_id, level, x, y))
        cb(self.map_id, map_attr)
    '''

    #could return None map
    def __genTileMap(self, map_attr, extra_p, req_type, cb=None):
        async_cb = cb if cb is not None and req_type == "async" else None
        #if cb is not None and req_type == "async":
        #    async_cb = lambda level, x, y: self.__tileIsReady(level, x, y, map_attr, cb) 

        #get tile x, y.
        t_left, t_upper, t_right, t_lower = map_attr.boundTiles(extra_p)
        tx_num = t_right - t_left +1
        ty_num = t_lower - t_upper +1

        #gen image
        logging.debug("pasting tile...")

        disp_map = None
        fail_tiles = 0

        for x in range(tx_num):
            for y in range(ty_num):
                tile = self.__tile_agent.getTile(map_attr.level, t_left +x, t_upper +y, req_type, async_cb)

                if tile is None or tile.is_fake:
                    fail_tiles += 1

                if tile is not None:
                    if disp_map is None:
                        disp_map = Image.new("RGBA", to_pixel(tx_num, ty_num), 'lightgray')
                    disp_map.paste(tile, to_pixel(x, y))

                if req_type == "sync" and cb is not None:
                    tile_info = (self.map_id, map_attr.level, t_left + x, t_upper +y)
                    cb(tile_info)

        logging.debug("pasting tile...done")

        #reset map_attr
        left, top = to_pixel(t_left, t_upper)
        right, bottom = to_pixel(t_right+1, t_lower+1)
        disp_attr = MapAttr(map_attr.level, left, top, right-1, bottom-1, fail_tiles)

        return  (disp_map, disp_attr)

#todo: what is the class's purpose?, suggest to reconsider
class MapController:

    #{{ properties
    @property
    def geo(self): return self.__geo
    @geo.setter
    def geo(self, v): self.__geo = v

    @property
    def lat(self): return self.__geo.lat

    @property
    def lon(self): return self.__geo.lon

    @property
    def px(self): return self.__geo.px(self.__level)

    @property
    def py(self): return self.__geo.py(self.__level)

    @property
    def level(self): return self.__level
    @level.setter
    def level(self, v): self.__level = v

    @property
    def gpx_layers(self):
        return self.__gpx_layers

    @property
    def is_hide_text(self): return self.__is_hide_text

    @is_hide_text.setter
    def is_hide_text(self, v): self.__is_hide_text = v

    def __init__(self, parent):
        #def settings
        self.__parent = parent
        self.__map_descs = None
        self.__map_agents = {}
        self.__geo = GeoPoint(lon=121.334754, lat=24.987969)  #default location
        self.__level = 14

        #image
        self.__cache_gpsmap = None
        self.__cache_attr = None
        self.__font = conf.IMG_FONT
        self.__is_hide_text = False

        #layer
        self.__mark_wpt = None
        self.__pseudo_gpx = GpsDocument()  #to hold waypoints which not read from gpx
        self.__gpx_layers = [self.__pseudo_gpx]

    def close(self):
        for agent in self.__map_agents.values():
            agent.close()

    def configMap(self, descs):
        #config agents
        for desc in descs:
            agent = self.__map_agents.get(desc)
            if agent is not None:
                if desc.enabled:
                    agent.resume()
                else:
                    agent.pause()
            elif desc.enabled:
                self.__map_agents[desc] = MapAgent(desc, conf.MAPCACHE_DIR)

        #config desc
        self.__map_descs = descs
        self.__cache_gpsmap = None
        self.__cache_attr = None

    #Are there any map contains the point?
    def mapContainsPt(self, geo):
        for desc in self.__map_descs:
            if desc.enabled:
                min_lon, min_lat = desc.lower_corner
                max_lon, max_lat = desc.upper_corner
                if (min_lat <= geo.lat and geo.lat <= max_lat) and (min_lon <= geo.lon and geo.lon <= max_lon):
                    return True
        return False

    def shiftGeoPixel(self, px, py):
        self.geo = self.geo.addPixel(int(px), int(py), self.__level)

    def addGpxLayer(self, gpx):
        self.__gpx_layers.append(gpx)

    def addWpt(self, wpt):
        self.__pseudo_gpx.addWpt(wpt)

    def addMark(self, geo):
        wpt = WayPoint(geo.lat, geo.lon)
        wpt.sym = 'crosshair'
        self.__mark_wpt = wpt

    def deleteWpt(self, wpt):
        for gpx in self.__gpx_layers:
            if wpt in gpx.way_points:
                gpx.way_points.remove(wpt)

    def getAllWpts(self):
        wpts = []
        for gpx in self.__gpx_layers:
            for wpt in gpx.way_points:
                wpts.append(wpt)
        return wpts

    def getAllTrks(self):
        trks = []
        for gpx in self.__gpx_layers:
            for trk in gpx.tracks:
                trks.append(trk)
        return trks

    def getWptAround(self, geo):
        px, py = geo.px(self.level), geo.py(self.level)
        r = int(conf.ICON_SIZE/2)
        for wpt in self.getAllWpts():
            wpx, wpy = wpt.pixel(self.level)
            if abs(px-wpx) < r and abs(py-wpy) < r:
                return wpt
        return None

    def getMap(self, width, height, force=None, geo=None, level=None, req_type="async", cb=None):
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "gen map: begin")
        if geo is None: geo = self.geo
        if level is None: level = self.level
        px, py = geo.px(level), geo.py(level)

        #The image attributes with which we want to create a image compatible.
        req_attr = MapAttr(level, px, py, px+width, py+height, 0)
        map, attr = self.__genGpsMap(req_attr, force, req_type, cb)

        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  crop map")
        map = self.__genCropMap(map, attr, req_attr)
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  draw coord")
        self.__drawCoordValue(map, req_attr)

        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "gen map: done")
        req_attr.fail_tiles = attr.fail_tiles
        return map, req_attr

    def __isCacheValid(self, cache_map, req_attr):
        cache_attr = self.__cache_attr
        return cache_map and \
               cache_attr and \
               cache_attr.fail_tiles == 0 and \
               cache_attr.containsImgae(req_attr)

    @classmethod
    def __combinePixel(cls, p, q, alpha):
        beta = 255 - alpha
        return ((p[0]*beta + q[0]*alpha) >> 8,
                (p[1]*beta + q[1]*alpha) >> 8,
                (p[2]*beta + q[2]*alpha) >> 8,
                255)

    @classmethod
    #tune alpha channel by @alpha, which between 0.0~1.0
    def tunealpha(cls, img, alpha):
        logging.debug("prepare to tune alpha...")
        if img.mode != "RGBA":
            logging.warning("not support mode '%s' to tune alpha" % (img.mode,))
            return

        alpha = int(alpha*256)

        #optimize
        min_a, max_a = img.getextrema()[3];
        if alpha == 255 or max_a == 0:
            return img
        if alpha == 0 or min_a == 255:
            img = img.copy()
            img.putalpha(alpha)
            return img

        logging.debug("start to tune alpha...")

        bands = img.split()

        #tune alpha channel
        #todo: for improve, may use numpy module
        data = bands[3].load()
        w, h = img.size
        for x in range(w):
            for y in range(h):
                p = data[x,y]
                if p:
                    data[x,y] = (p * alpha) >> 8

        result = Image.merge("RGBA", bands)

        logging.debug("end to tune alpha...")
        return result

    #alpha between 0.0~1.0
    @classmethod
    def combineMap(cls, basemap, map, alpha):
        if imageIsTransparent(map):
            map = cls.tunealpha(map, alpha)
            return Image.alpha_composite(basemap, map)
        else:
            return Image.blend(basemap, map, alpha)

    def __getMaps(self, req_attr, req_type, cb=None):
        maps = []
        for desc in self.__map_descs:
            if not desc.enabled:
                #logging.debug("map " + desc.map_id + " is not enabled")
                continue

            if not desc.alpha:
                logging.debug("map " + desc.map_id + " has zero alpha")
                continue

            #get
            agent = self.__map_agents.get(desc)
            if agent is None or not agent.isRunning():
                logging.error('map agent has Bad Configuration.')
                continue

            #create map
            map, attr = agent.genMap(req_attr, req_type, cb)
            maps.append((map, attr, desc.alpha))

            #logging.debug('The map %s is transparent: %s' % (desc.map_id, "NA" if map is None else imageIsTransparent(map)))
        return maps

    def __genBaseMap(self, req_attr, req_type, cb=None):
        maps = self.__getMaps(req_attr, req_type, cb)

        #create attr
        baseattr = None
        if not maps:
            baseattr = req_attr.clone() 
            baseattr.fail_tiles = 0
        else:
            attrs = [attr for map, attr, alpha in maps]
            baseattr = MapAttr.getMaxOverlapAttr(attrs, fail_count_method="sum")

        #create basemap
        basemap = Image.new("RGBA", baseattr.size, "white")
        for map, attr, alpha in reversed(maps):
            if map is None:
                continue

            map = self.__genCropMap(map, attr, baseattr)
            basemap = self.combineMap(basemap, map, alpha)

        return basemap, baseattr

    def __genGpsMap(self, req_attr, force=None, req_type="async", cb=None):
        if force not in ('all', 'gps', 'trk', 'wpt') and self.__isCacheValid(self.__cache_gpsmap, req_attr):
            #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  get gps map from cache")
            return (self.__cache_gpsmap, self.__cache_attr)

        basemap, attr = self.__genBaseMap(req_attr, req_type, cb)

        #create gpsmap, also cache
        self.__cache_gpsmap = basemap.copy()
        self.__cache_attr = attr
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  draw trk")
        self.__drawTrk(self.__cache_gpsmap, attr)
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  draw wpt")
        self.__drawWpt(self.__cache_gpsmap, attr)

        return self.__cache_gpsmap, self.__cache_attr

    def __drawTrk(self, map, map_attr):
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "draw gpx...")
        if not self.__gpx_layers:
            return

        with DrawGuard(map) as draw:
            for gpx in self.__gpx_layers:
                #draw tracks
                #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "draw gpx...")
                for trk in gpx.tracks:
                    if self.isTrackInImage(trk, map_attr):
                        self.drawTrkPoint(map, map_attr, trk, trk.color, draw=draw)

    def drawTrkPoint(self, map, map_attr, pts, color, bg_color=None, draw=None, width=3):
        if pts is None or len(pts) == 0:
            return

        #set to default color if invalid
        if not (color and color.lower() in ImageColor.colormap):
            color = 'darkmagenta'

        if bg_color and bg_color.lower() not in ImageColor.colormap:
            bg_color = 'orange'

        bg_width = width + 4
        _draw = draw if draw is not None else ImageDraw.Draw(map)
        try:
            if len(pts) == 1:
                #print('draw trk point')
                (px, py) = pts[0].pixel(map_attr.level)
                px -= map_attr.left_px
                py -= map_attr.up_py

                #r = int(bg_width/2)
                #_draw.ellipse((px-r, py-r, px+r, py+r), fill=bg_color)

                r = int(width/2)
                _draw.ellipse((px-r, py-r, px+r, py+r), fill=color, outline=bg_color)
            else:
                #print('draw trk seg')
                xy = []
                for pt in pts:
                    (px, py) = pt.pixel(map_attr.level)
                    xy.append(px - map_attr.left_px)
                    xy.append(py - map_attr.up_py)

                if bg_color is not None:
                    _draw.line(xy, fill=bg_color, width=width+4)

                _draw.line(xy, fill=color, width=width)
        finally:
            if draw is None:
                del _draw


    #disable for now, because the algo will be broken if two pt across the image
    def isTrackInImage(self, trk, map_attr):
        return True
        #if some track point is in disp
        for pt in trk:
            (px, py) = pt.pixel(map_attr.level)
            if map_attr.containsPoint(px, py):
                return True
        return False

    #draw pic as waypoint
    def __drawWpt(self, map, map_attr):
        wpts = self.getAllWpts()  #gpx's wpt + pic's wpt
        if self.__mark_wpt:
            wpts.append(self.__mark_wpt)
        if len(wpts) == 0:
            return

        with DrawGuard(map) as draw:
            for wpt in wpts:
                (px, py) = wpt.pixel(map_attr.level)
                self.drawWayPoint(map, map_attr, wpt, "black", draw=draw)

    @classmethod
    def pasteTransparently(cls, img, img2, pos=(0,0), errmsg=None):
        if img2.mode == 'RGBA':
            img.paste(img2, pos, img2)
        elif img2.mode == 'LA' or (img2.mode == 'P' and 'transparency' in img2.info):
            mask = img2.convert('RGBA')
            img.paste(img2, pos, mask)
        else:
            if errmsg: 
                logging.warning(errmsg)
            img.paste(img2, pos)

    def drawWayPoint(self, map, map_attr, wpt, txt_color, bg_color=None, draw=None):
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "draw wpt'", wpt.name, "'")
        #check range
        (px, py) = wpt.pixel(map_attr.level)
        if not map_attr.containsPoint(px, py):
            return

        px -= map_attr.left_px
        py -= map_attr.up_py
        adj = int(conf.ICON_SIZE/2)

        #get draw
        _draw = draw if draw is not None else ImageDraw.Draw(map)
        try:
            if bg_color is not None:
                r = ceil(conf.ICON_SIZE/sqrt(2))
                _draw.ellipse((px-r, py-r, px+r, py+r), fill=bg_color, outline='gray')

            #paste icon
            if wpt.sym is not None:
                icon = sym.getIcon(wpt.sym)
                if icon is not None:
                    self.pasteTransparently(map, icon, (px-adj, py-adj),
                            errmsg="Warning: Icon for '%s' with mode %s is not ransparency" % (wpt.sym, icon.mode))

            #draw text
            if not self.__is_hide_text:
                txt = wpt.name
                font = self.__font
                px, py = px +adj, py -adj  #adjust position for aligning icon
                _draw.text((px+1, py+1), txt, fill="white", font=font)
                _draw.text((px-1, py-1), txt, fill="white", font=font)
                _draw.text((px, py), txt, fill=txt_color, font=font)
        finally:
            if draw is None:
                del _draw


    def __genCropMap(self, map, src_attr, dst_attr):
        left  = dst_attr.left_px - src_attr.left_px
        up    = dst_attr.up_py - src_attr.up_py
        right = dst_attr.right_px - src_attr.left_px
        low   = dst_attr.low_py - src_attr.up_py
        img2 = map.crop((left, up, right, low))
        return img2

    @classmethod
    def __getCoordByPixel(cls, px, py, level, coord_sys):
        geo = GeoPoint(px=px, py=py, level=level)
        if coord_sys == "TWD67":
            return (geo.twd67_x, geo.twd67_y)
        if coord_sys == "TWD97":
            return (geo.twd97_x, geo.twd97_y)
        else:
            raise ValueError("Unknown coord system '%s'" % (coord,))

    @classmethod
    def __getPixelByCoord(cls, x, y, level, coord_sys):
        geo = None
        if coord_sys == "TWD67":
            geo = GeoPoint(twd67_x=x, twd67_y=y)
        elif coord_sys == "TWD97":
            geo = GeoPoint(twd97_x=x, twd97_y=y)
        else:
            raise ValueError("Unknown coord system '%s'" % (coord,))
        return geo.pixel(level)

    def __drawCoordValue(self, map, attr):

        if attr.level <= 12:  #too crowded to show
            return

        coord_sys = [desc.coord_sys for desc in self.__map_descs if desc.enabled and desc.coord_sys in ("TWD67", "TWD97")]
        if not coord_sys:
            return
        coord_sys = coord_sys[0]

        #set draw
        py_shift = 20
        font = self.__font

        with DrawGuard(map) as draw:
            #get xy of TM2
            (left_x, up_y) = self.__getCoordByPixel(attr.left_px, attr.up_py, attr.level, coord_sys)
            (right_x, low_y) = self.__getCoordByPixel(attr.right_px, attr.low_py, attr.level, coord_sys)

            #draw coord x per KM
            for x in range(ceil(left_x/1000), floor(right_x/1000) +1):
                #print("tm: ", x)
                (px, py) = self.__getPixelByCoord(x*1000, low_y, attr.level, coord_sys)
                px -= attr.left_px
                py -= attr.up_py
                draw.text((px, py - py_shift), str(x), fill="black", font=font)

            #draw coord y per KM
            for y in range(ceil(low_y/1000), floor(up_y/1000) +1):
                #print("tm: ", y)
                (px, py) = self.__getPixelByCoord(left_x, y*1000, attr.level, coord_sys)
                px -= attr.left_px
                py -= attr.up_py
                draw.text((px, py -py_shift), str(y), fill="black", font=font)

class MapProgressRec:
    @property
    #complete rate of tiles
    def rate(self):
        return 1 if not self.__total else self.__count / self.__total

    def __init__(self, map_area, map_ids, init_count=0, needed_count=-1):
        self.__map_area = map_area
        self.__map_ids = map_ids
        self.__total = self.__getTotalTiles()
        self.__count = max(0, self.__total - needed_count) if needed_count >= 0 else init_count
        self.__added_tiles = set()

    def __getTotalTiles(self):
        left, top, right, bottom = self.__map_area.boundTiles()
        ntiles = (right - left + 1) * (bottom - top + 1)
        nmaps = len(self.__map_ids)
        return nmaps * ntiles

    def __genKey(self, tile_info):
        return "%s_%d_%d_%d" % tile_info

    def update(self, tile_info):
        map_id, level, x, y = tile_info

        if map_id not in self.__map_ids:
            return False

        key = self.__genKey(tile_info)
        if key in self.__added_tiles:  #already added
            return False

        self.__added_tiles.add(key)
        tile_area = TileArea.fromTile(level, x, y)
        if self.__map_area.overlay(tile_area) is not None:
            self.__count += 1
            return True

        return False

class TileArea:
    @property
    def level(self): return self.__level

    @property
    def pos(self): return self.__pos

    @property
    def size(self): return self.__size

    @property
    def area(self):
        w, h = self.__size
        return w * h

    def __init__(self, level, pos, size):
        self.__level = level
        self.__pos = pos
        self.__size = size

    def __str__(self):
        x, y = self.pos
        w, h = self.size
        return "TileArea{level=%d, pos=(%d, %d), size=(%d, %d)}" % (self.level, x, y, w, h)

    # return overlayed area or None
    def overlay(self, rhs):
        if self.level != rhs.level:
           return None

        x1, y1 = self.pos
        w1, h1 = self.size

        x2, y2 = rhs.pos
        w2, h2 = rhs.size

        x_overlay = self.lineOverlay(x1, w1, x2, w2)
        if x_overlay is None:
            return None

        y_overlay = self.lineOverlay(y1, h1, y2, h2)
        if y_overlay is None:
            return None

        x, w = x_overlay
        y, h = y_overlay
        return TileArea(self.level, (x, y), (w, h))

    def boundTiles(self, extra_p=0):
        x, y = self.pos
        w, h = self.size
        t_left, t_upper  = to_tile(x - extra_p, y - extra_p)
        t_right, t_lower = to_tile(x + w + extra_p, y + h + extra_p)
        return (t_left, t_upper, t_right, t_lower)

    @classmethod
    def lineOverlay(cls, x1, w1, x2, w2):
        if x1 <= x2 and x2 < (x1 + w1):
            x = x2
        elif x2 <= x1 and x1 < (x2 + w2):
            x = x1
        else:
            return None

        w = min(x1 + w1, x2 + w2) - x
        return x, w

    @classmethod
    def fromTile(cls, level, x, y):
        pos = to_pixel(x, y)
        size = to_pixel(1, 1)
        return TileArea(level, pos, size)


#record image atrr
class MapAttr:
    @property
    def size(self):
        return (self.right_px - self.left_px, self.low_py - self.up_py)

    def __init__(self, level, left_px, up_py, right_px, low_py, fail_tiles=0):
        #self.img = None
        self.level = level
        self.left_px = left_px
        self.up_py = up_py
        self.right_px = right_px
        self.low_py = low_py
        self.fail_tiles = fail_tiles

    def clone(self):
        return MapAttr(self.level, self.left_px, self.up_py, self.right_px, self.low_py, self.fail_tiles)

    def containsImgae(self, attr):
        if self.level == attr.level and \
                self.left_px <= attr.left_px and self.up_py <= attr.up_py and \
                self.right_px >= attr.right_px and self.low_py >= attr.low_py:
            return True
        return False

    def containsPoint(self, px, py):
        return self.left_px <= px and self.up_py <= py and px <= self.right_px and py <= self.low_py

    #def isBoxInImage(self, px_left, py_up, px_right, py_low, map_attr):
        #return self.isPointInImage(px_left, py_up) or self.isPointInImage(px_left, py_low) or \
              #self.isPointInImage(px_right, py_up) or self.isPointInImage(px_right, py_low)

    def zoomToLevel(self, level):
        if level > self.level:
            s = level - self.level
            return MapAttr(level, self.left_px << s, self.up_py << s, self.right_px << s, self.low_py << s, self.fail_tiles)
        elif self.level > level:
            s = self.level - level
            return MapAttr(level, self.left_px >> s, self.up_py >> s, self.right_px >> s, self.low_py >> s, self.fail_tiles)
        else:
            return self

    def boundTiles(self, extra_p=0):
        t_left, t_upper  = to_tile(self.left_px - extra_p, self.up_py - extra_p)
        t_right, t_lower = to_tile(self.right_px + extra_p, self.low_py  + extra_p)
        return (t_left, t_upper, t_right, t_lower)

    @classmethod
    def getMaxOverlapAttr(cls, attrs, fail_count_method=None):
        if not attrs:
            return None

        res = attrs[0].clone()
        res.fail_tiles = 0

        for attr in attrs:
            if res.level != attr.level:
                raise ValueError('No match map level to compare')

            res.left_px  = max(res.left_px,  attr.left_px)
            res.up_py    = max(res.up_py,    attr.up_py)
            res.right_px = min(res.right_px, attr.right_px)
            res.low_py   = min(res.low_py,   attr.low_py)

            #fail_tiles
            if not fail_count_method:
                continue
            elif fail_count_method == "sum":
                res.fail_tiles += attr.fail_tiles

        return res

class WptBoard(tk.Toplevel):
    @property
    def is_changed(self): return self._is_changed

    def __init__(self, master, wpt_list, wpt=None, alter_handler=None):
        super().__init__(master)

        if wpt_list is None or len(wpt_list) == 0:
            raise ValueError('wpt_list is null or empty')
        if wpt is not None and wpt not in wpt_list:
            raise ValueError('wpt is not in wpt_list')

        self._curr_wpt = None  #only set the variable by setCurrWpt()
        self._wpt_list = wpt_list

        #conf
        self._font = 'Arialuni 12'
        self._bold_font = 'Arialuni 12 bold'
        self._title_name = "Name"
        self._title_pos = "TWD67/TM2"
        self._title_ele = "Elevation"
        self._title_time = "Time"
        self._title_focus = "Focus"
        self._altered_handlers = []
        self._is_changed = False

        if alter_handler is not None:
            addAlteredHandler(alter_handler)

        #board
        self.geometry('+0+0')
        self.protocol('WM_DELETE_WINDOW', lambda: self.onClosed(None))
        self.bind('<Escape>', self.onClosed)
        self.bind('<Shift-Delete>', lambda e: self.onDeleted(e, prompt=False))
        self.bind('<Delete>', lambda e: self.onDeleted(e, prompt=True))

        #focus
        self._var_focus = tk.BooleanVar()
        self._var_focus.trace('w', self.onFocusChanged)

        #wpt name
        self._var_name = tk.StringVar()
        self._var_name.trace('w', self.onNameChanged)

        #set focus
        self.transient(self.master)
        self.focus_set()
        if platform.system() == 'Linux':
            self.withdraw() #ensure update silently
            self.update()   #ensure viewable before grab, 
            self.deiconify() #show
        self.grab_set()

    #def show(self):
        #self.wait_window(self)

    def _hasPicWpt(self):
        for wpt in self._wpt_list:
            if isinstance(wpt, PicDocument):
                return True
        return False

    def _getNextWpt(self):
        sz = len(self._wpt_list)
        if sz == 1:
            return None
        idx = self._wpt_list.index(self._curr_wpt)
        idx += 1 if idx != sz-1 else -1
        return self._wpt_list[idx]

    def addAlteredHandler(self, h):
        self._altered_handlers.append(h)

    def removeAlteredHandler(self, h):
        self._altered_handlers.remove(h)

    def onAltered(self, alter):
        self.master.setAlter(alter)   #hard code fist!!!
        #for handler in self._altered_handlers:
            #handler()
        
    def onClosed(self, e=None):
        #reset or restore map
        self.master.resetMap() if self.is_changed else self.master.restore()
        self.master.focus_set()
        self.destroy()

    def onDeleted(self, e, prompt=True):
        if not self.master.onWptDeleted(self._curr_wpt, prompt):
            return

        self._is_changed = True

        next_wpt = self._getNextWpt()
        self._wpt_list.remove(self._curr_wpt)
        if next_wpt == None:
            self.onClosed()
        else:
            self.setCurrWpt(next_wpt)

    def onNameChanged(self, *args):
        #print('change to', self._var_name.get())
        name = self._var_name.get()
        if self._curr_wpt.name != name:
            self._curr_wpt.name = name
            self._curr_wpt.sym = toSymbol(name)
            self._is_changed = True
            self.showWptIcon(self._curr_wpt)

            self.onAltered('wpt')
            self.highlightWpt(self._curr_wpt)

    def onFocusChanged(self, *args):
        self.highlightWpt(self._curr_wpt)

    def onEditSymRule(self):
        sym.showRule(self)
    
    def highlightWpt(self, wpt):
        #focus
        if self._var_focus.get():
            self.master.resetMap(wpt)

        #highlight the current wpt
        self.master.highlightWpt(wpt)

    def unhighlightWpt(self, wpt):
        self.master.resetMap() if self.is_changed else self.master.restore()

    def showWptIcon(self, wpt):
        pass

    def setCurrWpt(self, wpt):
        pass

class WptSingleBoard(WptBoard):
    def __init__(self, master, wpt_list, wpt=None):
        super().__init__(master, wpt_list, wpt)

        #change buttons
        self.__left_btn = tk.Button(self, text="<<", command=lambda:self.onWptSelected(-1), disabledforeground='gray')
        self.__left_btn.pack(side='left', anchor='w', expand=0, fill='y')
        self.__right_btn = tk.Button(self, text=">>", command=lambda:self.onWptSelected(1), disabledforeground='gray')
        self.__right_btn.pack(side='right', anchor='e', expand=0, fill='y')

        #info
        self.info_frame = self.getInfoFrame()
        self.info_frame.pack(side='bottom', anchor='sw', expand=0, fill='x')

        #image
        self.__img_label = None
        self.__img_sz = (img_w, img_h) = (400, 300)
        if self._hasPicWpt():
            #bd=0: let widget size align image size; set width/height to disable auto resizing
            self.__img_label = tk.Label(self, bg='black', bd=0, width=img_w, height=img_h)
            self.__img_label.pack(side='top', anchor='nw', expand=1, fill='both', padx=0, pady=0)
            self.__img_label.bind('<Configure>', self.onImageResize)

        #set wpt
        if wpt is None:
            wpt = wpt_list[0]
        self.setCurrWpt(wpt)

        #wait
        self.wait_window(self)

    def onImageResize(self, e):
        if hasattr(self.__img_label, 'image'):
            img_w = self.__img_label.image.width()
            img_h = self.__img_label.image.height()
            #print('event: %d, %d; winfo: %d, %d; label: %d, %d; img: %d, %d' % (e.width, e.height, self.__img_label.winfo_width(), self.__img_label.winfo_height(), self.__img_label['width'], self.__img_label['height'], img_w, img_h))
            if e.width < img_w or e.height < img_h or (e.width > img_w and e.height > img_h):
                #print('need to zomm image')
                self.setWptImg(self._curr_wpt)

    def onWptSelected(self, inc):
        idx = self._wpt_list.index(self._curr_wpt) + inc
        if idx >= 0 and idx < len(self._wpt_list):
            self.setCurrWpt(self._wpt_list[idx])

    def getInfoFrame(self):
        font = self._font
        bold_font = self._bold_font

        frame = tk.Frame(self)#, bg='blue')

        row = 0
        #set sym rule
        tk.Button(frame, text="Rule...", font=font, relief='groove', overrelief='ridge', command=self.onEditSymRule).grid(row=row, column=0, sticky='w')
        #wpt icon
        self.__icon_label = tk.Label(frame)
        self.__icon_label.grid(row=row, column=1, sticky='e')
        self.__icon_label.bind('<Button-1>', self.onSymClick)

        #wpt name
        name_entry = tk.Entry(frame, textvariable=self._var_name, font=font)
        name_entry.bind('<Return>', lambda e: self.onWptSelected(1))
        name_entry.grid(row=row, column=2, sticky='w')

        row += 1
        #focus
        tk.Checkbutton(frame, text=self._title_focus, variable=self._var_focus).grid(row=row, column=0, sticky='w')
        #wpt positoin
        tk.Label(frame, text=self._title_pos, font=bold_font).grid(row=row, column=1, sticky='e')
        self._var_pos = tk.StringVar()
        tk.Label(frame, font=font, textvariable=self._var_pos).grid(row=row, column=2, sticky='w')

        row +=1
        #ele
        tk.Label(frame, text=self._title_ele, font=bold_font).grid(row=row, column=1, sticky='e')
        self._var_ele = tk.StringVar()
        tk.Label(frame, font=font, textvariable=self._var_ele).grid(row=row, column=2, sticky='w')

        row +=1
        #time
        tk.Label(frame, text=self._title_time, font=bold_font).grid(row=row, column=1, sticky='e')
        self._var_time = tk.StringVar()
        tk.Label(frame, textvariable=self._var_time, font=font).grid(row=row, column=2, sticky='w')

        return frame

    def onSymClick(self, e):
        wpt = self._curr_wpt
        sym = askSym(self, pos=(e.x_root, e.y_root), init_sym=wpt.sym)

        if sym is not None and sym != wpt.sym:
            wpt.sym = sym
            self._is_changed = True
            self.showWptIcon(wpt)

            #update map
            self.onAltered('wpt')
            self.highlightWpt(wpt)

    def showWptIcon(self, wpt):
        icon = ImageTk.PhotoImage(sym.getIcon(wpt.sym))
        self.__icon_label.image = icon
        self.__icon_label.config(image=icon, text=wpt.sym, compound='right')

    def setWptImg(self, wpt):
        img_w = self.__img_label

        if img_w is None:
            return
        size = self.__img_sz if not hasattr(img_w, 'image') else (img_w.winfo_width(), img_w.winfo_height())
        img = getAspectResize(wpt.img, size) if isinstance(wpt, PicDocument) else getTextImag("(No Pic)", size)
        img = ImageTk.PhotoImage(img)
        img_w.config(image=img)
        img_w.image = img #keep a ref

    def setCurrWpt(self, wpt):
        if self._curr_wpt != wpt:
            self.unhighlightWpt(self._curr_wpt)
            self.highlightWpt(wpt)

        self._curr_wpt = wpt

        #title
        self.title(wpt.name)

        #set imgae
        self.setWptImg(wpt)

        #info
        self.showWptIcon(wpt)
        self._var_name.set(wpt.name)   #this have side effect to set symbol icon
        self._var_pos.set(conf.getPtPosText(wpt))
        self._var_ele.set(conf.getPtEleText(wpt))
        self._var_time.set(conf.getPtTimeText(wpt))

        #button state
        if self._wpt_list is not None:
            idx = self._wpt_list.index(wpt)
            sz = len(self._wpt_list)
            self.__left_btn.config(state=('disabled' if idx == 0 else 'normal'))
            self.__right_btn.config(state=('disabled' if idx == sz-1 else 'normal'))

class WptListBoard(WptBoard):
    def __init__(self, master, wpt_list, wpt=None):
        super().__init__(master, wpt_list, wpt)

        self.__widgets = {}  #wpt: widgets 
        self.__focused_wpt = None
        self.__bg_color = self.cget('bg')
        self.__bg_hl_color = 'lightblue'
        self.init()
                
        #set wpt
        if wpt is not None:
            self.setCurrWpt(wpt)

        #wait
        self.wait_window(self)

    def initWidget(self, w, row, col):
        w.bind('<Double-Button-1>', self.onDoubleClick)
        w.bind('<Motion>', self.onMotion)
        w.grid(row=row, column=col, sticky='news')

    def init(self):
        self.sf = pmw.ScrolledFrame(self, usehullsize = 1, hull_width = 300, hull_height = 600)
        self.sf.pack(fill = 'both', expand = 1)

        frame = self.sf.interior()
        font = self._font
        bfont = self._bold_font

        row = 0
        tk.Label(frame, text=self._title_name, font=bfont).grid(row=row, column=1)
        tk.Label(frame, text=self._title_pos,  font=bfont).grid(row=row, column=2)
        tk.Label(frame, text=self._title_ele,  font=bfont).grid(row=row, column=3)
        tk.Label(frame, text=self._title_time, font=bfont).grid(row=row, column=4)

        for w in self._wpt_list:
            row += 1

            #icon
            icon = ImageTk.PhotoImage(sym.getIcon(w.sym))
            icon_label = tk.Label(frame, image=icon, anchor='e')
            icon_label.image=icon
            self.initWidget(icon_label, row, 0)

            name_label = tk.Label(frame, text=w.name, font=font, anchor='w')
            self.initWidget(name_label, row, 1)

            pos_txt = conf.getPtPosText(w, fmt='%.3f\n%.3f')
            pos_label = tk.Label(frame, text=pos_txt, font=font)
            self.initWidget(pos_label, row, 2)

            ele_label = tk.Label(frame, text=conf.getPtEleText(w), font=font)
            self.initWidget(ele_label, row, 3)

            time_label = tk.Label(frame, text=conf.getPtTimeText(w), font=font)
            self.initWidget(time_label, row, 4)

            #save
            self.__widgets[w] = (
                    icon_label,
                    name_label,
                    pos_label,
                    ele_label,
                    time_label
            )

    def onDoubleClick(self, e):
        wpt = self.getWptOfWidget(e.widget)
        self.master.resetMap(wpt) #focuse
        self.highlightWpt(wpt) #highlight

    def getWptOfWidget(self, w):
        for wpt, widgets in self.__widgets.items():
            if w in widgets:
                return wpt
        return None

    def onMotion(self, e):
        prev_wpt = self.__focused_wpt
        curr_wpt = self.getWptOfWidget(e.widget)

        #highligt/unhighlight
        if prev_wpt != curr_wpt:
            if prev_wpt is not None:
                self.unhighlightWpt(prev_wpt)
            if curr_wpt is not None:
                self.highlightWpt(curr_wpt)
                
        #rec
        self.__focused_wpt = curr_wpt

    #override
    def highlightWpt(self, wpt, is_focus=False):
        for w in self.__widgets[wpt]:
            w.config(bg=self.__bg_hl_color)
        super().highlightWpt(wpt)

    #override
    def unhighlightWpt(self, wpt):
        for w in self.__widgets[wpt]:
            w.config(bg=self.__bg_color)
        #super().unhighlightWpt(wpt)  #can skip, deu to followed by highlight

    #override
    def showWptIcon(self, wpt):
        pass

    #override
    def setCurrWpt(self, wpt):
        self._curr_wpt = wpt



class TrkSingleBoard(tk.Toplevel):
    @property
    def is_changed(self): return self._is_changed

    def __init__(self, master, trk_list, trk=None):
        super().__init__(master)

        if trk is not None and trk not in trk_list:
            raise ValueError('trk is not in trk_list')

        self._curr_trk = None
        self._trk_list = trk_list
        self._altered_handlers = []
        self._is_changed = False
        self._var_focus = tk.BooleanVar()
        self._var_focus.trace('w', self.onFocus)

        #board
        self.geometry('+0+0')
        self.bind('<Escape>', self.onClosed)
        self.protocol('WM_DELETE_WINDOW', lambda: self.onClosed(None))

        #change buttons
        self.__left_btn = tk.Button(self, text="<<", command=lambda:self.onSelected(-1), disabledforeground='gray')
        self.__left_btn.pack(side='left', anchor='w', expand=0, fill='y')
        self.__right_btn = tk.Button(self, text=">>", command=lambda:self.onSelected(1), disabledforeground='gray')
        self.__right_btn.pack(side='right', anchor='e', expand=0, fill='y')

        #info
        self.info_frame = self.getInfoFrame()
        self.info_frame.pack(side='top', anchor='nw', expand=0, fill='x')

        tk.Checkbutton(self, text='Focus Track point', anchor='e', variable=self._var_focus).pack(side='bottom', expand=0, fill='x')

        #pt list
        self.pt_list = tk.Listbox(self)
        pt_scroll = tk.Scrollbar(self, orient='vertical')
        pt_scroll.config(command=self.pt_list.yview)
        pt_scroll.pack(side='right', fill='y')
        self.pt_list.config(selectmode='extended', yscrollcommand=pt_scroll.set, width=50, height=30)
        self.pt_list.pack(side='left', anchor='nw', expand=1, fill='both')
        self.pt_list.bind('<ButtonRelease-1>', self.onPtSelected)
        self.pt_list.bind('<KeyRelease-Up>', self.onPtSelected)
        self.pt_list.bind('<KeyRelease-Down>', self.onPtSelected)
        self.pt_list.bind('<Delete>', self.onPtDeleted)

        #set trk
        if trk is not None:
            self.setCurrTrk(trk)
        elif len(trk_list) > 0:
            self.setCurrTrk(trk_list[0])

        #set focus
        self.transient(self.master)
        self.focus_set()
        if platform.system() == 'Linux':
            self.withdraw() #ensure update silently
            self.update()   #ensure viewable before grab, 
            self.deiconify() #show
        self.grab_set()

    #def show(self):
        #self.wait_window(self)

    def getInfoFrame(self):
        font = 'Arialuni 12'
        bold_font = 'Arialuni 12 bold'

        frame = tk.Frame(self)#, bg='blue')

        #trk name
        tk.Label(frame, text="Track", font=bold_font).grid(row=0, column=0, sticky='e')
        self._var_name = tk.StringVar()
        self._var_name.trace('w', self.onNameChanged)
        name_entry = tk.Entry(frame, textvariable=self._var_name, font=font)
        name_entry.bind('<Return>', lambda e: self.onSelected(1))
        name_entry.grid(row=0, column=1, sticky='w')

        #trk color
        tk.Label(frame, text="Color", font=bold_font).grid(row=1, column=0, sticky='e')
        self._var_color = tk.StringVar()
        #self._var_color.trace('w', self.onColorChanged)
        #self.__color_entry = tk.Entry(frame, font=font, textvariable=self._var_color)
        #self.__color_entry.grid(row=1, column=1, sticky='w')
        #self.__color_entry_bg = self.__color_entry['bg']
        self._var_color.trace('w', self.onColorSelected)
        color_combo = ttk.Combobox(frame, font=font, width=20, textvariable=self._var_color)
        color_combo.grid(row=1, column=1, sticky='w')
        color_combo['values'] = conf.TRK_COLORS

        #tk.Checkbutton(frame, text='Focus Track point', variable=self._var_focus).grid(row=2, column=1, sticky='w')

        return frame

    def addAlteredHandler(self, h):
        self._altered_handlers.append(h)

    def removeAlteredHandler(self, h):
        self._altered_handlers.remove(h)

    def onAltered(self, alter):
        self.master.setAlter(alter)   #hard code fist!!!
        #for handler in self._altered_handlers:
        #    handler()

    def onClosed(self, e=None):
        self.master.focus_set()
        self.destroy()

    def onSelected(self, inc):
        idx = self._trk_list.index(self._curr_trk) + inc
        if idx >= 0 and idx < len(self._trk_list):
            self.setCurrTrk(self._trk_list[idx])

    def onNameChanged(self, *args):
        #print('change to', self._var_name.get())
        name = self._var_name.get()
        if self._curr_trk.name != name:
            self._curr_trk.name = name
            self._is_changed = True
            self.onAltered('trk')

    def onColorChanged(self, *args):
        color = self._var_color.get()
        if self._curr_trk.color == color:
            self.__color_entry.config(bg=self.__color_entry_bg)  #reset default bg color
        else:
            #try: ImageColor.getrgb(color) except ValueError as e: print('Not support color %s: %s' % (color, e))
            if color.lower() not in ImageColor.colormap:
                self.__color_entry.config(bg='lightpink')
            else:
                self.__color_entry.config(bg='lightgreen')
                self._curr_trk.color = color
                self._is_changed = True
                self.onAltered('trk')

    def onColorSelected(self, *args):
        color = self._var_color.get()
        logging.debug('Set color to ' + color)
        if self._curr_trk.color != color:
            self._curr_trk.color = color
            self._is_changed = True
            self.onAltered('trk')

    def onFocus(self, *args):
        is_focus = self._var_focus.get()
        if is_focus:
            idxes = self.pt_list.curselection()
            if idxes:
                pts = [self._curr_trk[i] for i in idxes]
                self.highlightTrk(pts)

    def onPtSelected(self, e):
        idxes = self.pt_list.curselection()
        if idxes:
            pts = [e.widget.data[i] for i in idxes]  #index of pts -> pts
            self.highlightTrk(pts)

    def onPtDeleted(self, e):
        idxes = self.pt_list.curselection()
        if idxes:
            #Todo: bulk of deleting is better?
            for i in sorted(idxes, reverse=True):
                self.pt_list.delete(i) #view
                del self._curr_trk[i]  #data
            self._is_changed = True

            self.onAltered('trk')

    def highlightTrk(self, pts):
        if self._var_focus.get():
            self.master.resetMap(pts[0])
        self.master.restore()
        self.master.highlightTrk(pts)

        
    def setCurrTrk(self, trk):
        self._curr_trk = trk

        idx = self._trk_list.index(trk)
        sz = len(self._trk_list)

        #title
        title_txt = "%s (%d/%d)" % (trk.name, idx+1, sz)
        self.title(title_txt)

        #info
        self._var_name.set(trk.name)
        self._var_color.set(trk.color)

        #button state
        self.__left_btn.config(state=('disabled' if idx == 0 else 'normal'))
        self.__right_btn.config(state=('disabled' if idx == sz-1 else 'normal'))

        #pt
        self.pt_list.delete(0, 'end')
        self.pt_list.data = trk
        sn = 0
        for pt in trk:
            sn += 1
            txt = "#%04d  %s: %s, %s" % ( sn, conf.getPtTimeText(pt), conf.getPtPosText(pt), conf.getPtEleText(pt))
            self.pt_list.insert('end', txt)

def getAspectResize(img, size):
    dst_w, dst_h = size
    src_w, src_h = img.size

    ratio_w = dst_w / src_w
    ratio_h = dst_h / src_h

    if ratio_w < ratio_h: #zoom to width
        w = dst_w
        h = int(src_h*ratio_w)
    elif ratio_h < ratio_w: #zoom to height
        w = int(src_w*ratio_h)
        h = dst_h
    else:
        w = dst_w
        h = dst_h

    return img.resize((w, h))

def getTextImag(text, size):
    w, h = size
    img = Image.new("RGBA", size)
    with DrawGuard(img) as draw:
        draw.text( (int(w/2-20), int(h/2)), text, fill='lightgray', font=conf.IMG_FONT)

    return img

def __testTileArea():
    a1 = TileArea(16, (0, 0), (10, 10))
    a2 = TileArea(16, (5, 5), (2, 2))
    a3 = TileArea(15, (0, 0), (10, 10))
    a4 = TileArea(16, (5, 5), (10, 10))
    a5 = TileArea(16, (5, 5), (2, 10))

    print(a1)
    print(a2)
    print(a1.overlay(a2)) #a1 contains a2
    print(a1.overlay(a3)) # not the same level
    print(a1.overlay(a4)) # part
    print(a1.overlay(a5)) # part
    print(a4.overlay(a1)) # part

def canExit(disp_board):

    if not disp_board.is_alter:
        return True

    ans = messagebox.askquestion('Save before Exit', 'Do you want to save file?', type='yesnocancel')
    if ans == 'yes' and disp_board.onGpxSave():
        return True
    if ans == 'no':
        return True
    elif ans == 'cancel':
        return False

    return False

def onExit(root, disp_board):
    if canExit(disp_board):
        disp_board.exit()
        root.destroy()

def getTitleText(files):
    txt = ""
    if len(files) > 0:
        for f in files:
            txt += path.basename(f)
            txt += ' '
        txt += "- "
    return txt + "GisEditor"

def initArguments():
    parser = argparse.ArgumentParser(description='ref https://github.com/dayanuyim/GisEditor')
    parser.add_argument("-v", "--verbose", help="show detail information", action="count", default=0)
    parser.add_argument('files', nargs='*', help="Gps or photo files to parse")
    return parser.parse_args()

if __name__ == '__main__':
    __version = '0.2'
    args = initArguments()

    #init logging
    log_level = logging.DEBUG if args.verbose >= 2 else logging.INFO if args.verbose == 1 else logging.WARNING
    logging.basicConfig(level=log_level,
            format="%(asctime)s.%(msecs)03d [%(levelname)s] [%(module)s] %(message)s", datefmt="%H:%M:%S")

    logging.info("Initialize GisEditor version " + __version);
    try:
        #create root
        root = tk.Tk()
        pmw.initialise(root)
        root.withdraw() #hidden
        if platform.system() == "Windows":
            root.iconbitmap(conf.EXE_ICON)
            #icon = ImageTk.PhotoImage(conf.EXE_ICON)
            #root.tk.call('wm', 'iconphoto', root._w, icon)

        root.title(getTitleText(args.files))
        root.geometry('952x700+200+0')
        #root.geometry('256x256+500+500') #@@!

        #create display board
        pad_ = 2
        disp_board = MapBoard(root)
        disp_board.version = __version
        disp_board.pack(side='right', anchor='se', expand=1, fill='both', padx=pad_, pady=pad_)
        root.protocol('WM_DELETE_WINDOW', lambda: onExit(root, disp_board))

        #add files
        disp_board.addFiles(args.files)

        #show
        root.update()
        root.deiconify()
        root.mainloop()
    except Exception as ex:
        logging.error("Startup failed: %s" % str(ex,))
        messagebox.showwarning('Startup failed', str(ex))
        #raise ex  #@@!

