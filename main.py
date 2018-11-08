#!/usr/bin/python3

import os
import subprocess
import tkinter as tk
import Pmw as pmw
import shutil
import tempfile
import time
import logging
import argparse
import platform
import pytz
import types
from os import path
from PIL import Image, ImageTk, ImageDraw, ImageColor
from math import floor, ceil, sqrt
from tkinter import messagebox, filedialog, ttk
from datetime import datetime, timedelta
from threading import Lock, Thread
from collections import OrderedDict

#my modules
import src.conf as conf
import src.sym as sym
import src.coord as coord
import src.util as util
from src.ui import MapSelectFrame
from src.gpx import GpsDocument, WayPoint, TrackPoint
from src.pic import PicDocument
from src.util import GeoPoint, DrawGuard, imageIsTransparent, bindMenuCmdAccelerator, bindMenuCheckAccelerator
from src.util import AreaSelector, AreaSizeTooLarge, GeoInfo  #should move to ui.py
from src.util import downloadAsTemp, drawTextBg, subgroup, isValidFloat
from src.common import fmtPtPosText, fmtPtEleText, fmtPtTimeText, fmtPtTimezone, fmtPtLocaltime, textToGeo
from src.tile import TileAgent, MapDescriptor
from src.sym import askSym, toSymbol
from src.raw import *

to_pixel = coord.TileSystem.getPixcelXYByTileXY
to_tile = coord.TileSystem.getTileXYByPixcelXY

# TODO init from conf
Options = types.SimpleNamespace(
    coordLineSys = None,
    coordLineDensity = COORD_NONE,
)

def showmsg(msg):
    """print to console/log and messagebox (generalize this with LOG, moving to util.py)"""
    logging.error(msg)
    messagebox.showwarning('', msg)

def isGpsFile(path):
    """read pathes"""
    (fname, ext) = os.path.splitext(path)
    ext = ext.lower()
    return ext in conf.GPSBABEL_EXT_FMT

def isPicFile(path):
    (fname, ext) = os.path.splitext(path)
    ext = ext.lower()

    if ext in ('.jpg', '.jpeg', '.tif', '.gif', '.png'):
        return True
    return False

def getGpsDocument(path):
    try:
        #support http
        if path.startswith("http"):
            path = downloadAsTemp(path)

        (fname, ext) = os.path.splitext(path)
        ext = ext.lower()
        gps = GpsDocument()

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
        return PicDocument(path)
    except Exception as ex:
        showmsg("cannot read the picture '%s': %s" % (path, str(ex)))
    return None

def __toGpx(src_path, flag):
    exe_file = conf.GPSBABEL_EXE

    #input format
    (fname, ext) = os.path.splitext(src_path)
    if ext == '':
        raise ValueError("cannot identify gps format deu to no file extension")
    input_fmt = conf.GPSBABEL_EXT_FMT.get(ext.lower())
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

def parsePathes(pathes):
    """may generalize the method, and moving to util.py"""
    gps_path = []
    pic_path = []
    for path in pathes:
        __parsePath(path, gps_path, pic_path)
    gps_path.sort()
    pic_path.sort()
    return gps_path, pic_path

