#!/usr/bin/env python3

import os
import subprocess
import sys
import tkinter as tk
import Pmw as pmw
import urllib.request
import shutil
import tempfile
import time
from os import path
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageColor
from math import floor, ceil, sqrt
from tkinter import messagebox, filedialog
from datetime import datetime
from threading import Lock, Thread

#my modules
import tile
import conf
import util
from tile import TileSystem
from gpx import GpsDocument, WayPoint
from pic import PicDocument
from sym import SymRuleType, SymRule
from util import GeoPoint, getPrefCornerPos, AreaSelector, AreaSizeTooLarge

#print to console/log and messagebox (generalize this with LOG, moving to util.py)
def logMsg(desc, reason):
    #Todo: log
    print("%s: %s" % (desc, reason))
    messagebox.showwarning(desc, reason)

def logPrint(msg):
    #Todo: log
    print(msg)

#read pathes
def isGpsFile(path):
    (fname, ext) = os.path.splitext(path)
    ext = ext.lower()
    if ext == '.gpx':
        return True
    if ext == '.gdb':
        return True
    #assue the file is a gps file!
    return True

def isPicFile(path):
    (fname, ext) = os.path.splitext(path)
    ext = ext.lower()

    if ext == '.jpg' or ext == '.jpeg':
        return True
    return False

def getGpsDocument(path):
    try:
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
        logMsg("Error to open '%s'" % (path,), str(ex))
        return None

def getPicDocument(path):
    try:
        return PicDocument(path, conf.TZ)
    except Exception as ex:
        logMsg("cannot read the picture '%s'" % (path,), str(ex))
    return None

