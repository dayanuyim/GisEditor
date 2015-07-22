#!/usr/bin/env python3

import os
import subprocess
import sys
import tkinter as tk
import Pmw as pmw
import urllib.request
import shutil
import tempfile
from os import path
from PIL import Image, ImageTk, ImageDraw, ImageFont
from math import floor, ceil, sqrt
from tkinter import messagebox, filedialog
from datetime import datetime

#my modules
import tile
import conf
from tile import  TileSystem, TileMap, GeoPoint
from coord import  CoordinateSystem
from gpx import GpsDocument, WayPoint
from pic import PicDocument


class DispBoard(tk.Frame):
    @property
    def is_changed(self): return self.__is_changed

    def __init__(self, master):
        super().__init__(master)

        self.map_ctrl = MapController()

        #board
        self.bg_color='#D0D0D0'
        self.config(bg=self.bg_color)
        self.__focused_wpt = None
        self.__img = None         #buffer disp image for restore map
        self.__is_changed = False

        #info
        self.info_label = tk.Label(self, font='24', anchor='w', bg=self.bg_color)
        self.setMapInfo()
        self.info_label.pack(expand=0, fill='x', anchor='n')

        #display area
        self.__init_w= 800  #deprecated
        self.__init_h = 600  #deprecated
        self.disp_label = tk.Label(self, bg='#808080')
        self.disp_label.pack(expand=1, fill='both', anchor='n')
        self.disp_label.bind('<MouseWheel>', self.onMouseWheel)
        self.disp_label.bind('<Motion>', self.onMotion)
        self.disp_label.bind("<Button-1>", self.onClickDown)
        self.disp_label.bind("<Button-3>", self.onRightClickDown)
        self.disp_label.bind("<Button1-Motion>", self.onClickMotion)
        self.disp_label.bind("<Button1-ButtonRelease>", self.onClickUp)
        self.disp_label.bind("<Configure>", self.onResize)

        #right-click menu
        self.__rclick_menu = tk.Menu(self.disp_label, tearoff=0)
        self.__rclick_menu.add_command(label='Save to gpx...', underline=0, command=self.onGpxSave)
        self.__rclick_menu.add_separator()
        self.__rclick_menu.add_command(label='Add wpt')
        edit_wpt_menu = tk.Menu(self.__rclick_menu, tearoff=0)
        edit_wpt_menu.add_command(label='Edit 1-by-1', underline=5, command=lambda:self.onEditWpt(mode='single'))
        edit_wpt_menu.add_command(label='Edit in list', underline=5, command=lambda:self.onEditWpt(mode='list'))
        self.__rclick_menu.add_cascade(label='Edit waypoints...', menu=edit_wpt_menu)

        num_wpt_menu = tk.Menu(self.__rclick_menu, tearoff=0)
        num_wpt_menu.add_command(label='By time order', command=lambda:self.onNumberWpt(time=1))
        num_wpt_menu.add_command(label='By name order', command=lambda:self.onNumberWpt(name=1))
        self.__rclick_menu.add_cascade(label='Numbering wpt...', menu=num_wpt_menu)
        self.__rclick_menu.add_command(label='UnNumbering wpt', underline=0, command=self.onUnnumberWpt)
        self.__rclick_menu.add_command(label='Toggle wpt name', underline=0, command=self.onToggleWptNmae)
        self.__rclick_menu.add_separator()
        self.__rclick_menu.add_command(label='Edit tracks...', underline=5, command=self.onEditTrk)

        #wpt menu
        self.__wpt_menu = tk.Menu(self.disp_label, tearoff=0)
        self.__wpt_menu.add_command(label='Delete Wpt', underline=0, command=self.onDeleteWpt)

    def addGpx(self, gpx):
        self.map_ctrl.addGpxLayer(gpx)

    def addPic(self, pic):
        self.map_ctrl.addPicLayer(pic)

    #deprecated
    def initDisp(self):
        print('initDisp', self.winfo_width(), self.winfo_height())
        pt = self.__getPrefGeoPt()
        disp_w = self.__init_w
        disp_h = self.__init_h
        self.resetMap(pt, disp_w, disp_h)

    def __getPrefGeoPt(self):
        #prefer track point
        for trk in self.map_ctrl.getAllTrks():
            for pt in trk:
                return pt

        #wpt
        for wpt in self.map_ctrl.getAllWpts():
            return wpt

        return None
        
    def onMouseWheel(self, event):
        label = event.widget

        #set focused pixel
        self.map_ctrl.shiftGeoPixel(event.x, event.y)

        #level
        if event.delta > 0:
            self.map_ctrl.level += 1
        elif event.delta < 0:
            self.map_ctrl.level -= 1

        #set focused pixel again
        self.map_ctrl.shiftGeoPixel(-event.x, -event.y)

        self.setMapInfo()
        self.resetMap()

    def onClickDown(self, event):
        self.__mouse_down_pos = (event.x, event.y)

        #show lat/lon
        c = self.map_ctrl
        geo = GeoPoint(px=c.px + event.x, py=c.py + event.y, level=c.level) 
        (x_tm2_97, y_tm2_97) = CoordinateSystem.TWD97_LatLonToTWD97_TM2(geo.lat, geo.lon)
        (x_tm2_67, y_tm2_67) = CoordinateSystem.TWD97_TM2ToTWD67_TM2(x_tm2_97, y_tm2_97)

        txt = "LatLon/97: (%f, %f), TM2/97: (%.3f, %.3f), TM2/67: (%.3f, %.3f)" % (geo.lat, geo.lon, x_tm2_97/1000, y_tm2_97/1000, x_tm2_67/1000, y_tm2_67/1000)
        self.setMapInfo(txt=txt)

        #show wpt frame
        wpt = c.getWptAt(geo.px, geo.py)
        if wpt is not None:
            self.onEditWpt(mode='single', wpt=wpt)

    def onRightClickDown(self, event):
        if self.__focused_wpt is not None:
            self.__wpt_menu.post(event.x_root, event.y_root)
        else:
            self.__rclick_menu.post(event.x_root, event.y_root)

    #{{ Right click actions
    def onGpxSave(self):
        fpath = filedialog.asksaveasfilename(defaultextension=".gpx", filetypes=(("GPS Excahnge Format", ".gpx"), ("All Files", "*.*")) )
        if fpath is None or fpath == "":
            return False

        #gen gpx faile
        doc = GpsDocument()
        for gpx in self.map_ctrl.gpx_layers:
            doc.merge(gpx)
        for wpt in self.map_ctrl.pic_layers:
            doc.addWpt(wpt)

        #save
        doc.save(fpath)
        self.__is_changed = False

        return True

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

        self.resetMap()

    def onUnnumberWpt(self):
        wpt_list = self.map_ctrl.getAllWpts()
        for wpt in wpt_list:
            idx = wpt.name.find(' ')
            if idx >= 0 and wpt.name[:idx].isdigit():
                wpt.name = wpt.name[idx+1:]
        self.resetMap()

    def onToggleWptNmae(self):
        self.map_ctrl.hide_txt = not self.map_ctrl.hide_txt
        self.resetMap()

    def onEditTrk(self, trk=None):
        trk_list = self.map_ctrl.getAllTrks()
        trk_board = TrkBoard(self, trk_list, trk)
        self.__is_changed = self.__is_changed or trk_board.is_changed

    def onEditWpt(self, mode, wpt=None):
        wpt_list = self.map_ctrl.getAllWpts()
        if mode == 'single':
            wpt_board = WptSingleBoard(self, wpt_list, wpt)
        elif mode == 'list':
            wpt_board = WptListBoard(self, wpt_list, wpt)
        else:
            raise ValueError("WptBoade only supports mode: 'single' and 'list'")

        self.__is_changed = self.__is_changed or wpt_board.is_changed
        self.__focused_wpt = None
    #}} 


    def onClickMotion(self, event):
        if self.__mouse_down_pos is not None:
            label = event.widget

            #print("change from ", self.__mouse_down_pos, " to " , (event.x, event.y))
            (last_x, last_y) = self.__mouse_down_pos
            self.map_ctrl.shiftGeoPixel(last_x - event.x, last_y - event.y)
            self.setMapInfo()
            self.resetMap()

            self.__mouse_down_pos = (event.x, event.y)

    def onMotion(self, event):
        #draw point
        c = self.map_ctrl
        px=c.px + event.x
        py=c.py + event.y

        curr_wpt = c.getWptAt(px, py)
        prev_wpt = self.__focused_wpt
        if prev_wpt and curr_wpt != prev_wpt:
            if curr_wpt is None:  #highlight curr_wpt implies restore, so skip if curr_wpt is not None
                self.restore()
        if curr_wpt is not None:
            self.highlightWpt(curr_wpt)

        #rec
        self.__focused_wpt = curr_wpt

    def highlightWpt(self, wpt):
        if wpt is None:
            return

        #draw wpt
        c = self.map_ctrl
        img = self.__img.copy()
        img_attr = ImageAttr(c.level, c.px, c.py, c.px + img.size[0], c.py + img.size[1])
        c.drawWayPoint(img, img_attr, wpt, 'red', 'white')

        #set
        self.__setMap(img)

    def highlightTrk(self, pts):
        if pts is None or len(pts) == 0:
            return

        c = self.map_ctrl
        img = self.__img.copy()
        img_attr = ImageAttr(c.level, c.px, c.py, c.px + img.size[0], c.py + img.size[1])
        c.drawTrkPoint(img, img_attr, pts, 'orange', 'black', width=8)

        #set
        self.__setMap(img)

    def onDeleteWpt(self):
        wpt = self.__focused_wpt
        self.__focused_wpt = None
        self.deleteWpt(wpt)
        
    def deleteWpt(self, wpt):
        if wpt is not None:
            self.map_ctrl.deleteWpt(wpt)
            self.resetMap()

    def onClickUp(self, event):
        self.__mouse_down_pos = None

        #clear lat/lon
        #self.setMapInfo()

    def onResize(self, e):
        disp = self.disp_label
        if e.widget == disp:
            if not hasattr(disp, 'image'):  #init
                self.setMapInfo()
                self.resetMap(self.__getPrefGeoPt())
            elif e.width != disp.image.width() or e.height != disp.image.height():
                self.setMapInfo()
                self.resetMap()

    def setMapInfo(self, lat=None, lon=None, txt=None):
        c = self.map_ctrl
        if txt is not None:
            self.info_label.config(text="[%s] level: %s, %s" % (c.tile_map.getMapName(), c.level, txt))
        elif lat is not None and lon is not None:
            self.info_label.config(text="[%s] level: %s, lat: %f, lon: %f" % (c.tile_map.getMapName(), c.level, lat, lon))
        else:
            self.info_label.config(text="[%s] level: %s" % (c.tile_map.getMapName(), c.level))

    def resetMap(self, pt = None, w=None, h=None):
        if w is None: w = self.disp_label.winfo_width()
        if h is None: h = self.disp_label.winfo_height()

        if pt is not None:
            self.map_ctrl.lat = pt.lat
            self.map_ctrl.lon = pt.lon
            self.map_ctrl.shiftGeoPixel(-w/2, -h/2)

        self.__img = self.map_ctrl.getTileImage(w, h)  #buffer the image
        self.__setMap(self.__img)

    def restore(self):
        self.__setMap(self.__img)

    def __setMap(self, img):
        photo = ImageTk.PhotoImage(img)
        self.disp_label.config(image=photo)
        self.disp_label.image = photo #keep a ref