class MapBoard(tk.Frame):
    """The Main board to display the map"""
    MODE_NORMAL = 0
    MODE_DRAW_TRK = 1
    MODE_SAVE_IMG = 2

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

    @property
    def title(self):
        return self.master.title()

    @title.setter
    def title(self, v):
        self.master.title(v)

    @property
    def ref_geo(self):
        return self.__map_ctrl.geo

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

        self.__mode = self.MODE_NORMAL

        self.__map_descs = self.__getUserMapDescriptors()
        self.__map_ctrl = MapController(self)
        self.__map_ctrl.configMap(self.__map_descs)

        self.__map_menu = None

        #board
        self.__is_closed = False
        self.__bg_color=self['bg']
        self.__focused_wpt = None
        self.__map = None         #buffer disp image for restore map
        self.__map_attr = None
        self.__map_req_time = datetime.min
        self.__map_has_update = False
        self.__map_prog = None
        self.__map_req_lock = Lock()
        self.__alter_time = None
        self.__pref_dir = None
        self.__pref_geo = None
        self.__some_geo = GeoPoint(lon=121.334754, lat=24.987969)
        self.__draw_trk_id = None
        self.__orig_title = None
        self.__left_click_pos = None
        self.__right_click_pos = None
        self.__menu_ck_vars = []
        self.__set_level_ts = datetime.min
        self.__version = ''

        Thread(target=self.__runMapUpdater).start()

        #canvas items
        self.__canvas_map = None
        self.__canvas_sel_area = None

        #info
        self.__info_frame = self.initMapInfo()
        self.__info_frame.pack(side='top', expand=0, fill='x', anchor='nw')
        self.__setMapInfo()

        #status
        status_frame = self.initStatusBar()
        status_frame.pack(side='bottom', expand=0, fill='x', anchor='nw')

        #global events
        self.master.bind("<Escape>", lambda e: self.__resetMode())

        #display area
        self.__init_w= 800  #deprecated
        self.__init_h = 600  #deprecated
        self.disp_canvas = tk.Canvas(self, bg='#808080')
        self.disp_canvas.pack(expand=1, fill='both', anchor='n')

        if platform.system() == "Linux":
            self.disp_canvas.bind('<Button-4>', lambda e: self.__onMouseWheel(e, 1))  #roll up
            self.disp_canvas.bind('<Button-5>', lambda e: self.__onMouseWheel(e, -1)) #roll down
        else:
            self.disp_canvas.bind('<MouseWheel>', lambda e: self.__onMouseWheel(e, e.delta))

        self.disp_canvas.bind('<Motion>', self.onMotion)
        self.disp_canvas.bind("<Button-1>", lambda e: self.onClickDown(e, 'left'))
        self.disp_canvas.bind("<Button-2>" if platform.system() == "Darwin" else "<Button-3>",
                lambda e: self.onClickDown(e, 'right'))

        self.disp_canvas.bind("<Button1-Motion>", lambda e: self.onClickMotion(e, 'left'))
        self.disp_canvas.bind("<Button1-ButtonRelease>", lambda e: self.onClickUp(e, 'left'))
        self.disp_canvas.bind("<Button3-ButtonRelease>", lambda e: self.onClickUp(e, 'right'))
        self.disp_canvas.bind("<Configure>", self.onResize)

        #right-click menu
        self.__rclick_menu = tk.Menu(self.disp_canvas, tearoff=0)
        self.__rclick_menu.add_command(label='Add Files', underline=0, command=self.onAddFiles)
        self.__rclick_menu.add_separator()
        self.__rclick_menu.add_command(label='Add wpt', command=self.onWptAdd)
        '''
        edit_wpt_menu = tk.Menu(self.__rclick_menu, tearoff=0)
        edit_wpt_menu.add_command(label='Edit 1-by-1', underline=5, command=lambda:self.onEditWpt(mode='single'))
        edit_wpt_menu.add_command(label='Edit in list', underline=5, command=lambda:self.onEditWpt(mode='list'))
        self.__rclick_menu.add_cascade(label='Edit waypoints...', menu=edit_wpt_menu)
        '''
        bindMenuCmdAccelerator(self.master, '<Control-w>', self.__rclick_menu, 'Edit waypoints', lambda:self.onEditWpt(mode='single'))
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
        bindMenuCmdAccelerator(self.master, '<Control-t>',
                self.__rclick_menu, 'Edit tracks',
                lambda:self.onEditTrk(mode='single'))

        split_trk_menu = tk.Menu(self.__rclick_menu, tearoff=0)
        split_trk_menu.add_command(label='By day', command=lambda:self.onSplitTrk(self.trkDiffDay))
        split_trk_menu.add_command(label='By time gap', command=lambda:self.onSplitTrk(self.trkTimeGap))
        split_trk_menu.add_command(label='By distance', command=lambda:self.onSplitTrk(self.trkDistGap))
        self.__rclick_menu.add_cascade(label='Split tracks...', menu=split_trk_menu)

        # coordintate lines
        self.master.bind("<Control-6>", lambda e: self.onCoordLine(TWD67))
        self.master.bind("<Control-9>", lambda e: self.onCoordLine(TWD97))

        # mode to draw trk
        ck_var = bindMenuCheckAccelerator(self.master, '<F' + str(self.MODE_DRAW_TRK) + '>',
                self.__rclick_menu, 'Draw tracks...',
                lambda checked:self.__changeMode(self.MODE_DRAW_TRK if checked else self.MODE_NORMAL))
        self.__menu_ck_vars.append(ck_var)

        self.__rclick_menu.add_separator()

        # mode to save image
        bindMenuCmdAccelerator(self.master, '<F' + str(self.MODE_SAVE_IMG) + '>',
                self.__rclick_menu, 'Save to image...',
                lambda:self.__changeMode(self.MODE_SAVE_IMG))

        # mode to save gpx
        bindMenuCmdAccelerator(self.master, '<Control-s>',
                self.__rclick_menu, 'Save to gpx...',
                command=self.onGpxSave)

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

        self.__map_btn = tk.Button(frame, text="▼", relief='groove', border=2, command=self.__triggerMapSelector)
        self.__map_btn.pack(side='left', expand=0, anchor='nw')

        #level
        self.__info_level = self.__genInfoWidgetNum(frame, font, 'Level', 2, conf.MIN_SUPP_LEVEL, conf.MAX_SUPP_LEVEL,
                #state='disabled',
                cb=self.__onSetLevel)

        #pos
        self.__info_67tm2 = self.__genInfoWidget(frame, font, 'TM2/67', 16, self.onPosSet)
        self.__info_97tm2 = self.__genInfoWidget(frame, font, 'TM2/97', 16, self.onPosSet)
        self.__info_97latlon = self.__genInfoWidget(frame, font, 'LatLon/97', 20, self.onPosSet)

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

    def __genInfoWidgetNum(self, frame, font, title, width, min_, max_, state='normal', cb=None):

        bfont = font + ' bold'

        label = tk.Label(frame, font=bfont, text=title)
        label.pack(side='left', expand=0, anchor='nw')

        var = tk.IntVar()
        widget = tk.Spinbox(frame, font=font, width=width, textvariable=var, state=state, from_=min_, to=max_)
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

    # mode framework  =================================================
    def __leaveMode(self, mode):
        if mode == self.MODE_NORMAL:
            self.__rclick_menu.unpost()
            self.__wpt_rclick_menu.unpost()

        elif mode == self.MODE_SAVE_IMG:
            if self.__canvas_sel_area is not None:
                self.__canvas_sel_area.exit()
                self.__canvas_sel_area = None

        elif mode == self.MODE_DRAW_TRK:
            self.__draw_trk_id = None
            #ui
            self.resetMap(force='trk')
            self.master['cursor'] = ''

        #recover title
        if self.__orig_title is not None:
            self.title = self.__orig_title

    def __enterMode(self, mode):
        self.__orig_title = self.title
        self.__mode = mode;

        if mode == self.MODE_NORMAL:
            pass

        elif mode == self.MODE_SAVE_IMG:
            if self.__enterSaveImgMode():
                logging.critical("auto change back to NORMAL mode")
                self.__changeMode(self.MODE_NORMAL)

        elif mode == self.MODE_DRAW_TRK:
            self.title += " [Draw Track]"
            self.master['cursor'] = 'pencil'

        else:
            logging.critical("set to unknown mode '" + mdoe + "'")

    def __changeMode(self, mode):
        if self.__mode != mode:
            logging.critical("change from mode %d to mode %d" % (self.__mode, mode))
            self.__leaveMode(self.__mode)
            self.__enterMode(mode)

    def __resetMode(self):
        self.__hideMapSelector()         #hide map selector, if any
        for var in self.__menu_ck_vars:  #rest all menu's checks
            var.set(False)
        self.__changeMode(self.MODE_NORMAL)

    # operations ====================================================================
    #release sources to exit
    def exit(self):
        self.__is_closed = True
        self.__leaveMode(self.__mode)
        self.__map_ctrl.close()

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

    def addGpx(self, gpx):
        if gpx is not None:
            self.__map_ctrl.addGpxLayer(gpx)

    def genWpt(self, pos):
        px, py = pos
        geo = self.getGeoPointAt(px, py)
        wpt = WayPoint(geo.lat, geo.lon)
        wpt.time = datetime.utcnow().replace(tzinfo=pytz.utc)
        return wpt

    def addWpt(self, wpt):
        if wpt is not None:
            self.__map_ctrl.addWpt(wpt)

    def deleteTrk(self, trk):
        if trk is not None:
            self.__map_ctrl.deleteTrk(trk)

    def setLevel(self, level, focus_pt=None, allow_period_ms=500):
        #check mode
        if self.__mode == self.MODE_SAVE_IMG:
            return

        #clear message
        if hasattr(self, '__status_label'):
            self.__status_label['text'] = ''

        #check if level valid
        if self.__map_ctrl.level == level:
            return

        if level < conf.MIN_SUPP_LEVEL or level > conf.MAX_SUPP_LEVEL:
            #messagebox.showwarning('Level Over Limit', 'The level should between %d ~ %d' % (conf.MIN_SUPP_LEVEL, conf.MAX_SUPP_LEVEL))
            self.__status_label['text'] = 'The level should between %d ~ %d' % (conf.MIN_SUPP_LEVEL, conf.MAX_SUPP_LEVEL)
            return

        #check frequecy
        now = datetime.now()
        if now < (self.__set_level_ts + timedelta(milliseconds=allow_period_ms)):
            return

        try:
            self.__set_level_ts = now

            if focus_pt is not None:
                x, y = focus_pt
            else:
                x = int(self.disp_canvas.winfo_width()/2)
                y = int(self.disp_canvas.winfo_height()/2)

            self.__map_ctrl.shiftGeoPixel(x, y) #make click point as focused geo
            self.__map_ctrl.level = level
            self.__map_ctrl.shiftGeoPixel(-x, -y) #shift to make click point at the same position

            self.__setMapInfo()
            self.resetMap()
        except Exception as ex:
            logging.error("set level '%s' error: %s" % (str(level), str(ex)))
            messagebox.showwarning('set level error', str(ex))
    
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

    def __setMapInfo(self, geo=None):
        self.__info_mapname['text'] = self.__getMapNameText()

        self.__info_level.variable.set(self.__map_ctrl.level)

        if geo is not None:
            self.__info_97latlon.variable.set("%f, %f" % (geo.lat, geo.lon))
            self.__info_97tm2.variable.set("%.3f, %.3f" % (geo.twd97_x/1000, geo.twd97_y/1000))
            self.__info_67tm2.variable.set("%.3f, %.3f" % (geo.twd67_x/1000, geo.twd67_y/1000))


    # @Careful: multi-threads to access self.__status_label will cause blocking (but unknown why)
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

    def __getPrefGeoPt(self):
        #prefer track point
        for trk in self.__map_ctrl.getAllTrks():
            for pt in trk:
                return pt

        #wpt
        for wpt in self.__map_ctrl.getAllWpts():
            return wpt

        return None

    # events ==================================================================================
    def __onMapEnableChanged(self, desc, old_val):
        logging.debug("desc %s's enable change from %s to %s" % (desc.map_id, old_val, desc.enabled))
        #re-config
        self.__map_descs = self.__map_menu.map_descriptors
        self.__map_ctrl.configMap(self.__map_descs)
        self.resetMap()

    def __onMapAlphaChanged(self, desc, old_val):
        logging.debug("desc %s's enable change from %f to %f" % (desc.map_id, old_val, desc.alpha))
        if desc.enabled:
            self.resetMap(force='all')

    def __triggerMapSelector(self):
        if self.__map_menu is None:
            #create
            self.__map_menu = MapSelectFrame(self, self.__map_descs)
            self.__map_menu.visible = False

            self.__map_menu.enable_changed_handler = self.__onMapEnableChanged
            self.__map_menu.alpha_changed_handler = self.__onMapAlphaChanged
            
        #to show
        if not self.__map_menu.visible:
            self.__showMapSelector()
        #to hidden
        else:
            self.__hideMapSelector()

    def __showMapSelector(self):
        if self.__map_menu is not None:
            ref_w = self.__info_frame
            x = ref_w.winfo_x()
            y = ref_w.winfo_y() + ref_w.winfo_height()

            self.__map_menu.place(x=x, y=y)
            self.__map_menu.visible = True
            self.__map_menu.fitwidth()
            self.__map_btn['text'] = "▲"

    def __hideMapSelector(self):
        if self.__map_menu is not None:
            self.__map_menu.place_forget()
            self.__map_menu.visible = False
            self.__map_btn['text'] = "▼"
            self.__setMapInfo()          #re-gen map info

            # get new list & save
            self.__map_descs = self.__map_menu.map_descriptors
            self.__writeUserMapsConf()

    def __onMouseWheel(self, e, delta):
        level = self.__map_ctrl.level + (1 if delta > 0 else -1)
        self.setLevel(level, (e.x, e.y))

    def __onSetLevel(self, *args):
        try:
            level = self.__info_level.variable.get()
            self.setLevel(level)
        except Exception as ex:
            logging.warning("set level error: " + str(ex))
            #do Not show message box to user, which may be a 'temperary' key-in error

    def onPosSet(self, e):
        def coord_sys():
            if e.widget == self.__info_67tm2:
                return 'TWD67TM2'
            if e.widget == self.__info_97tm2:
                return 'TWD97TM2'
            if e.widget == self.__info_97latlon:
                return 'TWD97LatLon'
            raise ValueError('Unknown position widget: %s' % str(e.widget))

        try:
            #get geo point
            geo = textToGeo(e.widget.get(), coord_sys(), self.__map_ctrl.geo)

            #focus geo on map
            if self.__map_ctrl.mapContainsPt(geo):
                self.__map_ctrl.addMark(geo)
                self.__setMapInfo(geo)
                self.resetMap(geo, force='wpt')
            else:
                messagebox.showwarning('Invalid Location', "The location is out of range of map")

        except Exception as ex:
            messagebox.showwarning("Please use valid format: 2 decimals(KM), 2 integer(M), or 6 digits", "Get locatoin error: %s" % (str(ex),))

    #drag-n-drop events ===============================

    #@geo is just an extra candy to prevent duplicated calculation
    def __onDragBegin(self, pos, geo=None):
        #save img
        if self.__mode == self.MODE_SAVE_IMG:
            #not need, AreaSelector handle by itself
            pass
        #draw trk
        elif self.__mode == self.MODE_DRAW_TRK:
            x, y = pos
            if geo is None:
                geo = self.getGeoPointAt(x, y)
            trkpt = TrackPoint(geo.lat, geo.lon)
            #create trk and add pt
            self.__draw_trk_id = self.__map_ctrl.genTrk()
            self.__map_ctrl.addTrkpt(self.__draw_trk_id, trkpt)
            #show
            n = int(conf.TRK_WIDTH/2)
            coords = (x-n, y-n, x+n, y+n)
            self.disp_canvas.create_oval(coords, width=0, fill=conf.DEF_COLOR, tag='DRAW_TRK')
        #normal
        else:
            self.master['cursor'] = 'hand2'

    def __onDragMotion(self, last_pos, pos):
        #saving image
        if self.__mode == self.MODE_SAVE_IMG:
            #not need, AreaSelector handle by itself
            return
        #drawing track
        elif self.__mode == self.MODE_DRAW_TRK:
            if self.__draw_trk_id is None:
                logging.warning("[Logic Error] No track is created to keep trkpt")
                return
            if not last_pos:
                logging.warning("[Logic Error] No last pos")
                return
            #add pt
            x, y = pos
            geo = self.getGeoPointAt(x, y)
            trkpt = TrackPoint(geo.lat, geo.lon)
            self.__map_ctrl.addTrkpt(self.__draw_trk_id, trkpt)
            #show
            coords = last_pos + pos
            self.disp_canvas.create_line(coords, fill=conf.DEF_COLOR, width=conf.TRK_WIDTH, tag='DRAW_TRK')
        #normal
        else:
            if not last_pos:
                logging.warning("[Logic Error] No last pos")
                return
            last_x, last_y = last_pos
            x, y = pos
            self.__map_ctrl.shiftGeoPixel(last_x - x, last_y - y)
            self.__setMapInfo()
            self.resetMap()

    def __onDragEnd(self):
        #saving image
        if self.__mode == self.MODE_SAVE_IMG:
            #not need, AreaSelector handle by itself
            return
        #drawing track
        elif self.__mode == self.MODE_DRAW_TRK:
            self.disp_canvas.delete('DRAW_TRK')
            self.resetMap(force='trk')
            self.__draw_trk_id = None
        #normal
        else:
            self.master['cursor'] = ''

    # click-related events ======================================
    def onClickDown(self, e, flag):
        #to grap key events
        e.widget.focus_set()

        #bookkeeper
        pos = (e.x, e.y)
        if flag == 'left':
            self.__left_click_pos = pos
        elif flag == 'right':
            self.__right_click_pos = pos

        #geo info
        geo = self.getGeoPointAt(e.x, e.y)
        self.__setMapInfo(geo)

        if flag == 'right':
            if self.__mode != self.MODE_SAVE_IMG:
                wpt = self.__map_ctrl.getWptAround(geo)
                if wpt is not None:
                    self.__wpt_rclick_menu.post(e.x_root, e.y_root)  #right menu for wpt
                else:
                    self.__rclick_menu.post(e.x_root, e.y_root)  #right menu

        elif flag == 'left':
            #clear right menu, if any
            self.__rclick_menu.unpost()
            self.__wpt_rclick_menu.unpost()
            #if click on a wpt?
            if self.__mode != self.MODE_SAVE_IMG:
                wpt = self.__map_ctrl.getWptAround(geo)
                if wpt is not None:
                    self.onEditWpt(mode='single', wpt=wpt)
                    return
            #begin drag
            self.__onDragBegin(pos, geo)

    def onClickMotion(self, e, flag):
        curr_pos = (e.x, e.y)

        if flag == 'left':
            self.__onDragMotion(self.__left_click_pos, curr_pos)
            self.__left_click_pos = curr_pos
        else:
            self.__right_click_pos = curr_pos


    def onClickUp(self, e, flag):
        # !not unset click pos, it may be used by later method, ex: onWptAdd()

        if flag == 'left':
            self.__onDragEnd()


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

    #{{ Right click actions ==========================================
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
                self.__setMapInfo(self.__pref_geo)
                self.resetMap(self.__pref_geo)
            else:
                self.setAlter('all')
        except Exception as ex:
            showmsg('Add Files Error: %s' % (str(ex),))

    def onWptAdd(self):
        if not self.__right_click_pos:
            showmsg('Create Wpt Error: Cannot get right click position')
            return

        wpt = self.genWpt(self.__right_click_pos)
        self.addWpt(wpt)
        self.setAlter('wpt')

    def onTrkDelete(self, trk):
        self.deleteTrk(trk)
        self.setAlter('trk')

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
            trk_board.on_trk_delete_handler = self.onTrkDelete
            trk_board.show()
        else:
            trk_board = TrkListBoard(self, trk_list, trk)
            #trk_board.addAlteredHandler(self.setAlter)
            #trk_board.show()

    def onCoordLine(self, coord_sys):
        #the next coordline resolution
        def _next(density):
            if density == COORD_NONE: return COORD_KM
            if density == COORD_KM: return COORD_100M
            if density == COORD_100M: return COORD_NONE
            return COORD_NONE

        # the same coordinate system with the next density
        if Options.coordLineSys == coord_sys:
            Options.coordLineDensity = _next(Options.coordLineDensity)
            if Options.coordLineDensity == COORD_NONE:   #also disable coordinate system
                Options.coordLineSys = None
        # reset to new coordintate system
        else:
            Options.coordLineSys = coord_sys
            Options.coordLineDensity = _next(COORD_NONE)

        self.resetMap()

    @staticmethod
    def trkDiffDay(pt1, pt2):
        t1 = fmtPtLocaltime(pt1)
        t2 = fmtPtLocaltime(pt2)
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
        logging.debug("set map progress %f", rate)
        #set status
        if rate >= 1:
            self.__setStatus('', 0, is_immediate)
        else:
            prog = 100 * rate
            txt = "Map Loading...%.1f%%" % (prog,)
            self.__setStatus(txt, prog, is_immediate)

    #return True: expected return
    #return False: interrupted by other mode
    def __enterSaveImgMode(self):

        self.title += " [Save Image]"

        enabled_maps = [desc for desc in self.__map_descs if desc.enabled]
        if not enabled_maps:
            messagebox.showwarning("Save Image Error", "No maps to save")
            return True

        try:
            coord_sys, _ = self.__map_ctrl.getDisplayCoordSys()
            if coord_sys is None:
                coord_sys = 'virtual'

            #select area
            geo_info = GeoInfo.get(coord_sys, self.__map_ctrl.geo, self.__map_ctrl.level)

            self.__canvas_sel_area = AreaSelector(self.disp_canvas, geo_info)

            #wait the returned state
            state = self.__canvas_sel_area.wait(self)
            if not state:
                return False
            if state != 'OK':
                return True

            #get fpath
            def to_ask(init_dir):
                return filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=(("Portable Network Graphics", ".png"), ("All Files", "*.*")),
                    initialdir=init_dir)
            fpath = self.withPreferredDir(to_ask)
            if not fpath:
                return True

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
            progress = MapProgressRec(img_area, img_ids)
            self.__setMapProgress(0, is_immediate=True)

            def update_prog_cb(tile_info):
                try:
                    if progress.update(tile_info):
                        logging.debug('Start to save image...%f' % (progress.rate,))
                        self.__setMapProgress(progress.rate, is_immediate=True)
                except Exception as ex:
                    logging.warning('Update saving progress error: ' + str(ex))

            #get and save
            logging.info('Start to save image')
            map, attr = self.__map_ctrl.getMap(dx, dy, geo=sel_geo, level=out_level, req_type="sync", cb=update_prog_cb)

            logging.info('Start to save image to file')
            map.save(fpath, format='png')

            #notify the saving is  done
            self.__setMapProgress(1, is_immediate=True)
            messagebox.showwarning('', 'The saving is OK!')

        except AreaSizeTooLarge as ex:
            messagebox.showwarning(str(ex), 'Please zoom out or resize the window to enlarge the map')
        except Exception as ex:
            messagebox.showwarning("Save Image Error", str(ex))
        return True

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

    #}} Right click actions ============================================

    def setAlter(self, alter):
        logging.debug(alter + " is altered")
        self.__alter_time = datetime.now()
        self.resetMap(force=alter)

    def getGeoPointAt(self, px, py):
        px += self.__map_ctrl.px
        py += self.__map_ctrl.py
        return GeoPoint(px=px, py=py, level=self.__map_ctrl.level)

    def onMotion(self, event):
        if self.__mode == self.MODE_NORMAL:
            geo = self.getGeoPointAt(event.x, event.y)

            #draw point
            curr_wpt = self.__map_ctrl.getWptAround(geo)
            prev_wpt = self.__focused_wpt
            if curr_wpt != prev_wpt:
                self.highlightWpt(curr_wpt, prev_wpt)

            #rec
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
        self.__map_ctrl.drawTrkPoint(map, self.__map_attr, pts, 'orange', 'black', width=conf.TRK_WIDTH+5)
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

    def onResize(self, e):
        disp = self.disp_canvas
        if e.widget == disp:
            if not hasattr(disp, 'image'):  #init
                self.__pref_geo = self.__getPrefGeoPt()
                geo = self.__pref_geo if self.__pref_geo is not None else self.__some_geo
                self.__setMapInfo(geo)
                self.resetMap(geo)
            elif e.width != disp.image.width() or e.height != disp.image.height():
                self.__setMapInfo()
                self.resetMap()
            # raise AS, if any
            #if self.isSaveImgMode():
            #    self.disp_canvas.tag_raise('AS')

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
                    if self.__map_prog and progress_rate != self.__map_prog.rate:
                        progress_rate = self.__map_prog.rate
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
            if self.__map_prog.update(tile_info): #need the lock due to access to data members
                self.__map_has_update = True
                logging.debug("has update")

    def resetMap(self, geo=None, w=None, h=None, force=None):
        logging.debug("RESET MAP [BEGIN].")
        _begin = datetime.now()

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
            self.__map_prog = MapProgressRec(map_area, map_ids, needed_count=self.__map_attr.fail_tiles)

        #set map
        self.__setMap(self.__map)

        #debug
        _end = datetime.now();
        _elapse = _end - _begin
        _elapse = _elapse.seconds + _elapse.microseconds/1000000
        logging.debug("RESET MAP [END], elapse: %.6fs. %s" % (_elapse, "*" * int(_elapse/0.2)))

    def restore(self):
        self.__setMap(self.__map)

    def __setMap(self, img):
        pimg = ImageTk.PhotoImage(img)
        self.disp_canvas.image = pimg #keep a ref
        
        canvas_map = self.disp_canvas.create_image((0,0), image=pimg, anchor='nw')
        self.disp_canvas.tag_lower(canvas_map)    #ensure the map is the lowest to avoid hiding other canvas objects
        '''
        #it seems the view is more smoothly if DISABLED...update...NORMAL
        #any better idea?
        self.disp_canvas['state'] = 'disabled'
        tmp = self.__canvas_map
        self.__canvas_map = self.disp_canvas.create_image((0,0), image=pimg, anchor='nw')
        if tmp:
            self.disp_canvas.tag_lower(tmp)
            self.disp_canvas.delete(tmp)
        self.disp_canvas['state'] = 'normal'
        '''

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
               cache_attr.coversArea(req_attr)

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
            return (t_left <= x <= t_right) and (t_upper <= y <= t_lower)
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
        pos = to_pixel(t_left, t_upper)
        size = to_pixel(tx_num, ty_num)
        disp_attr = MapAttr(map_attr.level, pos, size, fail_tiles)

        return  (disp_map, disp_attr)