def __toGpx(src_path, output):
    (fname, ext) = os.path.splitext(src_path)
    if ext == '':
        raise ValueError("cannot identify input format")

    exe_file = conf.GPSBABEL_EXE
    tmp_in_path = os.path.join(tempfile.gettempdir(),  "giseditor_in.tmp")

    shutil.copyfile(src_path, tmp_in_path)  #to work around the problem of gpsbabel connot read non-ascii filename

    if output == 'string':
        cmd = '"%s" -i %s -f "%s" -o gpx,gpxver=1.1 -F -' % (exe_file, ext[1:], tmp_in_path)
        logPrint(cmd)
        output = subprocess.check_output(cmd, shell=True)  #@@! pythonW.exe caused 'WinError 6: the handler is invalid'
        result = output.decode("utf-8")
    elif output == 'file':
        tmp_out_path = os.path.join(tempfile.gettempdir(),  "giseditor_out.tmp")
        cmd = '"%s" -i %s -f "%s" -o gpx,gpxver=1.1 -F "%s"' % (exe_file, ext[1:], tmp_in_path, tmp_out_path)
        logPrint(cmd)
        subprocess.call(cmd, shell=True)
        result = tmp_out_path
    else:
        raise ValueError('Unknow type to convert to gpx: ' + output)

    os.remove(tmp_in_path) #clean tmp file before return
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

    def __init__(self, master):
        super().__init__(master)

        self.map_ctrl = MapController(self)

        #board
        self.__is_closed = False
        self.__bg_color=self['bg']
        self.__focused_wpt = None
        self.__focused_geo = None
        self.__map = None         #buffer disp image for restore map
        self.__map_attr = None
        self.__map_req = False
        self.__map_req_time = None
        self.__alter_time = None
        self.__pref_dir = None
        self.__pref_geo = None
        Thread(target=self.mapUpdater).start()

        #canvas items
        self.__canvas_map = None
        self.__canvas_sel_area = None

        #info
        info_frame = self.initMapInfo()
        info_frame.pack(side='top', expand=0, fill='x', anchor='nw')
        self.setMapInfo()

        #status
        status_frame = self.initStatusBar()
        status_frame.pack(side='bottom', expand=0, fill='x', anchor='nw')

        #display area
        self.__init_w= 800  #deprecated
        self.__init_h = 600  #deprecated
        self.disp_canvas = tk.Canvas(self, bg='#808080')
        self.disp_canvas.pack(expand=1, fill='both', anchor='n')
        if conf.OS == "Linux":
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

        frame = tk.Frame(self, relief='ridge', bd=1)

        #title
        info_mapname = tk.Label(frame, font=bfont, bg='lightgray')
        info_mapname.pack(side='left', expand=0, anchor='nw')
        info_mapname['text'] = self.map_ctrl.tile_map.title

        #level
        self.__info_level = self.__genInfoWidget(frame, font, 'Level', 2, self.onSetLevel)

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
        entry = tk.Entry(frame, font=font, width=width,textvariable=var)
        entry.pack(side='left', expand=0, anchor='nw')
        entry.variable = var
        
        if cb is not None:
            entry.bind('<Return>', cb)

        return entry

    def initStatusBar(self):
        font = 'Arialuni 10'
        bg='lightgray'
        frame = tk.Frame(self, relief='ridge', bd=1, bg=bg)
        self.__status_label = tk.Label(frame, font=font, bg=bg)
        self.__status_label.pack(side='left', expand=0, anchor='nw')
        return frame

    #{{{ operations
    def inSaveMode(self):
        return self.__canvas_sel_area is not None

    #release sources to exit
    def exit(self):
        self.__is_closed = True
        if self.inSaveMode():
            self.__canvas_sel_area.exit()
        self.map_ctrl.close()

    #}}} operations

    
    #{{{ Events
    def onSetLevel(self, e):
        if self.inSaveMode():
            return

        if e.widget == self.__info_level:
            try:
                level = int(e.widget.get())
            except:
                messagebox.showwarning('Bad Number', 'Please check level')
                return
            level = min(max(conf.MIN_SUPP_LEVEL, level), conf.MAX_SUPP_LEVEL)  #limit
            self.map_ctrl.level = level
            self.setMapInfo()
            self.resetMap()

    def onSetPos(self, e):
        #get pos
        try:
            pos = e.widget.get()
            x, y = pos.split(',')
            x = float(x.strip())
            y = float(y.strip())
            #print('x=%f, y=%f' % (x, y))
        except:
            messagebox.showwarning('Bad Format', "Please use format '%d,%d'")
            return

        #make geo according to the coordinate
        if e.widget == self.__info_67tm2:
            geo = GeoPoint(twd67_x=int(x*1000), twd67_y=int(y*1000))
        elif e.widget == self.__info_97tm2:
            geo = GeoPoint(twd69_x=int(x*1000), twd69_y=int(y*1000))
        elif e.widget == self.__info_97latlon:
            geo = GeoPoint(lat=x, lon=y)
        else:
            raise ValueError("Code flow error to set location")

        #check
        min_lon, min_lat = self.map_ctrl.tile_map.lower_corner
        max_lon, max_lat = self.map_ctrl.tile_map.upper_corner
        if not (min_lat <= geo.lat and geo.lat <= max_lat and min_lon <= geo.lon and geo.lon <= max_lon):
            messagebox.showwarning('Invalid Location', 'Please check location')
            return

        #focus geo on map
        self.map_ctrl.addMark(geo)
        self.setMapInfo(geo)
        self.resetMap(geo, force='wpt')

    def setMapInfo(self, geo=None):
        self.__info_level.variable.set(self.map_ctrl.level)

        if geo is not None:
            self.__info_97latlon.variable.set("%f, %f" % (geo.lat, geo.lon))
            self.__info_97tm2.variable.set("%.3f, %.3f" % (geo.twd97_x/1000, geo.twd97_y/1000))
            self.__info_67tm2.variable.set("%.3f, %.3f" % (geo.twd67_x/1000, geo.twd67_y/1000))

    def setStatus(self, txt):
        self.__status_label['text'] = txt

    def addGpx(self, gpx):
        if gpx is not None:
            self.map_ctrl.addGpxLayer(gpx)

    def addWpt(self, wpt):
        if wpt is not None:
            self.map_ctrl.addWpt(wpt)

    #deprecated
    '''
    def initDisp(self):
        print('initDisp', self.winfo_width(), self.winfo_height())
        pt = self.__getPrefGeoPt()
        disp_w = self.__init_w
        disp_h = self.__init_h
        self.resetMap(pt, disp_w, disp_h)
   '''

    def __getPrefGeoPt(self):
        #prefer track point
        for trk in self.map_ctrl.getAllTrks():
            for pt in trk:
                return pt

        #wpt
        for wpt in self.map_ctrl.getAllWpts():
            return wpt

        return None
        
    def onMouseWheel(self, event, delta):
        if self.inSaveMode():
            return

        ctrl = self.map_ctrl
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
        e.widget.focus_set() #to grap key events
        self.__mouse_down_pos = (e.x, e.y)

        geo = self.__focused_geo
        wpt = self.__focused_wpt

        #geo info
        self.setMapInfo(geo)

        #wpt. left->edit, right->menu
        if wpt is not None:
            if flag == 'left':
                self.onEditWpt(mode='single', wpt=wpt)
            elif flag == 'right':
                self.__wpt_rclick_menu.post(e.x_root, e.y_root)  #right menu for wpt
        #general right menu
        elif flag == 'right':
            self.__rclick_menu.post(e.x_root, e.y_root)  #right menu
        #unpost, if any
        else:
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

        #also set preferred dir if needed
        def getPrefDir(pathes):
            return None if not len(pathes) else os.path.dirname(pathes[0])
        if not self.__pref_dir:
            self.__pref_dir = getPrefDir(gps_path)
        if not self.__pref_dir:
            self.__pref_dir = getPrefDir(pic_path)

    #{{ Right click actions
    def onAddFiles(self):
        try:
            #add filenames
            def to_ask(init_dir):
                return filedialog.askopenfilenames(initialdir=init_dir)
            filenames = self.withPreferredDir(to_ask)
            self.addFiles(filenames)

            #go to pref geo, if no init_geo before
            if not self.__pref_geo:
                geo = self.__getPrefGeoPt()
                if geo:
                    self.__pref_geo = geo
                    self.setMapInfo(geo)
                    self.resetMap(geo)
        except Exception as ex:
            logMsg('Add Files Error', str(ex))

    def onAddWpt(self):
        geo = self.__focused_geo
        wpt = WayPoint(geo.lat, geo.lon)
        wpt.time = datetime.now()

        self.addWpt(wpt)
        self.setAlter('wpt')

    def onNumberWpt(self, name=None, time=None):
        wpt_list = self.map_ctrl.getAllWpts()
        if name is not None:
            wpt_list = sorted(wpt_list, key=lambda wpt: wpt.name)
        elif time is not None:
            wpt_list = sorted(wpt_list, key=lambda wpt: wpt.time)

        sn = 0
        for wpt in wpt_list:
            sn += 1
            wpt.name = "%02d %s" % (sn, wpt.name)

        self.setAlter('wpt')

    def onUnnumberWpt(self):
        wpt_list = self.map_ctrl.getAllWpts()
        for wpt in wpt_list:
            idx = wpt.name.find(' ')
            if idx >= 0 and wpt.name[:idx].isdigit():
                wpt.name = wpt.name[idx+1:]
        self.setAlter('wpt')

    def onToggleWptNmae(self):
        self.map_ctrl.hide_txt = not self.map_ctrl.hide_txt
        self.resetMap(force='wpt')

    def onApplySymbolRule(self):
        is_alter = False

        for wpt in self.map_ctrl.getAllWpts():
            sym = conf.getSymbol(wpt.name)
            if wpt.sym != sym:
                wpt.sym = sym
                is_alter = True

        if is_alter:
            self.setAlter('wpt')

    def onEditTrk(self, mode, trk=None):
        trk_list = self.map_ctrl.getAllTrks()
        if len(trk_list) == 0:
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
            
        for gpx in self.map_ctrl.gpx_layers:
            if gpx.splitTrk(split_fn):
                is_alter = True

        if is_alter:
            self.setAlter('trk')

    def onEditWpt(self, mode, wpt=None):
        wpt_list = self.map_ctrl.getAllWpts()
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

    def onImageSave(self):
        if self.inSaveMode():
            return

        #pos adjuster to align twd67
        def twd67PosAdjuster(pos):
            level = self.map_ctrl.level
            sel_geo = self.map_ctrl.geo.incPixel(pos[0], pos[1], level)
            #adjust to twd67
            x = round(sel_geo.twd67_x/1000)*1000
            y = round(sel_geo.twd67_y/1000)*1000
            adjust_geo = GeoPoint(twd67_x=x, twd67_y=y)
            return adjust_geo.diffPixel(sel_geo, level)

        #convert Geo Diff to Pixel diff, x/y->w/h
        def twd67GeoScaler(xy):
            level = self.map_ctrl.level
            #sel_geo = self.map_ctrl.geo.incPixel(pos[0], pos[1], level)
            sel_geo = self.map_ctrl.geo #use pos(0,0) as ref
            x = sel_geo.twd67_x + xy[0]*1000
            y = sel_geo.twd67_y - xy[1]*1000
            ext_geo = GeoPoint(twd67_x=x, twd67_y=y)
            return ext_geo.diffPixel(sel_geo, level)

        try:
            #select area
            self.__canvas_sel_area = AreaSelector(self.disp_canvas,
                    pos_adjuster=twd67PosAdjuster,
                    geo_scaler=twd67GeoScaler
                ) 
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
            org_level = self.map_ctrl.level
            w, h = self.__canvas_sel_area.size
            x, y = self.__canvas_sel_area.pos
            #bounding geo
            sel_geo = self.map_ctrl.geo.incPixel(x, y, org_level)  #upper-left
            ext_geo = sel_geo.incPixel(w, h, org_level)            #lower-right
            dx, dy = ext_geo.diffPixel(sel_geo, out_level)
            #get map
            map, attr = self.map_ctrl.getMap(dx, dy, geo=sel_geo, level=out_level)
            map.save(fpath, format='png')

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
        for gpx in self.map_ctrl.gpx_layers:
            doc.merge(gpx)

        #save
        doc.save(fpath)
        self.__alter_time = None

        return True

    #}} Right click actions

    def setAlter(self, alter):
        print(alter, 'is altered')
        self.__alter_time = datetime.now()
        self.resetMap(force=alter)

    def onClickMotion(self, event):
        if self.inSaveMode():
            return

        if self.__mouse_down_pos is not None:
            label = event.widget

            #print("change from ", self.__mouse_down_pos, " to " , (event.x, event.y))
            (last_x, last_y) = self.__mouse_down_pos
            self.map_ctrl.shiftGeoPixel(last_x - event.x, last_y - event.y)
            self.setMapInfo()
            self.resetMap()

            self.__mouse_down_pos = (event.x, event.y)

    def onMotion(self, event):
        if self.inSaveMode():
            return

        #draw point
        c = self.map_ctrl
        px=c.px + event.x
        py=c.py + event.y

        curr_wpt = c.getWptAt(px, py)
        prev_wpt = self.__focused_wpt
        if curr_wpt != prev_wpt:
            self.highlightWpt(curr_wpt, prev_wpt)

        #rec
        self.__focused_geo = GeoPoint(px=px, py=py, level=c.level)
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
            self.map_ctrl.drawWayPoint(map, self.__map_attr, wpt, 'red', 'white')
            self.__setMap(map)

    def highlightTrk(self, pts):
        if pts is None or len(pts) == 0:
            return
        map = self.__map.copy()
        self.map_ctrl.drawTrkPoint(map, self.__map_attr, pts, 'orange', 'black', width=8)
        self.__setMap(map)

    def onWptDeleted(self, wpt=None, prompt=True):
        if prompt:
            if not messagebox.askyesno('Delete Waypoint', "Delete the Waypoint?"):
                return False

        if wpt is None:
            wpt = self.__focused_wpt
            self.__focused_wpt = None

        self.map_ctrl.deleteWpt(wpt)
        self.setAlter('wpt')
        return True

    def onClickUp(self, event, flag):
        self.__mouse_down_pos = None

    def onResize(self, e):
        disp = self.disp_canvas
        if e.widget == disp:
            if not hasattr(disp, 'image'):  #init
                geo = self.__getPrefGeoPt()
                self.__pref_geo = geo  #rec
                if not geo:
                    geo = self.map_ctrl.geo
                self.setMapInfo(geo)
                self.resetMap(geo)
            elif e.width != disp.image.width() or e.height != disp.image.height():
                self.setMapInfo()
                self.resetMap()
            # raise AS, if any
            if self.inSaveMode():
                self.disp_canvas.tag_raise('AS')

    def mapUpdater(self):
        while not self.__is_closed:
            #sleep 3sec
            time.sleep(1)
            if self.__is_closed:
                break  #exit

            #update if req, prevent from frequent updating
            if self.__map_attr and self.__map_attr.fake_count and \
               self.__map_req and \
               (datetime.now()-self.__map_req_time).seconds >= 3:
                try:
                    self.resetMap()
                except Exception as ex:
                    print("Auto reset map error: ", str(ex))

    def resetMap(self, geo=None, w=None, h=None, force=None):
        if w is None: w = self.disp_canvas.winfo_width()
        if h is None: h = self.disp_canvas.winfo_height()

        if geo is not None:
            self.map_ctrl.geo = geo
            self.map_ctrl.shiftGeoPixel(-w/2, -h/2)

        def refreshMap():
            self.__map_req = True

        #request map
        self.__map_req = False #reset flag
        self.__map_req_time = datetime.now()
        self.__map, self.__map_attr = self.map_ctrl.getMap(w, h, force, cb=refreshMap)  #buffer the image

        #set map
        self.__setMap(self.__map)

        #set status
        if self.__map_attr.fake_count:
            txt = "Map Loading...(%d)" % (self.__map_attr.fake_count,)
            print(txt)
            self.setStatus(txt)
        else:
            print("Map Loading...OK")
            self.setStatus('')

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