class MapController:

    #{{ properties
    @property
    def tile_map(self): return self.__tile_map

    @property
    def lat(self): return self.__geo.lat
    @lat.setter
    def lat(self, v): self.__geo.lat = v

    @property
    def lon(self): return self.__geo.lon
    @lon.setter
    def lon(self, v): self.__geo.lon = v

    @property
    def px(self): return self.__geo.px
    @px.setter
    def px(self, v): self.__geo.px = v

    @property
    def py(self): return self.__geo.py
    @py.setter
    def py(self, v): self.__geo.py = v

    @property
    def level(self): return self.__geo.level
    @level.setter
    def level(self, v): self.__geo.level = v

    def __init__(self):
        #def settings
        self.__tile_map = tile.getTM25Kv3TileMap(cache_dir=conf.CACHE_DIR)
        self.__geo = GeoPoint(lon=121.334754, lat=24.987969)  #default location
        self.__geo.level = 14

        #image
        self.disp_img = None
        self.disp_attr = None
        self.extra_p = 256
        self.pt_size = 3
        self.__font = conf.IMG_FONT
        self.hide_txt = False

        #layer
        self.gpx_layers = []
        self.pic_layers = []


    def shiftGeoPixel(self, px, py):
        self.__geo.px += int(px)
        self.__geo.py += int(py)

    def addGpxLayer(self, gpx):
        self.gpx_layers.append(gpx)

    def addPicLayer(self, pic):
        self.pic_layers.append(pic)

    def getAllWpts(self):
        wpts = []
        for gpx in self.gpx_layers:
            for wpt in gpx.way_points:
                wpts.append(wpt)
        for pic in self.pic_layers:
                wpts.append(pic)
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
            wpx, wpy = wpt.getPixel(self.level)
            if abs(px-wpx) < r and abs(py-wpy) < r:
                return wpt
        return None

    def deleteWpt(self, wpt):
        for gpx in self.gpx_layers:
            if wpt in gpx.way_points:
                gpx.way_points.remove(wpt)
        if wpt in self.pic_layers:
                self.pic_layers.remove(wpt)

    def getTileImage(self, width, height):

        #The image attributes with which we want to create a image compatible.
        img_attr = ImageAttr(self.level, self.px, self.py, self.px + width, self.py + height)

        print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "gen map: begin")
        #gen new map if need
        if self.disp_attr is None or not self.disp_attr.containsImgae(img_attr):
            print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  gen base map")
            (self.disp_img, self.disp_attr) = self.__genBaseMap(img_attr)
            print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  draw trk")
            self.__drawTrk(self.disp_img, self.disp_attr)

        #crop by width/height
        print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  crop map")
        img = self.__getCropMap(img_attr)
        print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  draw coord")
        self.__drawTM2Coord(img, img_attr)
        print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "  draw wpt")
        self.__drawWpt(img, img_attr)
        print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "gen map: done")
        return img

    def __genBaseMap(self, img_attr):
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "gen base map...")
        level_max = self.__tile_map.level_max
        level_min = self.__tile_map.level_min
        level = max(self.__tile_map.level_min, min(img_attr.level, self.__tile_map.level_max))

        if img_attr.level == level:
            return self.__genTileMap(img_attr, self.extra_p)
        else:
            zoom_attr = img_attr.zoomToLevel(level)
            extra_p = self.extra_p * 2**(level - img_attr.level)

            (img, attr) = self.__genTileMap(zoom_attr, extra_p)
            return self.__zoomImage(img, attr, img_attr.level)

    def __zoomImage(self, img, attr, level):
        s = level - attr.level
        if s == 0:
            return (img, attr)
        elif s > 0:
            w = (attr.right_px - attr.left_px) << s
            h = (attr.low_py - attr.up_py) << s
        else:
            w = (attr.right_px - attr.left_px) >> (-s)
            h = (attr.low_py - attr.up_py) >> (-s)

        #Image.NEAREST, Image.BILINEAR, Image.BICUBIC, or Image.LANCZOS 
        img = img.resize((w,h), Image.BILINEAR)

        #the attr of resized image
        attr = attr.zoomToLevel(level)

        return (img, attr)

    def __genTileMap(self, img_attr, extra_p):
        #get tile x, y.
        (t_left, t_upper) = TileSystem.getTileXYByPixcelXY(img_attr.left_px - extra_p, img_attr.up_py - extra_p)
        (t_right, t_lower) = TileSystem.getTileXYByPixcelXY(img_attr.right_px + extra_p, img_attr.low_py + extra_p)

        tx_num = t_right - t_left +1
        ty_num = t_lower - t_upper +1

        #gen image
        disp_img = Image.new("RGBA", (tx_num*256, ty_num*256))
        for x in range(tx_num):
            for y in range(ty_num):
                tile = self.__tile_map.getTileByTileXY(img_attr.level, t_left +x, t_upper +y)
                disp_img.paste(tile, (x*256, y*256))

        #reset img_attr
        disp_attr = ImageAttr(img_attr.level, t_left*256, t_upper*256, (t_right+1)*256 -1, (t_lower+1)*256 -1)

        return  (disp_img, disp_attr)

    def __drawTrk(self, img, img_attr):
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "draw gpx...")
        if len(self.gpx_layers) == 0:
            return

        draw = ImageDraw.Draw(img)

        for gpx in self.gpx_layers:
            #draw tracks
            #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "draw gpx...")
            for trk in gpx.tracks:
                if self.isTrackInImage(trk, img_attr):
                    self.drawTrkPoint(img, img_attr, trk, trk.color, draw=draw)

        #recycle draw object
        del draw

    def drawTrkPoint(self, img, img_attr, pts, color, bg_color=None, draw=None, width=2):
        if pts is None or len(pts) == 0:
            return

        bg_width = width + 4
        _draw = draw if draw is not None else ImageDraw.Draw(img)

        if len(pts) == 1:
            #print('draw trk point')
            (px, py) = pts[0].getPixel(img_attr.level)
            px -= img_attr.left_px
            py -= img_attr.up_py

            #r = int(bg_width/2)
            #_draw.ellipse((px-r, py-r, px+r, py+r), fill=bg_color)

            r = int(width/2)
            _draw.ellipse((px-r, py-r, px+r, py+r), fill=color, outline=bg_color)
        else:
            #print('draw trk seg')
            xy = []
            for pt in pts:
                (px, py) = pt.getPixel(img_attr.level)
                xy.append(px - img_attr.left_px)
                xy.append(py - img_attr.up_py)

            if bg_color is not None:
                _draw.line(xy, fill=bg_color, width=width+4)

            _draw.line(xy, fill=color, width=width)

        if draw is None:
            del _draw


    def isTrackInImage(self, trk, img_attr):
        #if some track point is in disp
        for pt in trk:
            (px, py) = pt.getPixel(img_attr.level)
            if img_attr.containsPoint(px, py):
                return True
        return False

    #draw pic as waypoint
    def __drawWpt(self, img, img_attr):
        wpts = self.getAllWpts()  #gpx's wpt + pic's wpt
        if len(wpts) == 0:
            return

        draw = ImageDraw.Draw(img)
        for wpt in wpts:
            (px, py) = wpt.getPixel(img_attr.level)
            self.drawWayPoint(img, img_attr, wpt, "gray", draw=draw)
        del draw

    def drawWayPoint(self, img, img_attr, wpt, txt_color, bg_color=None, draw=None):
        #print(datetime.strftime(datetime.now(), '%H:%M:%S.%f'), "draw wpt'", wpt.name, "'")
        #check range
        (px, py) = wpt.getPixel(img_attr.level)
        if not img_attr.containsPoint(px, py):
            return

        px -= img_attr.left_px
        py -= img_attr.up_py
        adj = int(conf.ICON_SIZE/2)

        #get draw
        _draw = draw if draw is not None else ImageDraw.Draw(img)

        if bg_color is not None:
            r = ceil(conf.ICON_SIZE/sqrt(2))
            _draw.ellipse((px-r, py-r, px+r, py+r), fill=bg_color, outline='gray')


        #paste icon
        if wpt.sym is not None:
            icon = conf.getIcon(wpt.sym)
            if icon is not None:
                if icon.mode == 'RGBA':
                    img.paste(icon, (px-adj, py-adj), icon)
                else:
                    #print("Warning: Icon for '%s' is not RGBA" % wpt.sym)
                    img.paste(icon, (px-adj, py-adj))

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


    def __getCropMap(self, img_attr):
        disp = self.disp_attr

        left  = img_attr.left_px - disp.left_px
        up    = img_attr.up_py - disp.up_py
        right = img_attr.right_px - disp.left_px
        low   = img_attr.low_py - disp.up_py
        return self.disp_img.crop((left, up, right, low))

    def __drawTM2Coord(self, img, attr):

        if attr.level <= 12:  #too crowded to show
            return

        #set draw
        py_shift = 20
        font = self.__font
        draw = ImageDraw.Draw(img)

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
    def getTWD67TM2ByPixcelXY(x, y, level):
        (lat, lon) = TileSystem.getLatLonByPixcelXY(x, y, level)
        return CoordinateSystem.TWD97_LatLonToTWD67_TM2(lat, lon)

    @staticmethod
    def getPixcelXYByTWD67TM2(x, y, level):
        (lat, lon) = CoordinateSystem.TWD67_TM2ToTWD97_LatLon(x, y)
        return TileSystem.getPixcelXYByLatLon(lat, lon, level)