# todo: what is the class's purpose?, suggest to reconsider
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
                if (min_lat <= geo.lat <= max_lat) and (min_lon <= geo.lon <= max_lon):
                    return True
        return False

    def shiftGeoPixel(self, px, py):
        self.geo = self.geo.addPixel(int(px), int(py), self.__level)

    def addGpxLayer(self, gpx):
        self.__gpx_layers.append(gpx)

    def genTrk(self):
        def_name = "TRK-" + str(len(self.__pseudo_gpx.tracks) + 1)
        return self.__pseudo_gpx.genTrk(def_name, conf.DEF_COLOR)

    def deleteTrk(self, trk):
        for gpx in self.__gpx_layers:
            if trk in gpx.tracks:
                gpx.tracks.remove(trk)
                break

    def addTrkpt(self, trk_idx, pt):
        self.__pseudo_gpx.addTrkpt(trk_idx, pt)

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
                break

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
        req_attr = MapAttr(level, (px, py), (width, height), 0)
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
               cache_attr.coversArea(req_attr)

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
        if alpha == 256 or max_a == 0:
            return img
        if alpha == 0 or min_a == 255:
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

    def __getMapAgents(self):
        agents = []
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

            agents.append(agent)

        return agents

    def __runReqMap(self, repo, repo_lock, agent, req_attr, req_type, cb):
        logging.debug('generating map: %s', (agent.map_id,))
        res = agent.genMap(req_attr, req_type, cb)
        logging.debug('generated map: %s', (agent.map_id,))
        with repo_lock:
            repo[agent] = res

    def __getMaps(self, req_attr, req_type, cb=None):
        agents = self.__getMapAgents()

        if not agents:
            return None

        maps = []
        
        # sync to get maps
        if len(agents) == 1 or req_type == 'sync':
            for agent in agents:
                map, attr = agent.genMap(req_attr, req_type, cb)
                maps.append((map, attr, agent.alpha))
        # Async to get maps
        else:
            map_repo = {}
            map_repo_lock = Lock()
            map_workers = []

            #create req map workers
            for agent in agents:
                job = lambda: self.__runReqMap(map_repo, map_repo_lock, agent, req_attr, req_type, cb)
                worker = Thread(target=job)
                worker.start()
                map_workers.append(worker)

            #wait all workers done
            for worker in map_workers:
                worker.join()

            #collectin maps
            idx = 0
            for agent in agents:
                map, attr = map_repo[agent]
                maps.append((map, attr, agent.alpha))
                logging.debug('get map[%d] %-20s, size: %s, attr: %s' % (idx, agent.map_id, "None" if map is None else str(map.size), str(attr)))
                idx += 1

        return maps

    def __checkAttrs(self, attrs, baseattr):
        basearea = baseattr.toTileArea()
        areas = [attr.toTileArea() for attr in attrs]

        for i in range(len(areas)):
            area = areas[i]
            if area != basearea:
                logging.warning("[NeedCropMap] map[%d]: %s" % (i, str(attrs[i])))
                logging.warning("[NeedCropMap]      -> %s" % (str(baseattr)))

    #alpha between 0.0~1.0
    @classmethod
    def combineMap(cls, basemap, map, alpha):
        if imageIsTransparent(map):
            if alpha != 1.0:
                map = cls.tunealpha(map, alpha)
            return Image.alpha_composite(basemap, map)
        else:
            if alpha != 1.0:
                return Image.blend(basemap, map, alpha)
            return map

    def __genBaseMap(self, req_attr, req_type, cb=None):

        maps = self.__getMaps(req_attr, req_type, cb)

        #create attr
        baseattr = None
        if not maps:
            baseattr = req_attr.clone() 
            baseattr.fail_tiles = 0
        else:
            attrs = [attr for map, attr, alpha in maps]
            area = TileArea.intersetOverlap(attrs)
            fail_tiles = sum([attr.fail_tiles for attr in attrs])
            baseattr = MapAttr.toMapAttr(area, fail_tiles)

            self.__checkAttrs(attrs, baseattr)

        #create basemap
        basemap = Image.new("RGBA", baseattr.size, "white")
        if maps:
            for map, attr, alpha in reversed(maps):
                if map is None:
                    continue
                cropmap = self.__genCropMap(map, attr, baseattr)
                basemap = self.combineMap(basemap, cropmap, alpha)

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
                # Draw tracks in reversed order, to put the first track on the most top.
                #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "draw gpx...")
                for trk in reversed(gpx.tracks):
                    if self.isTrackInImage(trk, map_attr):
                        self.drawTrkPoint(map, map_attr, trk, trk.color, draw=draw)

    def drawTrkPoint(self, map, map_attr, pts, color, bg_color=None, draw=None, width=conf.TRK_WIDTH):
        if pts is None or len(pts) == 0:
            return

        #set to default color if invalid
        if not (color and color.lower() in ImageColor.colormap):
            color = conf.DEF_COLOR

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


    def isTrackInImage(self, trk, map_attr):
        """Currently disabled, 'cause the algo will be broken if two pt across the image"""
        return True
        #if some track point is in disp
        # for pt in trk:
        #     (px, py) = pt.pixel(map_attr.level)
        #     if map_attr.coversPoint(px, py):
        #         return True
        # return False

    def __drawWpt(self, map, map_attr):
        """draw pic as waypoint"""
        try:
            wpts = self.getAllWpts()  #gpx's wpt + pic's wpt
            if self.__mark_wpt:
                wpts.append(self.__mark_wpt)

            if len(wpts) == 0:
                return

            with DrawGuard(map) as draw:
                for wpt in wpts:
                    (px, py) = wpt.pixel(map_attr.level)
                    self.drawWayPoint(map, map_attr, wpt, "black", draw=draw)
        except Exception as ex:
            logging.error('draw wpt error: %s' % str(ex))
            

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
        if not map_attr.coversPoint(px, py):
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


    def __genCropMap(self, map, src_area, dst_area):
        left   = dst_area.x - src_area.x
        top    = dst_area.y - src_area.y
        right  = left + dst_area.width
        bottom = top + dst_area.height

        bbox = (left, top, right, bottom)
        if bbox == (0, 0) + map.size:
            return map
        else:
            return map.crop(bbox)

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

    def getDisplayCoordSys(self):
        # enforced by options
        if Options.coordLineSys:
            return (Options.coordLineSys,
                    Options.coordLineDensity)

        # attr from maps
        coord_syss = [desc.coord_sys for desc in self.__map_descs \
                if desc.enabled and desc.coord_sys in SUPP_COORD_SYSTEMS]
        if coord_syss:
            return (coord_syss[0], COORD_TEXT)

        # NA
        return None, COORD_NONE


    def __drawCoordValue(self, map, attr):

        if attr.level <= 12:  #too crowded to show
            return

        coord_sys, coord_density = self.getDisplayCoordSys()
        if coord_sys is None:
            return

        # init GeoInfo
        geo_info = GeoInfo.get(coord_sys, self.geo, attr.level)

        # xy to draw
        lines, texts, line5, line10, text10 = self.__getCoordValueXY(attr, geo_info, coord_density)

        #to draw acoording to data
        with DrawGuard(map) as draw:
            for xy in lines:
                draw.line(xy, fill="#909090", width=1)
            for xy in line5:
                draw.line(xy, fill="#606060", width=1)
            for xy in line10:
                draw.line(xy, fill="#202020", width=1)
            for xy, text in texts:
                drawTextBg(draw, xy, text, fill="gray", font=conf.IMG_FONT_SMALL)
            for xy, text in text10:
                drawTextBg(draw, xy, text, fill="black", font=conf.IMG_FONT)

    def __getCoordValueXY(self, attr, geo_info, coord_density):
        # xy list
        lines = []
        texts = []
        line5 = []
        line10 = []
        text10 = []

        # w/h
        width = attr.right_px - attr.left_px
        height = attr.low_py - attr.up_py

        # TM2 x/y of bounding-box
        left_x, up_y = geo_info.getCoordByPixel(attr.left_px, attr.up_py)
        right_x, low_y = geo_info.getCoordByPixel(attr.right_px, attr.low_py)

        scale = 100 #if coord_density >= COORD_100M else 1000

        # xy for text
        def toTxt10XY(px, py): return (px + 5, py - 20)
        def toTxtXY(px, py):   return (px + 5, py - 20 + 4)

        # the functions depends on x or y
        def getPx(px, py): return px
        def getPy(px, py): return py
        def toVer(px): return (px, 0, px, height)
        def toHor(py): return (0, py, width, py)
        def getBasePixelOfX(x): return geo_info.getPixelByCoord(x*scale, low_y)
        def getBasePixelOfY(y): return geo_info.getPixelByCoord(left_x, y*scale)

        # the logic to collect xy position of line/text.
        # (the function prevents from looping x and y, respectively.)
        def getCoordData(begin_pos, end_pos, base_fun, line_fun, pxl_fun):
            for pos in range(ceil(begin_pos/scale), floor(end_pos/scale) +1):
                #print("tm: ", x)
                px, py = base_fun(pos)
                px -= attr.left_px
                py -= attr.up_py
                p = pxl_fun(px, py) # selecting px or py by pxl_fun

                if coord_density >= COORD_TEXT and pos % 10 == 0:
                    text10.append( (toTxt10XY(px,py), str(int(pos/10))) )
                if coord_density >= COORD_KM and pos % 10 == 0:
                    line10.append(line_fun(p))
                if coord_density >= COORD_100M:
                    if pos % 5 == 0:
                        line5.append(line_fun(p))
                    else:
                        lines.append(line_fun(p))

                    if pos % 10 != 0 and attr.level >= 16:  #also show text for 100m
                        texts.append( (toTxtXY(px,py), str(pos%10)) )

        # get data
        getCoordData(left_x, right_x, getBasePixelOfX, toVer, getPx)
        getCoordData(low_y, up_y, getBasePixelOfY, toHor, getPy)

        return lines, texts, line5, line10, text10