class MapController:

    #{{ properties
    @property
    def tile_map(self): return self.__tile_map

    @property
    def tile_max_level(self): return self.__tile_map.level_max

    @property
    def tile_min_level(self): return self.__tile_map.level_min

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

    def __init__(self, parent):
        #def settings
        self.__parent = parent
        self.__tile_map = tile.getTM25Kv3TileMap(cache_dir=conf.CACHE_DIR)
        self.__geo = GeoPoint(lon=121.334754, lat=24.987969)  #default location
        self.__level = 14

        #image
        self.__cache_gpsmap = None
        self.__cache_basemap = None
        self.__cache_attr = None
        self.extra_p = 0
        self.pt_size = 3
        self.__font = conf.IMG_FONT
        self.hide_txt = False

        self.__dirty_map_info = None

        #layer
        self.__mark_wpt = None
        self.__pseudo_gpx = GpsDocument()  #to hold waypoints which not read from gpx
        self.gpx_layers = []
        self.gpx_layers.append(self.__pseudo_gpx)

    def close(self):
        self.__tile_map.close()

    def shiftGeoPixel(self, px, py):
        self.geo = self.geo.incPixel(int(px), int(py), self.__level)

    def addGpxLayer(self, gpx):
        self.gpx_layers.append(gpx)

    def addWpt(self, wpt):
        self.__pseudo_gpx.addWpt(wpt)

    def addMark(self, geo):
        wpt = WayPoint(geo.lat, geo.lon)
        wpt.sym = 'crosshair'
        self.__mark_wpt = wpt

    def deleteWpt(self, wpt):
        for gpx in self.gpx_layers:
            if wpt in gpx.way_points:
                gpx.way_points.remove(wpt)

    def getAllWpts(self):
        wpts = []
        for gpx in self.gpx_layers:
            for wpt in gpx.way_points:
                wpts.append(wpt)
        return wpts

    def getAllTrks(self):
        trks = []
        for gpx in self.gpx_layers:
            for trk in gpx.tracks:
                trks.append(trk)
        return trks

    def getWptAt(self, px, py):
        r = int(conf.ICON_SIZE/2)
        for wpt in self.getAllWpts():
            wpx, wpy = wpt.pixel(self.level)
            if abs(px-wpx) < r and abs(py-wpy) < r:
                return wpt
        return None

    def getMap(self, width, height, force=None, geo=None, level=None, cb=None):
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "gen map: begin")
        if geo is None: geo = self.geo
        if level is None: level = self.level
        px, py = geo.px(level), geo.py(level)

        #The image attributes with which we want to create a image compatible.
        req_attr = MapAttr(level, px, py, px+width, py+height, 0)
        map, attr = self.__genGpsMap(req_attr, force)

        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  crop map")
        map = self.__genCropMap(map, attr, req_attr)
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  draw coord")
        self.__drawTM2Coord(map, req_attr)

        #rec attr/cb or update later
        self.__dirty_map_info = (attr, cb) if attr.fake_count and cb else None

        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "gen map: done")
        req_attr.fake_count = attr.fake_count
        return map, req_attr

    def __isCacheValid(self, cache_map, req_attr):
        cache_attr = self.__cache_attr
        return cache_map and \
               cache_attr and \
               cache_attr.fake_count == 0 and \
               cache_attr.containsImgae(req_attr)

    def __genGpsMap(self, req_attr, force=None):
        if force not in ('all', 'gps', 'trk', 'wpt') and self.__isCacheValid(self.__cache_gpsmap, req_attr):
            #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  get gps map from cache")
            return (self.__cache_gpsmap, self.__cache_attr)

        map, attr = self.__genBaseMap(req_attr)
        self.__cache_gpsmap = map.copy()   #copy as cache

        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  draw trk")
        self.__drawTrk(self.__cache_gpsmap, attr)
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  draw wpt")
        self.__drawWpt(self.__cache_gpsmap, attr)

        return self.__cache_gpsmap, attr

    def __genBaseMap(self, req_attr):
        if self.__isCacheValid(self.__cache_basemap, req_attr):
            return (self.__cache_basemap, self.__cache_attr)

        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  gen base map")
        level = min(max(self.tile_min_level, req_attr.level), self.tile_max_level)

        if req_attr.level == level:
            tile_map = self.__genTileMap(req_attr, self.extra_p)
        else:
            #get approx map
            aprx_attr = req_attr.zoomToLevel(level)
            extra_p = self.extra_p * 2**(level - req_attr.level)
            aprx_map, aprx_attr = self.__genTileMap(aprx_attr, extra_p)
            #zoom to request level
            tile_map = self.__genZoomMap(aprx_map, aprx_attr, req_attr.level)

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

    #return tile no. of left, right, upper, lower
    def __tileRangeOfAttr(self, map_attr, extra_p=0):
        (t_left, t_upper) = TileSystem.getTileXYByPixcelXY(map_attr.left_px - extra_p, map_attr.up_py - extra_p)
        (t_right, t_lower) = TileSystem.getTileXYByPixcelXY(map_attr.right_px + extra_p, map_attr.low_py + extra_p)
        return (t_left, t_right, t_upper, t_lower)

    def __updateDirtyMap(self, level, x, y):
        def tileInAttr(level, x, y, attr):
            #handle psudo level beyond min level or max level
            crop_level = min(max(self.tile_min_level, attr.level), self.tile_max_level)
            if crop_level != attr.level:
                attr = attr.zoomToLevel(crop_level)
            #check range
            if level == attr.level:
                t_left, t_right, t_upper, t_lower = box = self.__tileRangeOfAttr(attr, self.extra_p)
                return (t_left <= x and x <= t_right) and (t_upper <= y and y <= t_lower)
            return False

        if not self.__dirty_map_info:
            return
        attr, cb = self.__dirty_map_info
        if tileInAttr(level, x, y, attr):
            print('UPDATE is available.')
            cb()

    def __genTileMap(self, map_attr, extra_p):
        #get tile x, y.
        t_left, t_right, t_upper, t_lower = self.__tileRangeOfAttr(map_attr, extra_p)
        tx_num = t_right - t_left +1
        ty_num = t_lower - t_upper +1

        #gen image
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "paste tile...")
        disp_map = Image.new("RGBA", (tx_num*256, ty_num*256))
        fake_count = 0
        self.__paste_count = tx_num*ty_num
        for x in range(tx_num):
            for y in range(ty_num):
                tile = self.__tile_map.getTile(map_attr.level, t_left +x, t_upper +y, self.__updateDirtyMap)
                if tile.is_fake:
                    fake_count += 1
                disp_map.paste(tile, (x*256, y*256))
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "paste tile...done")

        #reset map_attr
        disp_attr = MapAttr(map_attr.level, t_left*256, t_upper*256, (t_right+1)*256 -1, (t_lower+1)*256 -1, fake_count)

        return  (disp_map, disp_attr)

    def __drawTrk(self, map, map_attr):
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "draw gpx...")
        if len(self.gpx_layers) == 0:
            return

        draw = ImageDraw.Draw(map)

        for gpx in self.gpx_layers:
            #draw tracks
            #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "draw gpx...")
            for trk in gpx.tracks:
                if self.isTrackInImage(trk, map_attr):
                    self.drawTrkPoint(map, map_attr, trk, trk.color, draw=draw)

        #recycle draw object
        del draw

    def drawTrkPoint(self, map, map_attr, pts, color, bg_color=None, draw=None, width=2):
        if pts is None or len(pts) == 0:
            return

        bg_width = width + 4
        _draw = draw if draw is not None else ImageDraw.Draw(map)

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

        draw = ImageDraw.Draw(map)
        for wpt in wpts:
            (px, py) = wpt.pixel(map_attr.level)
            self.drawWayPoint(map, map_attr, wpt, "black", draw=draw)
        del draw

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

        if bg_color is not None:
            r = ceil(conf.ICON_SIZE/sqrt(2))
            _draw.ellipse((px-r, py-r, px+r, py+r), fill=bg_color, outline='gray')

        #paste icon
        if wpt.sym is not None:
            icon = conf.getIcon(wpt.sym)
            if icon is not None:
                if icon.mode == 'RGBA':
                    map.paste(icon, (px-adj, py-adj), icon)
                elif icon.mode == 'LA' or (icon.mode == 'P' and 'transparency' in icon.info):
                    mask = icon.convert('RGBA')
                    map.paste(icon, (px-adj, py-adj), mask)
                else:
                    print("Warning: Icon for '%s' with mode %s is not ransparency" % (wpt.sym, icon.mode))
                    map.paste(icon, (px-adj, py-adj))

        #draw point   //replace by icon
        #n = self.pt_size
        #_draw.ellipse((px-n, py-n, px+n, py+n), fill=color, outline='white')

        #draw text
        if not self.hide_txt:
            txt = wpt.name
            font = self.__font
            px, py = px +adj, py -adj  #adjust position for aligning icon
            _draw.text((px+1, py+1), txt, fill="white", font=font)
            _draw.text((px-1, py-1), txt, fill="white", font=font)
            _draw.text((px, py), txt, fill=txt_color, font=font)

        if draw is None:
            del _draw


    def __genCropMap(self, map, src_attr, dst_attr):
        left  = dst_attr.left_px - src_attr.left_px
        up    = dst_attr.up_py - src_attr.up_py
        right = dst_attr.right_px - src_attr.left_px
        low   = dst_attr.low_py - src_attr.up_py
        img2 = map.crop((left, up, right, low))
        return img2

    def __drawTM2Coord(self, map, attr):

        if attr.level <= 12:  #too crowded to show
            return

        #set draw
        py_shift = 20
        font = self.__font
        draw = ImageDraw.Draw(map)

        #get xy of TM2
        (left_x, up_y) = self.getTWD67TM2ByPixcelXY(attr.left_px, attr.up_py, attr.level)
        (right_x, low_y) = self.getTWD67TM2ByPixcelXY(attr.right_px, attr.low_py, attr.level)

        #draw TM2' x per KM
        for x in range(ceil(left_x/1000), floor(right_x/1000) +1):
            #print("tm: ", x)
            (px, py) = self.getPixcelXYByTWD67TM2(x*1000, low_y, attr.level)
            px -= attr.left_px
            py -= attr.up_py
            draw.text((px, py - py_shift), str(x), fill="black", font=font)

        #draw TM2' y per KM
        for y in range(ceil(low_y/1000), floor(up_y/1000) +1):
            #print("tm: ", y)
            (px, py) = self.getPixcelXYByTWD67TM2(left_x, y*1000, attr.level)
            px -= attr.left_px
            py -= attr.up_py
            draw.text((px, py -py_shift), str(y), fill="black", font=font)

        del draw


    @staticmethod
    def getTWD67TM2ByPixcelXY(px, py, level):
        geo = GeoPoint(px=px, py=py, level=level)
        return (geo.twd67_x, geo.twd67_y)

    @staticmethod
    def getPixcelXYByTWD67TM2(x, y, level):
        geo = GeoPoint(twd67_x=x, twd67_y=y)
        return geo.pixel(level)