#record image atrr
class ImageAttr:
    def __init__(self, level, left_px, up_py, right_px, low_py):
        #self.img = None
        self.level = level
        self.left_px = left_px
        self.up_py = up_py
        self.right_px = right_px
        self.low_py = low_py

    def containsImgae(self, attr):
        if self.level == attr.level and \
                self.left_px <= attr.left_px and self.up_py <= attr.up_py and \
                self.right_px >= attr.right_px and self.low_py >= attr.low_py:
            return True
        return False

    def containsPoint(self, px, py):
        return self.left_px <= px and self.up_py <= py and px <= self.right_px and py <= self.low_py

    #def isBoxInImage(self, px_left, py_up, px_right, py_low, img_attr):
        #return self.isPointInImage(px_left, py_up) or self.isPointInImage(px_left, py_low) or \
              #self.isPointInImage(px_right, py_up) or self.isPointInImage(px_right, py_low)

    def zoomToLevel(self, level):
        if level > self.level:
            s = level - self.level
            return ImageAttr(level, self.left_px << s, self.up_py << s, self.right_px << s, self.low_py << s)
        elif self.level > level:
            s = self.level - level
            return ImageAttr(level, self.left_px >> s, self.up_py >> s, self.right_px >> s, self.low_py >> s)
        else:
            return self