class MapProgressRec:
    @property
    #complete rate of tiles
    def rate(self):
        return 1 if not self.__total else self.__count / self.__total

    def __init__(self, map_area, map_ids, init_count=0, needed_count=None):
        self.__map_area = map_area
        self.__map_ids = map_ids

        self.__total = self.__getTotalTiles()
        self.__count = init_count if needed_count is None else self.__total - needed_count
        self.__count = min(max(0, self.__count), self.__total)  #crop

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
    def level(self): return self._level

    @property
    def pos(self): return self._pos

    @property
    def size(self): return self._size

    @property
    def x(self): return self._pos[0]

    @property
    def y(self): return self._pos[1]

    @property
    def width(self): return self._size[0]

    @property
    def height(self): return self._size[1]

    @property
    def area(self):
        return self.width * self.height

    def __init__(self, level, pos, size):
        self._level = level
        self._pos = pos
        self._size = size

    def __str__(self):
        x, y = self.pos
        w, h = self.size
        return "TileArea{level=%d, pos=(%d, %d), size=(%d, %d)}" % (self.level, x, y, w, h)

    def __eq__(self, rhs):
        return self.level == rhs.level and self.pos == rhs.pos and self.size == rhs.size

    def __ne__(self, rhs):
        return not self.__eq__(rhs)

    def overlay(self, rhs):
        """
        :return: overlayed area or None
        """
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

    def coversArea(self, rhs):
        return self.level == rhs.level and \
               self.left_px <= rhs.left_px and self.up_py <= rhs.up_py and \
               self.right_px >= rhs.right_px and self.low_py >= rhs.low_py

    def coversPoint(self, px, py):
        return 0 <= px - self.x < self.width and 0 <= py - self.y < self.height

    def boundTiles(self, extra_p=0):
        x, y = self.pos
        w, h = self.size
        t_left, t_upper  = to_tile(x - extra_p, y - extra_p)
        t_right, t_lower = to_tile(x + w + extra_p, y + h + extra_p)
        return (t_left, t_upper, t_right, t_lower)

    def zoomToLevel(self, level):
        x, y = self.pos
        w, h = self.size

        if level > self.level:
            s = level - self.level
            return TileArea(level, (x << s, y << s), (w << s, h << s))
        elif self.level > level:
            s = self.level - level
            return TileArea(level, (x >> s, y >> s), (w >> s, h >> s))
        else:
            return self

    @classmethod
    def lineOverlay(cls, x1, w1, x2, w2):
        if x1 <= x2 < (x1 + w1):
            x = x2
        elif x2 <= x1 < (x2 + w2):
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

    @classmethod
    def intersetOverlap(cls, areas):
        if not areas:
            return None

        inter_area = areas[0]
        for area in areas[1:]:
            inter_area = inter_area.overlay(area)
            if inter_area is None:
                return None
        return inter_area