#record image atrr
class MapAttr:
    def __init__(self, level, left_px, up_py, right_px, low_py, fake_count):
        #self.img = None
        self.level = level
        self.left_px = left_px
        self.up_py = up_py
        self.right_px = right_px
        self.low_py = low_py
        self.fake_count = fake_count

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
            return MapAttr(level, self.left_px << s, self.up_py << s, self.right_px << s, self.low_py << s, self.fake_count)
        elif self.level > level:
            s = self.level - level
            return MapAttr(level, self.left_px >> s, self.up_py >> s, self.right_px >> s, self.low_py >> s, self.fake_count)
        else:
            return self

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
        if conf.OS == 'Linux':
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
            self._curr_wpt.sym = conf.getSymbol(name)
            self._is_changed = True
            self.showWptIcon(self._curr_wpt)

            self.onAltered('wpt')
            self.highlightWpt(self._curr_wpt)

    def onFocusChanged(self, *args):
        self.highlightWpt(self._curr_wpt)

    def onEditSymRule(self):
        SymRuleBoard(self)
    
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
        self.__img_sz = (img_w, img_h) = (600, 450)
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
        icon = ImageTk.PhotoImage(conf.getIcon(wpt.sym))
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
            on_motion = lambda e: self.onMotion(e)

            #icon
            icon = ImageTk.PhotoImage(conf.getIcon(w.sym))
            icon_label = tk.Label(frame, image=icon, anchor='e')
            icon_label.image=icon
            icon_label.bind('<Motion>', on_motion)
            icon_label.grid(row=row, column=0, sticky='news')

            name_label = tk.Label(frame, text=w.name, font=font, anchor='w')
            name_label.bind('<Motion>', on_motion)
            name_label.grid(row=row, column=1, sticky='news')

            pos_txt = conf.getPtPosText(w, fmt='%.3f\n%.3f')
            pos_label = tk.Label(frame, text=pos_txt, font=font)
            pos_label.bind('<Motion>', on_motion)
            pos_label.grid(row=row, column=2, sticky='news')

            ele_label = tk.Label(frame, text=conf.getPtEleText(w), font=font)
            ele_label.bind('<Motion>', on_motion)
            ele_label.grid(row=row, column=3, sticky='news')

            time_label = tk.Label(frame, text=conf.getPtTimeText(w), font=font)
            time_label.bind('<Motion>', on_motion)
            time_label.grid(row=row, column=4, sticky='news')

            #save
            self.__widgets[w] = (
                    icon_label,
                    name_label,
                    pos_label,
                    ele_label,
                    time_label
            )

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
        self.pt_list.config(selectmode='extended', yscrollcommand=pt_scroll.set, width=43, height=30)
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
        if conf.OS == 'Linux':
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
        self._var_color.trace('w', self.onColorChanged)
        self.__color_entry = tk.Entry(frame, font=font, textvariable=self._var_color)
        self.__color_entry.grid(row=1, column=1, sticky='w')
        self.__color_entry_bg = self.__color_entry['bg']

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

        #title
        self.title(trk.name)

        #info
        self._var_name.set(trk.name)
        self._var_color.set(trk.color)

        #button state
        idx = self._trk_list.index(trk)
        sz = len(self._trk_list)
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