class WptBoard(tk.Toplevel):
    @property
    def is_changed(self): return self._is_changed

    def __init__(self, master, wpt_list, wpt=None):
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
        self._is_changed = False

        #board
        self.geometry('+0+0')
        self.protocol('WM_DELETE_WINDOW', lambda: self.onClosed(None))
        self.bind('<Escape>', self.onClosed)
        self.bind('<Delete>', self.onDeleted)

        #focus
        self._var_focus = tk.BooleanVar()
        self._var_focus.trace('w', self.onFocusChanged)

        #wpt name
        self._var_name = tk.StringVar()
        self._var_name.trace('w', self.onNameChanged)

        #show as dialog
        self.transient()
        self.focus_set()
        self.grab_set()

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
        
    def onClosed(self, e=None):
        #reset or restore map
        self.master.resetMap() if self.is_changed else self.master.restore()
        self.master.focus_set()
        self.destroy()

    def onDeleted(self, e):
        self.master.deleteWpt(self._curr_wpt)

        next_wpt = self._getNextWpt()
        self._wpt_list.remove(self._curr_wpt)
        self._is_changed = True
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
            self.showWptIcon(self._curr_wpt)
            self.highlightWpt(self._curr_wpt)
            #update status
            self._is_changed = True

    def onFocusChanged(self, *args):
        self.highlightWpt(self._curr_wpt)

    def onEditSymRule(self):
        messagebox.showinfo('', 'edit sym rule')
    
    def highlightWpt(self, wpt):
        #focus
        if self._var_focus.get():
            self.master.resetMap(wpt)

        #highlight the current wpt
        self.master.highlightWpt(wpt)

    def unhighlightWpt(self, wpt):
        if self.is_changed:
            self.master.resetMap(wpt)
        else:
            self.master.restore()

    def showWptIcon(self, wpt):
        pass

    def setCurrWpt(self, wpt):
        pass