class MapAttr(TileArea):
    @property
    def left_px(self): return self.x

    @property
    def up_py(self): return self.y

    @property
    def right_px(self): return self.x + self.width - 1

    @property
    def low_py(self): return self.y + self.height - 1

    @property
    def fail_tiles(self): return self._fail_tiles

    @fail_tiles.setter
    def fail_tiles(self, v): self._fail_tiles = v

    def __init__(self, level, pos, size, fail_tiles=0):
        super().__init__(level, pos, size)
        self._fail_tiles = fail_tiles

    def __str__(self):
        return "MapAttr{level=%d, pos=%s, size=%s, fail_tiles=%d}" % (self.level, str(self.pos), str(self.size), self.fail_tiles)

    def clone(self):
        return MapAttr(self.level, self.pos, self.size, self.fail_tiles)

    def toTileArea(self):
        return TileArea(self.level, self.pos, self.size)

    def zoomToLevel(self, level):
        area = super().zoomToLevel(level)
        return self.toMapAttr(area, self.fail_tiles)

    @classmethod
    def toMapAttr(cls, area, fail_tiles=0):
        return MapAttr(area.level, area.pos, area.size, fail_tiles)


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
        self._var_focus = tk.BooleanVar(value=conf.WPT_SET_FOCUS)
        self._var_focus.trace('w', self.onFocusChanged)

        #wpt name
        self._var_name = tk.StringVar()
        self._var_name.trace('w', self.__onNameChanged)

        self._var_pos = tk.StringVar()
        self._var_ele = tk.StringVar()
        self._var_time = tk.StringVar()

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

    def onFocusChanged(self, *args):
        self.highlightWpt(self._curr_wpt)

    def onEditSymRule(self):
        sym.showRule(self)
    
    def __onNameChanged(self, *args):
        #print('change to', self._var_name.get())
        name = self._var_name.get()
        if self._curr_wpt.name != name:
            self._curr_wpt.name = name
            self._curr_wpt.sym = toSymbol(name)
            self._is_changed = True
            self.showWptIcon(self._curr_wpt)
            #main map
            self.onAltered('wpt')
            self.highlightWpt(self._curr_wpt)

    def highlightWpt(self, wpt):
        #focus
        is_focus = self._var_focus.get()
        if is_focus:
            self.master.resetMap(wpt)

        #highlight the current wpt
        self.master.highlightWpt(wpt)

        #save user setting
        if conf.WPT_SET_FOCUS != is_focus:
            conf.WPT_SET_FOCUS = is_focus
            conf.writeUserConf()

    def unhighlightWpt(self, wpt):
        self.master.resetMap() if self.is_changed else self.master.restore()

    def showWptIcon(self, wpt):
        pass

    def setCurrWpt(self, wpt):
        pass