class SymBoard(tk.Toplevel):

    @property
    def sym(self): return self.__sym

    @sym.setter
    def sym(self, val):
        self.__sym = val
        if val is None:
            self.selectSymWidget(None)
        else:
            val = conf._tosymkey(val)
            w = self.__widgets.get(val)
            self.selectSymWidget(w)

    @property
    def pos(self): return self.__pos

    @pos.setter
    def pos(self, val):
        val = (0,0) if val is None else getPrefCornerPos(self, val)
        self.geometry('+%d+%d' % val)
        self.__pos = val

    def __init__(self, master=None):
        super().__init__(master)

        self.__parent = None #for show/onClosed
        self.__col_sz = 20
        self.__bg_color = self.cget('bg')
        self.__ext_bg_color = 'gray'
        self.__hl_bg_color = 'lightblue'
        self.__filter_bg_color = 'red'
        self.__sym = None
        self.__curr_widget = None
        self.__widgets = {}
        self.__pos = (0, 0)

        #board
        self.title('')
        self.resizable(0, 0)
        self.bind('<Escape>', self.onClosed)
        self.protocol('WM_DELETE_WINDOW', lambda: self.onClosed(None))

        #init
        dir_sym = conf.getIconPath().keys()
        self.__def_sym = conf.getDefSymList()
        self.__ext_sym = listdiff(dir_sym, self.__def_sym)

        sn = 0
        for sym in self.__def_sym:
            self.showSym(sym, sn, self.__bg_color)
            sn += 1

        sn = self.getNextRowSn(sn)
        for sym in self.__ext_sym:
            self.showSym(sym, sn, self.__ext_bg_color)
            sn += 1

        span = max(1, int(self.__col_sz/3))
        row, col = self.toRowCol(self.getNextRowSn(sn))
        self.__var_filter = tk.StringVar()
        self.__var_filter.trace('w', self.onFilterSym)
        filter_entry = tk.Entry(self, textvariable=self.__var_filter)
        filter_entry.grid(row=row, column=col+self.__col_sz-span, columnspan=span, sticky='news')

        #hidden
        self.withdraw()  #for silent update
        self.visible = tk.BooleanVar(value=False)

        #update window size
        self.update()  

    def show(self, parent):
        self.__parent = parent #rec

        #UI
        self.transient(parent)  #remove max/min buttons
        self.focus_set()  #prevent key-press sent back to parent
        
        self.deiconify() #show
        self.visible.set(True)

        self.grab_set()   #disalbe interact of parent
        parent.wait_variable(self.visible)

    def onClosed(self, e):
        if self.__parent is not None:
            self.__parent.focus_set()
        self.grab_release()

        #self.destroy()
        self.withdraw()
        self.visible.set(False)

    def toRowCol(self, sn):
        return int(sn/self.__col_sz), sn%self.__col_sz

    def getNextRowSn(self, sn):
        return ceil(sn/self.__col_sz) * self.__col_sz

    def showSym(self, sym, sn, bg_color):

        txt = ""
        icon = ImageTk.PhotoImage(conf.getIcon(sym))

        disp = tk.Label(self)
        disp.config(image=icon, text=txt, compound='left', anchor='w', bg=bg_color)
        disp.image=icon

        row, col = self.toRowCol(sn)
        disp.grid(row=row, column=col, sticky='we')
        disp.bind('<Motion>', self.onMotion)
        disp.bind('<Button-1>', self.onClick)

        #save
        disp.sym = sym
        self.__widgets[sym] = disp

    def onMotion(self, e):
        self.selectSymWidget(e.widget)

    def onFilterSym(self, *args):
        #reet 
        self.sym = None

        f = self.__var_filter.get().lower()
        for w in self.children.values():
            if hasattr(w, 'sym'):
                sym = w.sym.lower()
                w['bg'] = self.__filter_bg_color if f and f in sym else self.getWidgetsBgColor(w)

    def getWidgetsBgColor(self, widget):
        return self.__bg_color if widget.sym in self.__def_sym else self.__ext_bg_color

    #careful: widget could be None
    def selectSymWidget(self, widget):
        if self.__curr_widget != widget:
            self.unhighlight(self.__curr_widget)
            self.highlight(widget)
        self.__curr_widget = widget

    def unhighlight(self, widget):
        if widget is not None:
            if widget['bg'] != self.__filter_bg_color:
                widget['bg'] = self.getWidgetsBgColor(widget)

    def highlight(self, widget):
        if widget is not None:
            if widget['bg'] != self.__filter_bg_color:
                widget['bg'] = self.__hl_bg_color
            self.title(widget.sym)
        else:
            self.title("")

    def onClick(self, e):
        self.__sym = e.widget.sym
        self.onClosed(None)