class WptSingleBoard(WptBoard):
    def __init__(self, master, wpt_list, wpt=None):
        super().__init__(master, wpt_list, wpt)

        #change buttons
        self.__left_btn = tk.Button(self, text="<<", command=lambda:self.onWptSelected(-1), disabledforeground='lightgray')
        self.__left_btn.pack(side='left', anchor='w', expand=0, fill='y')
        self.__right_btn = tk.Button(self, text=">>", command=lambda:self.onWptSelected(1), disabledforeground='lightgray')
        self.__right_btn.pack(side='right', anchor='e', expand=0, fill='y')

        #info
        self.info_frame = self.getInfoFrame()
        self.info_frame.pack(side='bottom', anchor='sw', expand=0, fill='x')

        #image
        self.__img_label = None
        self.__img_sz = (img_w, img_h) = (600, 450)
        if self._hasPicWpt():
            self.__img_label = tk.Label(self, anchor='n', width=img_w, height=img_h, bg='black')
            self.__img_label.pack(side='top', anchor='nw', expand=1, fill='both', padx=0, pady=0)

        self.bind('<Configure>', self.onResize)

        #set wpt
        if wpt is None:
            wpt = wpt_list[0]
        self.setCurrWpt(wpt)

        #wait
        self.wait_window(self)

    def onResize(self, e):
        if e.widget == self.__img_label:
            img_w = self.__img_label.image.width()
            img_h = self.__img_label.image.height()
            if e.width < img_w or e.height < img_h or (e.width > img_w and e.height > img_h):
                print('need to zomm image')
                self.setWptImg(self._curr_wpt, (e.width, e.height))

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

    def showWptIcon(self, wpt):
        icon = ImageTk.PhotoImage(conf.getIcon(wpt.sym))
        self.__icon_label.image = icon
        self.__icon_label.config(image=icon, text=wpt.sym, compound='right')

    def setWptImg(self, wpt, size):
        if self.__img_label is not None:
            img = getAspectResize(wpt.img, size) if isinstance(wpt, PicDocument) else getTextImag("(No Pic)", size)
            img = ImageTk.PhotoImage(img)
            self.__img_label.config(image=img)
            self.__img_label.image = img #keep a ref

    def setCurrWpt(self, wpt):
        if self._curr_wpt != wpt:
            self.unhighlightWpt(self._curr_wpt)
            self.highlightWpt(wpt)

        self._curr_wpt = wpt

        #title
        self.title(wpt.name)

        #set imgae
        self.setWptImg(wpt, self.__img_sz)

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