#todo: integrate with TrkSingleBoard
class WptSingleBoard(WptBoard):
    def __init__(self, master, wpt_list, wpt=None):
        super().__init__(master, wpt_list, wpt)

        #pick buttons
        self.__left_btn = tk.Button(self, text="<<", command=lambda:self.onWptPick(-1), disabledforeground='gray')
        self.__left_btn.pack(side='left', anchor='w', expand=0, fill='y')
        self.__left_btn.bind('<Button1-ButtonRelease>', self.onPickButtonClick)

        self.__right_btn = tk.Button(self, text=">>", command=lambda:self.onWptPick(1), disabledforeground='gray')
        self.__right_btn.pack(side='right', anchor='e', expand=0, fill='y')
        self.__right_btn.bind('<Button1-ButtonRelease>', self.onPickButtonClick)

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
        name_entry = tk.Entry(frame, font=font, relief='flat', bg=frame['bg'], highlightthickness=2, highlightcolor='lightblue', textvariable=self._var_name)
        name_entry.bind('<Return>', lambda e: e.widget.master.focus())  #focus out
        name_entry.grid(row=row, column=2, sticky='w')

        row += 1
        #focus
        tk.Checkbutton(frame, text=self._title_focus, variable=self._var_focus).grid(row=row, column=0, sticky='w')
        #wpt positoin
        pos_label = tk.Label(frame, font=bold_font, text=self._title_pos).grid(row=row, column=1, sticky='e')
        pos_entry = tk.Entry(frame, font=font, relief='flat', bg=frame['bg'], highlightthickness=2, highlightcolor='lightblue', textvariable=self._var_pos)
        pos_entry.bind('<KeyRelease>', self.__onPosKeyRelease)
        pos_entry.bind('<FocusOut>', lambda e: self._var_pos.set(fmtPtPosText(self._curr_wpt, '(%.3f, %.3f)')))  #view
        pos_entry.bind('<FocusIn>',  lambda e: self._var_pos.set(fmtPtPosText(self._curr_wpt, '%.3f, %.3f')))    #edit
        pos_entry.bind('<Return>',  lambda e: e.widget.master.focus())  #focus out
        pos_entry.grid(row=row, column=2, sticky='w')

        row +=1
        #ele
        ele_label = tk.Label(frame, font=bold_font, text=self._title_ele).grid(row=row, column=1, sticky='e')
        ele_entry = tk.Entry(frame, font=font, relief='flat', bg=frame['bg'], highlightthickness=2, highlightcolor='lightblue', textvariable=self._var_ele)
        ele_entry.bind('<KeyRelease>', self.__onEleKeyRelease)
        ele_entry.bind('<FocusOut>', lambda e: self._var_ele.set(fmtPtEleText(self._curr_wpt, '%.1f m')))  #view
        ele_entry.bind('<FocusIn>',  lambda e: self._var_ele.set(fmtPtEleText(self._curr_wpt, '%.1f')))    #edit
        ele_entry.bind('<Return>',  lambda e: e.widget.master.focus())  #focus out
        ele_entry.grid(row=row, column=2, sticky='w')

        row +=1
        #time
        tk.Label(frame, font=bold_font, text=self._title_time).grid(row=row, column=1, sticky='e')
        tk.Label(frame, font=font, textvariable=self._var_time).grid(row=row, column=2, sticky='w')

        return frame

    def __onEleKeyRelease(self, e):
        #print('on ele key-release %s' % self._var_ele.get())
        try:
            ele = float(self._var_ele.get())
            e.widget['highlightcolor'] = 'lightblue'

            if self._curr_wpt.ele != ele:
                self._curr_wpt.ele = ele
                self._is_changed = True
                self.onAltered('wpt')
        except:
            e.widget['highlightcolor'] = 'pink'

    def __onPosKeyRelease(self, e):
        #print('on pos key-release %s' % self._var_pos.get())
        try:
            geo = textToGeo(self._var_pos.get(), 'TWD67TM2', self.master.ref_geo)
            e.widget['highlightcolor'] = 'lightblue'

            if self._curr_wpt.lat != geo.lat or \
               self._curr_wpt.lon != geo.lon:
                self._curr_wpt.resetPos(lat=geo.lat, lon=geo.lon)
                self._is_changed = True
                self.onAltered('wpt')
                self.highlightWpt(self._curr_wpt)
        except Exception as ex:
            #print('on pos key-release error: %s' % ex)
            e.widget['highlightcolor'] = 'pink'

    def onImageResize(self, e):
        if hasattr(self.__img_label, 'image'):
            img_w = self.__img_label.image.width()
            img_h = self.__img_label.image.height()
            #print('event: %d, %d; winfo: %d, %d; label: %d, %d; img: %d, %d' % (e.width, e.height, self.__img_label.winfo_width(), self.__img_label.winfo_height(), self.__img_label['width'], self.__img_label['height'], img_w, img_h))
            if e.width < img_w or e.height < img_h or (e.width > img_w and e.height > img_h):
                #print('need to zomm image')
                self.setWptImg(self._curr_wpt)

    def onPickButtonClick(self, e):
        if e.widget['state'] == 'disabled' and len(self._wpt_list) > 1:
            e.widget['state'] = 'normal'

    def onWptPick(self, inc):
        idx = self._wpt_list.index(self._curr_wpt) + inc
        if idx >= len(self._wpt_list): #warp
            idx = 0
        self.setCurrWpt(self._wpt_list[idx])

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

        idx = self._wpt_list.index(wpt)
        sz = len(self._wpt_list)
        
        #title
        title_txt = "%s (%d/%d)" % (wpt.name, idx+1, sz)
        self.title(title_txt)

        #set imgae
        self.setWptImg(wpt)

        #info
        self.showWptIcon(wpt)
        self._var_name.set(wpt.name)   #this have side effect to set symbol icon
        self._var_pos.set(fmtPtPosText(wpt))
        self._var_ele.set(fmtPtEleText(wpt))
        self._var_time.set(fmtPtTimeText(wpt))

        #button state
        self.__left_btn['state'] = 'disabled' if idx == 0 else 'normal'
        self.__right_btn['state'] = 'disabled' if idx == sz-1 else 'normal'


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

            pos_txt = fmtPtPosText(w, fmt='%.3f\n%.3f')
            pos_label = tk.Label(frame, text=pos_txt, font=font)
            self.initWidget(pos_label, row, 2)

            ele_label = tk.Label(frame, text=fmtPtEleText(w), font=font)
            self.initWidget(ele_label, row, 3)

            time_label = tk.Label(frame, text=fmtPtTimeText(w), font=font)
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

    def __init__(self, master, trk_list, init_trk=None):
        super().__init__(master)

        #check init
        if not trk_list:
            raise ValueError('trk_list is empty')

        if init_trk is not None and init_trk not in trk_list:
            raise ValueError('trk is not in trk_list')

        if init_trk is None:
            init_trk = trk_list[0]

        self._curr_trk = None
        self._trk_list = trk_list
        self._altered_handlers = []
        self._is_changed = False
        self._var_focus = tk.BooleanVar(value=conf.TRK_SET_FOCUS)
        self._var_focus.trace('w', self.onFocus)

        #handlers
        self.on_trk_delete_handler = None

        #board
        self.geometry('+0+0')
        self.bind('<Escape>', lambda e: self.close())
        self.protocol('WM_DELETE_WINDOW', self.close)

        #pick buttons
        self.__left_btn = tk.Button(self, text="<<", command=lambda:self.onTrkPick(-1), disabledforeground='gray')
        self.__left_btn.pack(side='left', anchor='w', expand=0, fill='y')
        self.__left_btn.bind('<Button1-ButtonRelease>', self.onPickButtonClick)

        self.__right_btn = tk.Button(self, text=">>", command=lambda:self.onTrkPick(1), disabledforeground='gray')
        self.__right_btn.pack(side='right', anchor='e', expand=0, fill='y')
        self.__right_btn.bind('<Button1-ButtonRelease>', self.onPickButtonClick)

        #focus
        tk.Checkbutton(self, text='Focus Track point', anchor='e', variable=self._var_focus)\
            .pack(side='bottom', expand=0, fill='x')

        #pt list
        self.pt_list = tk.Listbox(self)
        pt_scroll = tk.Scrollbar(self, orient='vertical')
        pt_scroll.config(command=self.pt_list.yview)
        pt_scroll.pack(side='right', fill='y')
        self.pt_list.config(selectmode='extended', yscrollcommand=pt_scroll.set, width=50, height=30)
        self.pt_list.pack(side='bottom', anchor='nw', expand=1, fill='both')
        self.pt_list.bind('<ButtonRelease-1>', self.onTrkptSelected)
        self.pt_list.bind('<KeyRelease-Up>', self.onTrkptSelected)
        self.pt_list.bind('<KeyRelease-Down>', self.onTrkptSelected)
        self.pt_list.bind('<Delete>', self.onTrkptDeleted)

        #delete
        img = getAspectResize(Image.open(conf.DEL_ICON), (24, 24))
        self.del_icon = ImageTk.PhotoImage(img)
        tk.Button(self, image=self.del_icon, command=self.onTrkDelete, relief="flat", overrelief="raised")\
                .pack(side='right', anchor='ne', expand=0)

        #info
        self.info_frame = self.getInfoFrame()
        self.info_frame.pack(side='left', anchor='nw', expand=0, fill='x')

        self.transient(self.master)  #remove max/min buttons
        util.quietenTopLevel(self)

        #set trk
        self.setCurrTrk(init_trk)

    def show(self):
        util.showToplevel(self)

    def close(self):
        util.hideToplevel(self)
        self.destroy()

    def getInfoFrame(self):
        font = 'Arialuni 12'
        bold_font = 'Arialuni 12 bold'

        frame = tk.Frame(self)#, bg='blue')

        #trk name
        tk.Label(frame, text="Track", font=bold_font).grid(row=0, column=0, sticky='e')
        self._var_name = tk.StringVar()
        self._var_name.trace('w', self.onNameChanged)
        name_entry = tk.Entry(frame, textvariable=self._var_name, font=font)
        name_entry.bind('<Return>', lambda e: self.onTrkPick(1))
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

    def onPickButtonClick(self, e):
        if e.widget['state'] == 'disabled' and len(self._trk_list) > 1:
            e.widget['state'] = 'normal'

    def onTrkPick(self, inc):
        idx = self._trk_list.index(self._curr_trk) + inc
        if idx > len(self._trk_list) -1: #wrap
            idx = 0
        self.setCurrTrk(self._trk_list[idx])

    def onTrkDelete(self):
        if not messagebox.askyesno('Delete Track', "Delete the track?"):
            return

        #del
        trk = self._curr_trk
        idx = self._trk_list.index(trk)
        del self._trk_list[idx]

        #show the next trk
        if not self._trk_list:
            self.close()
        else:
            idx = min(idx, len(self._trk_list) -1) #crop
            self.setCurrTrk(self._trk_list[idx])

        #calllback
        if self.on_trk_delete_handler is not None:
            self.on_trk_delete_handler(trk)

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

        #save user setting
        conf.TRK_SET_FOCUS = is_focus
        conf.writeUserConf()

    def onTrkptSelected(self, e):
        idxes = self.pt_list.curselection()
        if idxes:
            pts = [e.widget.data[i] for i in idxes]  #index of pts -> pts
            self.highlightTrk(pts)

    def onTrkptDeleted(self, e):
        idxes = self.pt_list.curselection()
        if not idxes:
            return

        #deleting sequential indexes, doing it one-by-one will take time!!
        idx_groups = subgroup(idxes, lambda x,y: abs(x-y) <= 1)
        idx_groups.reverse()
        for grp in idx_groups:
            first = grp[0]
            last = grp[-1]
            logging.debug("delete trk points [%d,%d]" % (first, last))
            self.pt_list.delete(first, last)        #view
            del self._curr_trk[first : last + 1]    #data

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
        self.__left_btn['state'] = 'disabled' if idx == 0 else 'normal'
        self.__right_btn['state'] = 'disabled' if idx == sz-1 else 'normal'

        #pt list
        self.pt_list.delete(0, 'end')
        self.pt_list.data = trk
        if trk:
            tz = fmtPtTimezone(trk[0])  #optimize, prevent calculation for each pt 
            for sn, pt in enumerate(trk, 1):
                txt = "#%04d  %s: %s, %s" % ( sn, fmtPtTimeText(pt, tz), fmtPtPosText(pt), fmtPtEleText(pt))
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


def init_arguments():
    parser = argparse.ArgumentParser(description='ref https://github.com/dayanuyim/GisEditor')
    parser.add_argument("-v", "--verbose", help="show detail information", action="count", default=0)
    parser.add_argument("-c", "--conf", help="load the config file in specific folder", default="")
    parser.add_argument('files', nargs='*', help="Gps or photo files to parse")
    return parser.parse_args()

if __name__ == '__main__':

    __version = '0.25'
    args = init_arguments()

    if args.conf:
        conf.change_conf_dir(args.conf)
        logging.info('Change configure folder to ' + args.conf)

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