class SymRuleBoard(tk.Toplevel):
    def __init__(self, master, pos=None):
        super().__init__(master)

        self.__bg_color = self.cget('bg')
        self.__hl_bg_color = 'lightblue'
        self.__focused_rule = None
        self.__widgets = {}
        self.__var_widgets = {}
        self.__rules = conf.Sym_rules
        if not hasattr(self.__rules, 'is_altered'):
            self.__rules.is_altered = tk.BooleanVar(value=False)
        self.__font = 'Arialuni 12'
        self.__bfont = 'Arialuni 12 bold'

        #board
        pos = '+%d+%d' % (pos[0], pos[1]) if pos is not None else '+0+0'
        self.geometry(pos)
        self.title('Symbol Rules')
        self.bind('<Escape>', self.onClosed)
        self.protocol('WM_DELETE_WINDOW', lambda: self.onClosed(None))

        self.init()
        self.initRightMenu()
        self.initTypeMenu()

        #set focus
        self.transient(self.master)
        self.focus_set()
        if conf.OS == 'Linux':
            self.withdraw() #ensure update silently
            self.update()   #ensure viewable before grab, 
            self.deiconify() #show
        self.grab_set()
        self.wait_window(self)

    def onClosed(self, e):
        self.master.focus_set()
        self.destroy()

    def init(self):
        self.sf = pmw.ScrolledFrame(self, usehullsize = 1, hull_width = 450, hull_height = 600)
        self.sf.pack(side='bottom', anchor='nw', fill = 'both', expand = 1)

        self.__dec_btn = tk.Button(self, text='↑', state='disabled', command=lambda: self.onPriorityMove(-1))
        self.__dec_btn.pack(side='right', anchor='ne')

        self.__inc_btn = tk.Button(self, text='↓', state='disabled', command=lambda: self.onPriorityMove(1))
        self.__inc_btn.pack(side='right', anchor='ne')

        self.__save_btn = tk.Button(self, text='Save', command=lambda: self.onSave())
        self.__save_btn.pack(side='left', anchor='nw')
        self.__rules.is_altered.trace('w', self.setSaveButtonState)
        self.setSaveButtonState() #init invoke

        frame = self.sf.interior()
        bfont = self.__bfont

        row = 0
        #tk.Label(frame, text='Enabled', font=bfont).grid(row=row, column=0)
        tk.Label(frame, text='Type',  font=bfont, anchor='w').grid(row=row, column=1, sticky='news')
        tk.Label(frame, text='Text',  font=bfont, anchor='w').grid(row=row, column=2, sticky='news')
        tk.Label(frame, text='Symbol', font=bfont, anchor='w').grid(row=row, column=3, sticky='news')

        for rule in self.__rules:
            row += 1
            self.genRuleWidgets(rule, row)  #view
            self.setRuleWidgets(rule)      #data

    def setSaveButtonState(self, *args):
        self.__save_btn['state'] = 'normal' if self.__rules.is_altered.get() else 'disabled' 

    def genRuleWidgets(self, rule, row):
        bfont = self.__bfont
        font = self.__font

        #config
        frame = self.sf.interior()
        en_label = tk.Label(frame, font=bfont, anchor='e')
        self.setWidgetCommon(en_label, row, 0)

        type_label = tk.Label(frame, font=font, anchor='w')
        self.setWidgetCommon(type_label, row, 1)

        #text_label = tk.Label(frame, font=font)
        text_label = tk.Entry(frame, font=font, relief='flat', \
                state='disabled', disabledforeground='black',disabledbackground=self.__bg_color)
        self.setWidgetEditable(text_label, self.onTextWrite)
        self.setWidgetCommon(text_label, row, 2)

        sym_label = tk.Label(frame, font=font, compound='left', anchor='w')
        self.setWidgetCommon(sym_label, row, 3)

        #save
        self.__widgets[rule] = (
                en_label,
                type_label,
                text_label,
                sym_label
        )

    def onSave(self):
        self.__rules.save()
        self.__rules.is_altered.set(False)

    def getWidgetsRow(self, rule):
        w = self.__widgets[rule]
        row = w[0].grid_info()['row']
        return row

    def resetWidgetsRow(self, widgets, row):
        col = 0
        for w in widgets:
            w.grid(row=row, column=col, sticky='news')
            col += 1

    def shiftWidgetsRow(self, rule, inc):
        widgets = self.__widgets[rule]
        row = self.getWidgetsRow(rule)

        for w in widgets: w.grid_forget()
        self.resetWidgetsRow(widgets, row+inc)

    def swapWidgetsRow(self, rule1, rule2):
        w1 = self.__widgets[rule1]
        w2 = self.__widgets[rule2]

        r1 = self.getWidgetsRow(rule1)
        r2 = self.getWidgetsRow(rule2)

        for w in w1: w.grid_forget()
        for w in w2: w.grid_forget()

        self.resetWidgetsRow(w1, r2)
        self.resetWidgetsRow(w2, r1)

    def onPriorityMove(self, inc):
        rule1 = self.__focused_rule
        idx1 = self.__rules.index(rule1)
        idx2 = idx1+inc
        rule2 = self.__rules[idx2]

        #view
        self.swapWidgetsRow(rule1, rule2)

        #data
        self.__rules.remove(rule1)
        self.__rules.insert(idx2, rule1)

    def setRuleWidgets(self, rule):
        en_w, type_w, txt_w, sym_w = self.__widgets[rule]

        en_text = 'v' if rule.enabled else 'x'
        en_color = 'green' if rule.enabled else 'red'
        en_w.config(text=en_text, fg=en_color)

        type_txt = SymRuleType.toStr(rule.type)
        type_w.config(text=type_txt)

        #txt_w.config(text=rule.text)
        txt_w.variable.set(rule.text)

        icon = ImageTk.PhotoImage(conf.getIcon(rule.symbol))
        sym_w.config(image=icon, text=rule.symbol)
        sym_w.image=icon

    def setWidgetCommon(self, w, row, col):
        w.bind('<Motion>', self.onMotion)
        w.bind('<Button-1>', self.onClick)
        w.bind('<Button-3>', self.onRightClick)
        w.grid(row=row, column=col, sticky='news')

    def getRuleOfWidget(self, widget):
        for rule, widgets in self.__widgets.items():
            if widget in widgets:
                return rule
        return None

    def onMotion(self, e):
        prev = self.__focused_rule
        curr = self.getRuleOfWidget(e.widget)

        #highligt/unhighlight
        if prev != curr:
            self.setRuleBgColor(prev, self.__bg_color)
            self.setRuleBgColor(curr, self.__hl_bg_color)
                
        #rec
        self.__focused_rule = curr
        self.__dec_btn.config(state=('disabled' if curr == conf.Sym_rules[0] else 'normal'))
        self.__inc_btn.config(state=('disabled' if curr == conf.Sym_rules[-1] else 'normal'))

    def setRuleBgColor(self, rule, color):
        if rule is not None:
            for w in self.__widgets[rule]:
                if w.cget('state') == 'disabled':
                    w.config(disabledbackground=color)
                else:
                    w.config(bg=color)

    def setWidgetEditable(self, w, cb):
        var = tk.StringVar()
        w.config(textvariable=var)
        w.variable = var  #keep ref: widget->var
        self.__var_widgets[str(var)] = w  #keep ref: var->widget

        def onEnterEdit(e):
            e.widget.config(state='normal')
            e.widget.focus_set()

        def onLeaveEdit(e):
            if e.widget.cget('state') == 'normal':
                e.widget.config(state='disabled')

        def onEditWrite(*args):
            var_name = args[0]
            widget = self.__var_widgets.get(var_name)
            cb(widget)

        w.bind('<Double-Button-1>', onEnterEdit)
        w.bind('<Leave>', onLeaveEdit)
        w.bind('<Return>', onLeaveEdit)
        w.variable.trace_variable('w', onEditWrite)

    def initTypeMenu(self):
        menu = tk.Menu(self, tearoff=0)
        #for t in SymRuleType.types():
        #    txt = SymRuleType.toStr(t)
        #    menu.add_command(label=txt, command=lambda:self.onTypeWrite(t))

        menu.add_command(label='Contain', command=lambda: self.onTypeWrite(SymRuleType.CONTAIN))
        menu.add_command(label='BeginWith', command=lambda: self.onTypeWrite(SymRuleType.BEGIN_WITH))
        menu.add_command(label='EndWith', command=lambda: self.onTypeWrite(SymRuleType.END_WITH))
        menu.add_command(label='Equal', command=lambda: self.onTypeWrite(SymRuleType.EQUAL))
        menu.add_command(label='Regex', command=lambda: self.onTypeWrite(SymRuleType.REGEX))

        self.__type_menu = menu

    def onClick(self, e):
        rule = self.getRuleOfWidget(e.widget)
        en_w, type_w, txt_w, sym_w = self.__widgets[rule]
        pos = (e.x_root, e.y_root)

        #edit
        if e.widget == en_w:
            rule.enabled = not rule.enabled
            self.setRuleWidgets(rule)
            self.__rules.is_altered.set(True)
        elif e.widget == type_w:
            self.__type_menu.post(e.x_root, e.y_root)
        elif e.widget == txt_w:
            pass
        elif e.widget == sym_w:
            sym = askSym(self, pos, rule.symbol)
            if sym is not None and rule.symbol != sym:
                rule.symbol = sym
                self.setRuleWidgets(rule)
                self.__rules.is_altered.set(True)

    def onTextWrite(self, widget):
        var = widget.variable
        rule = self.getRuleOfWidget(widget)
        if rule.text != var.get():
            #print('rule change text from ', rule.text, 'to', var.get() )
            rule.text = var.get()
            self.__rules.is_altered.set(True)

    def onTypeWrite(self, t):
        #print('set type to ', str(t))
        rule = self.__focused_rule
        if rule.type != t:
            rule.type = t
            self.setRuleWidgets(rule)
            self.__rules.is_altered.set(True)

    #{{ add/dup rule

    def onRightClick(self, e):
        self.__add_menu.post(e.x_root, e.y_root)

    def initRightMenu(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label='Insert rule', command=self.onAddRule)
        menu.add_command(label='Duplicate rule', command=lambda: self.onAddRule(dup=1))
        menu.add_separator()
        menu.add_command(label='Remove rule', command=self.onRemoveRule)
        self.__add_menu = menu

    def onAddRule(self, dup=0):
        rule = self.__focused_rule
        idx = self.__rules.index(rule)
        row = self.getWidgetsRow(rule)
        new_rule = rule.clone() if dup == 1 else SymRule()

        #data
        self.__rules.insert(idx, new_rule)

        #view, to shift
        for i in range(len(self.__rules)-1, idx , -1):
            rule = self.__rules[i]
            self.shiftWidgetsRow(rule, 1)

        #view, to insert new
        self.genRuleWidgets(new_rule, row)
        self.setRuleWidgets(new_rule)
        self.__rules.is_altered.set(True)

    def onRemoveRule(self):
        rule = self.__focused_rule
        widgets = self.__widgets[rule]

        #data
        self.__rules.remove(rule)
        self.__widgets.pop(rule, None)

        #view
        for w in widgets:
            w.grid_forget()

        self.__focused_rule = None
        self.__rules.is_altered.set(True)
    #}}