class TrkBoard(tk.Toplevel):
    @property
    def is_changed(self): return self._is_changed

    def __init__(self, master, trk_list, trk=None):
        super().__init__(master)

        if trk is not None and trk not in trk_list:
            raise ValueError('trk is not in trk_list')

        self._curr_trk = None
        self._trk_list = trk_list
        self._is_changed = False
        self._sel_idx = None
        self._var_focus = tk.BooleanVar()
        self._var_focus.trace('w', self.onFocus)

        #board
        self.geometry('+0+0')
        self.bind('<Escape>', self.onClosed)
        self.protocol('WM_DELETE_WINDOW', lambda: self.onClosed(None))

        #change buttons
        self.__left_btn = tk.Button(self, text="<<", command=lambda:self.onSelected(-1), disabledforeground='lightgray')
        self.__left_btn.pack(side='left', anchor='w', expand=0, fill='y')
        self.__right_btn = tk.Button(self, text=">>", command=lambda:self.onSelected(1), disabledforeground='lightgray')
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
        self.pt_list.bind('<Down>', self.onPtSelected)
        self.pt_list.bind('<Delete>', self.onPtDeleted)


        #set trk
        if trk is not None:
            self.setCurrTrk(trk)
        elif len(trk_list) > 0:
            self.setCurrTrk(trk_list[0])

        #self.poll() # start polling the list

        #show as dialog
        self.transient()
        self.focus_set()
        self.grab_set()
        self.wait_window(self)

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
        tk.Entry(frame, font=font, textvariable=self._var_color).grid(row=1, column=1, sticky='w')

        #tk.Checkbutton(frame, text='Focus Track point', variable=self._var_focus).grid(row=2, column=1, sticky='w')

        return frame

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

    def onColorChanged(self, *args):
        color = self._var_color.get()
        if self._curr_trk.color != color:
            self._curr_trk.color = color
            self._is_changed = True
            self.master.resetMap()

    def onFocus(self, *args):
        is_focus = self._var_focus.get()
        if self._sel_idx is not None:
            pts = [self._curr_trk[i] for i in self._sel_idx]
            self.highlightTrk(pts)

    def onPtSelected(self, e):
        idx = self.pt_list.curselection()
        if self._sel_idx != idx:
            self._sel_idx = idx
            pts = [e.widget.data[i] for i in idx]  #index of pts -> pts
            self.highlightTrk(pts)

    def onPtDeleted(self, e):
        if self._sel_idx is not None:
            idx = sorted(self._sel_idx, reverse=True)
            self._sel_idx = None
            self._is_changed = True

            #Todo: may improve by deleting range.
            for i in idx:
                self.pt_list.delete(i)
                del self._curr_trk[i]

            #Todo: not work!
            self.master.resetMap()

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