__sym_board = None
def askSym(parent, pos=None, init_sym=None):
    #sym_board = SymBoard(master, pos, init_sym)
    #return sym_board.sym

    global __sym_board

    if __sym_board is None:
        __sym_board = SymBoard()
    __sym_board.pos = pos
    __sym_board.sym = init_sym

    __sym_board.show(parent)
    return __sym_board.sym

def listdiff(list1, list2):
    result = []
    for e in list1:
        if not e in list2:
            result.append(e)
    return result

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
    draw = ImageDraw.Draw(img)
    draw.text( (int(w/2-20), int(h/2)), text, fill='lightgray', font=conf.IMG_FONT)
    del draw

    return img


def isExit(disp_board):

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
    if isExit(disp_board):
        disp_board.exit()
        root.destroy()

def getTitleText():
    txt = "GisEditor"
    if len(sys.argv) > 1:
        txt += " - "
        for arg in sys.argv[1:]:
            txt += path.basename(arg)
            txt += ' '
    return txt

if __name__ == '__main__':
    try:
        #create window
        root = tk.Tk()
        pmw.initialise(root)
        root.iconbitmap(conf.EXE_ICON)
        root.title(getTitleText())
        root.geometry('950x700+200+0')

        pad_ = 2
        disp_board = MapBoard(root)
        disp_board.pack(side='right', anchor='se', expand=1, fill='both', padx=pad_, pady=pad_)
        root.protocol('WM_DELETE_WINDOW', lambda: onExit(root, disp_board))

        #add files
        disp_board.addFiles(sys.argv[1:])

        #disp_board.initDisp()
        root.mainloop()
    except Exception as ex:
        messagebox.showwarning('Startup failed', str(ex))