def getAspectResize(img, size):
    dst_w, dst_h = size
    src_w, src_h = img.size

    w_ratio = dst_w / src_w
    h_ratio = dst_h / src_h
    ratio = min(w_ratio, h_ratio)

    w = int(src_w*ratio)
    h = int(src_h*ratio)

    return img.resize((w, h))

def getTextImag(text, size):
    w, h = size
    img = Image.new("RGBA", size)
    draw = ImageDraw.Draw(img)
    draw.text( (int(w/2-20), int(h/2)), text, fill='lightgray', font=conf.IMG_FONT)
    del draw

    return img


def isGpsFile(path):
    (fname, ext) = os.path.splitext(path)
    ext = ext.lower()
    if ext == '.gpx':
        return True
    if ext == '.gdb':
        return True
    return False

def getGpsDocument(path):
    (fname, ext) = os.path.splitext(path)
    ext = ext.lower()
    gpx = GpsDocument(conf.TZ)
    if ext == '.gpx':
        gpx.load(filename=path)
    else:
        gpx_string = toGpxString(path)
        gpx.load(filestring=gpx_string)
    return gpx

def toGpxString(src_path):
    (fname, ext) = os.path.splitext(src_path)
    if ext == '':
        raise ValueError("cannot identify input format")

    exe_file = conf.GPSBABEL_DIR + "\gpsbabel.exe"
    tmp_path = os.path.join(tempfile.gettempdir(),  "giseditor_gps.tmp")

    shutil.copyfile(src_path, tmp_path)  #to work around the problem of gpx read non-ascii filename
    cmd = '"%s" -i %s -f "%s" -o gpx,gpxver=1.1 -F -' % (exe_file, ext[1:], tmp_path)
    output = subprocess.check_output(cmd, shell=True)
    os.remove(tmp_path)

    return output.decode("utf-8")

def isPicFile(path):
    (fname, ext) = os.path.splitext(path)
    ext = ext.lower()

    if ext == '.jpg' or ext == '.jpeg':
        return True
    return False

def readFiles(paths):
    gps_path = []
    pic_path = []
    __readFiles(paths, gps_path, pic_path)
    return gps_path, pic_path
    
def __readFiles(paths, gps_path, pic_path):
    for path in paths:
        if os.path.isdir(path):
            subpaths = [os.path.join(path, f) for f in os.listdir(path)]
            __readFiles(subpaths, gps_path, pic_path)
        elif isPicFile(path):
            pic_path.append(path)
        elif isGpsFile(path):
            gps_path.append(path)

def isExit(disp_board):
    if not disp_board.is_changed:
        return True
    if not messagebox.askyesno('Save before Exit', 'Do you want to save file?'):
        return True
    if disp_board.onGpxSave():
        return True
    return False

def onExit(root, disp_board):
    if isExit(disp_board):
        root.destroy()

if __name__ == '__main__':

    #create window
    root = tk.Tk()
    root.title("PicGisEditor")
    root.geometry('800x600+400+0')

    pad_ = 2
    disp_board = DispBoard(root)
    disp_board.pack(side='right', anchor='se', expand=1, fill='both', padx=pad_, pady=pad_)
    root.protocol('WM_DELETE_WINDOW', lambda: onExit(root, disp_board))

    #add files
    gps_path, pic_path = readFiles(sys.argv[1:])
    for path in gps_path:
        disp_board.addGpx(getGpsDocument(path))
    for path in pic_path:
        disp_board.addPic(PicDocument(path, conf.TZ))

    #disp_board.initDisp()
    root.mainloop()

