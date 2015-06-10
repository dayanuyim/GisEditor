#!/usr/bin/env python3

import os
import sys
import math
import tkinter as tk
import urllib.request
import shutil
from os import listdir
from os.path import isdir, isfile, exists
from PIL import Image, ImageTk, ImageDraw, ImageFont
#my modules
import tile
from tile import  TileSystem, TileMap, GeoPoint
from coord import  CoordinateSystem
from gpx import GpsDocument
from math import floor, ceil

class SettingBoard(tk.LabelFrame):
    def __init__(self, master):
        super().__init__(master)

        #data member
        self.sup_type = [".jpg"]
        self.bg_color = '#D0D0D0'
        self.load_path = tk.StringVar()
        self.load_path.set("C:\\Users\\TT_Tsai\\Dropbox\\Photos\\Sample Album")  #for debug
        self.pic_filenames = []
        self.row_fname = 0
        self.cb_pic_added = []

        #board
        self.config(text='settings', bg=self.bg_color)

        #load pic files
        row = 0
        tk.Button(self, text="Load Pic...", command=self.doLoadPic).grid(row=row, column=0, sticky='w')
        tk.Entry(self, textvariable=self.load_path).grid(row=row, column=1, columnspan = 99, sticky='we')
        row += 1
        self.row_fname = row

        #load gpx file
        row += 1
        tk.Button(self, text="Load Gpx...").grid(row=row, sticky='w')
        row += 1
        tk.Label(self, text="(no gpx)", bg=self.bg_color).grid(row=row, sticky='w')

    def isSupportType(self, fname):
        fname = fname.lower()

        for t in self.sup_type:
            if(fname.endswith(t)):
                return True
        return False

    #add pic filename if cond is ok
    def addPicFile(self, f):
        if(not self.isSupportType(f)):
            return False
        if(f in self.pic_filenames):
            return False

        self.pic_filenames.append(f)
        return True

    #load pic filenames from dir/file
    def doLoadPic(self):
        path = self.load_path.get()

        #error check
        if(path is None or len(path) == 0):
            return
        if(not exists(path)):
            print("The path does not exist")
            return

        #add file, if support
        has_new = False
        if(isdir(path)):
            for f in listdir(path):
                if(self.addPicFile(f)):
                    has_new = True
        elif(isfile(path)):
            if(self.addPicFile(f)):
                has_new = True
        else:
            print("Unknown type: " + path)  #show errmsg
            return

        if(has_new):
            self.dispPicFilename()
            self.doPicAdded()

    #disp pic filename 
    def dispPicFilename(self):
        fname_txt = ""
        for f in self.pic_filenames:
            fname_txt += f
            fname_txt += " "
        #self.label_fname["text"] = fname_txt
        label_fname = tk.Label(self)
        label_fname.config(text=fname_txt, bg=self.bg_color)
        label_fname.grid(row=self.row_fname, column=0, columnspan=99, sticky='w')

        #for f in self.pic_filenames:
            #tk.Button(self, text=f, relief='groove').grid(row=self.row_fname, column=self.pic_filenames.index(f))

    def getPicFilenames(self):
        return self.pic_filenames

    def onPicAdded(self, cb):
        self.cb_pic_added.append(cb)

    def doPicAdded(self):
        for cb in self.cb_pic_added:
            cb(self.pic_filenames)
            
class PicBoard(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg='#000000')

        #data member
        self.pic_filenames = []

    def addPic(self, fnames):
        self.pic_filenames.extend(fnames)
        #reset pic block
        for f in self.pic_filenames:
            tk.Button(self, text=f).grid(row=self.pic_filenames.index(f), sticky='news')

class DispBoard(tk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.map_ctrl = MapController()

        #board
        self.bg_color='#D0D0D0'
        self.config(bg=self.bg_color)

        #info
        self.info_label = tk.Label(self, font='24', anchor='w', bg=self.bg_color)
        self.setMapInfo()
        self.info_label.pack(expand=0, fill='x', anchor='n')

        #display area
        disp_w = 800
        disp_h = 600
        self.disp_label = tk.Label(self, width=disp_w, height=disp_h, bg='#808080')
        #self.disp_label.config(width=disp_w, height=disp_h)
        self.disp_label.pack(expand=1, fill='both', anchor='n')
        self.disp_label.bind('<MouseWheel>', self.onMouseWheel)
        self.disp_label.bind("<Button-1>", self.onMouseDown)
        self.disp_label.bind("<Button1-Motion>", self.onMouseMotion)
        self.disp_label.bind("<Button1-ButtonRelease>", self.onMouseUp)
        self.disp_label.bind("<Configure>", self.onResize)

    def showGpx(self, gpx):
        self.map_ctrl.addGpxLayer(gpx)
        self.map_ctrl.geo.lon = (gpx.getMinLon() + gpx.getMaxLon()) / 2
        self.map_ctrl.geo.lat = (gpx.getMaxLat() + gpx.getMinLat()) / 2

        disp_w = 800
        disp_h = 600
        self.map_ctrl.shiftGeoPixel(-disp_w/2, -disp_h/2)
        self.setMap(self.map_ctrl.getTileImage(disp_w, disp_h));
        
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
        self.setMap(self.map_ctrl.getTileImage(label.winfo_width(), label.winfo_height()))

    def onMouseDown(self, event):
        self.__mouse_down_pos = (event.x, event.y)

        #show lat/lon
        c = self.map_ctrl
        geo = GeoPoint(px=c.geo.px + event.x, py=c.geo.py + event.y, level=c.geo.level) 
        (x_tm2_97, y_tm2_97) = CoordinateSystem.TWD97_LatLonToTWD97_TM2(geo.lat, geo.lon)
        (x_tm2_67, y_tm2_67) = CoordinateSystem.TWD97_TM2ToTWD67_TM2(x_tm2_97, y_tm2_97)

        txt = "LatLon/97: (%f, %f), TM2/97: (%.3f, %.3f), TM2/67: (%.3f, %.3f)" % (geo.lat, geo.lon, x_tm2_97/1000, y_tm2_97/1000, x_tm2_67/1000, y_tm2_67/1000)
        self.setMapInfo(txt=txt)

    def onMouseMotion(self, event):
        if self.__mouse_down_pos is not None:
            label = event.widget

            #print("change from ", self.__mouse_down_pos, " to " , (event.x, event.y))
            (last_x, last_y) = self.__mouse_down_pos
            self.map_ctrl.shiftGeoPixel(last_x - event.x, last_y - event.y)
            self.setMapInfo()
            self.setMap(self.map_ctrl.getTileImage(label.winfo_width(), label.winfo_height()))

            self.__mouse_down_pos = (event.x, event.y)

    def onMouseUp(self, event):
        self.__mouse_down_pos = None

        #clear lat/lon
        #self.setMapInfo()

    def onResize(self, event):
        label = event.widget
        self.setMapInfo()
        self.setMap(self.map_ctrl.getTileImage(label.winfo_width(), label.winfo_height()))

    def setMapInfo(self, lat=None, lon=None, txt=None):
        c = self.map_ctrl
        if txt is not None:
            self.info_label.config(text="[%s] level: %s, %s" % (c.tile_map.getMapName(), c.level, txt))
        elif lat is not None and lon is not None:
            self.info_label.config(text="[%s] level: %s, lat: %f, lon: %f" % (c.tile_map.getMapName(), c.level, lat, lon))
        else:
            self.info_label.config(text="[%s] level: %s" % (c.tile_map.getMapName(), c.level))

    def setMap(self, img):
        photo = ImageTk.PhotoImage(img)
        self.disp_label.config(image=photo)
        self.disp_label.image = photo #keep a ref


class MapController:
    @property
    def tile_map(self): return self.__tile_map

    @property
    def geo(self): return self.__geo

    @property
    def level(self): return self.__geo.level
    @level.setter
    def level(self, level):
        if self.__tile_map.isSupportedLevel(level):
            self.__geo.level = level

    def __init__(self):
        #def settings
        self.__tile_map = tile.getTM25Kv3TileMap()
        self.__geo = GeoPoint(lon=121.334754, lat=24.987969)  #default location
        self.__geo.level = 14

        #image
        self.disp_img = None
        self.disp_img_attr = None

        #layer
        self.gpx_layers = []

    def shiftGeoPixel(self, px, py):
        self.__geo.px += int(px)
        self.__geo.py += int(py)

    def addGpxLayer(self, gpx):
        self.gpx_layers.append(gpx)

    def getTileImage(self, width, height):

        #gen new map if need
        if not self.__isInDispMap(width, height):
            self.__genDispMap(width, height)

        #crop by width/height
        img = self.__getCropMap(width, height)
        img_attr = (self.level, self.geo.px, self.geo.py, self.geo.px + width, self.geo.py + height)
        self.__drawTM2Coord(img, img_attr)

        return img

    def __isInDispMap(self, width, height):
        if self.disp_img_attr is None:
            return False

        left = self.geo.px
        up = self.geo.py
        right = self.geo.px + width
        low = self.geo.py + height
        (img_level, img_left, img_up, img_right, img_low) = self.disp_img_attr

        if img_level == self.level and img_left <= left and img_up <= up and img_right >= right and img_low >= low:
            return True

    def __genDispMap(self, width, height):
        print("gen disp map")
        self.__genBaseMap(width, height)
        self.__drawGPX(width, height)

    def __genBaseMap(self, width, height):

        #gen w/ more tile
        ext_tile = 1

        left = self.geo.px
        up = self.geo.py
        right = self.geo.px + width
        low = self.geo.py + height

        #get tile x, y.
        (t_left, t_upper) = TileSystem.getTileXYByPixcelXY(left, up)
        (t_left, t_upper) = (t_left - ext_tile, t_upper - ext_tile)  #extend tile
        (t_right, t_lower) = TileSystem.getTileXYByPixcelXY(right, low)
        (t_right, t_lower) = (t_right + ext_tile, t_lower + ext_tile)  #extend tile
        tx_num = t_right - t_left +1
        ty_num = t_lower - t_upper +1

        #gen image
        img = Image.new("RGB", (tx_num*256, ty_num*256))
        for x in range(tx_num):
            for y in range(ty_num):
                tile = self.__tile_map.getTileByTileXY(self.level, t_left +x, t_upper +y)
                img.paste(tile, (x*256, y*256))

        #save image
        self.disp_img_attr = (self.level, t_left*256, t_upper*256, (t_right+1)*256 -1, (t_lower+1)*256 -1)
        self.disp_img = img

    def __drawGPX(self, width, height):
        if len(self.gpx_layers) == 0:
            return

        (img_level, img_left, img_up, img_right, img_low) = self.disp_img_attr
        img = self.disp_img

        font = ImageFont.truetype("ARIALUNI.TTF", 18)
        draw = ImageDraw.Draw(img)

        for gpx in self.gpx_layers:
            #draw tracks
            for trk in gpx.getTracks():
                if self.isTrackInDisp(trk):
                    xy = []
                    for pt in trk:
                        (px, py) = pt.getPixel(self.level)
                        xy.append(px - img_left)
                        xy.append(py - img_up)
                    draw.line(xy, fill=trk.color, width=2)

            #draw way points
            for wpt in gpx.getWayPoints():
                (px, py) = TileSystem.getPixcelXYByLatLon(wpt.lat, wpt.lon, self.level)
                if self.isPointInDisp(px, py):
                    px -= img_left
                    py -= img_up
                    #draw point
                    draw.ellipse((px-3, py-3, px+3, py+3), fill="#404040", outline='white')
                    #draw text
                    draw.text((px+1, py+1), wpt.name, fill="white", font=font)
                    draw.text((px-1, py-1), wpt.name, fill="white", font=font)
                    draw.text((px, py), wpt.name, fill="gray", font=font)
        #recycle draw object
        del draw

    def isPointInDisp(self, px, py):
        (img_level, img_left, img_up, img_right, img_low) = self.disp_img_attr
        return img_left <= px and img_up <= py and px <= img_right and py <= img_low

    def isBoxInDisp(self, px_left, py_up, px_right, py_low):
        return self.isPointInDisp(px_left, py_up) or self.isPointInDisp(px_left, py_low) or \
              self.isPointInDisp(px_right, py_up) or self.isPointInDisp(px_right, py_low)

    def isTrackInDisp(self, trk):
        #if the box containing the track is in disp
        #(px_left, py_up) = TileSystem.getPixcelXYByLatLon(trk.maxlat, trk.minlon, self.level)
        #(px_right, py_low) = TileSystem.getPixcelXYByLatLon(trk.minlat, trk.maxlon, self.level)
        #return self.isBoxInDisp(px_left, py_up, px_right, py_low)

        #if some track point is in disp
        for pt in trk:
            (px, py) = pt.getPixel(self.level)
            if self.isPointInDisp(px, py):
                return True
        return False

    def __getCropMap(self, width, height):
        (img_level, img_left, img_up, img_right, img_low) = self.disp_img_attr
        img = self.disp_img

        img_x = self.geo.px - img_left
        img_y = self.geo.py - img_up
        return img.crop((img_x, img_y, img_x + width, img_y + height))

    @classmethod
    def __drawTM2Coord(cls, img, img_attr):

        (level, left_px, up_py, right_px, low_py) = img_attr

        #set draw
        py_shift = 20
        font = ImageFont.truetype("ARIALUNI.TTF", 18)
        draw = ImageDraw.Draw(img)

        #get xy of TM2
        (left_x, up_y) = cls.getTWD67TM2ByPixcelXY(left_px, up_py, level)
        (right_x, low_y) = cls.getTWD67TM2ByPixcelXY(right_px, low_py, level)

        #draw TM2' x per KM
        for x in range(ceil(left_x/1000), floor(right_x/1000) +1):
            #print("tm: ", x)
            (px, py) = cls.getPixcelXYByTWD67TM2(x*1000, low_y, level)
            px -= left_px
            py -= up_py
            draw.text((px, py - py_shift), str(x), fill="black", font=font)

        #draw TM2' y per KM
        for y in range(ceil(low_y/1000), floor(up_y/1000) +1):
            #print("tm: ", y)
            (px, py) = cls.getPixcelXYByTWD67TM2(left_x, y*1000, level)
            px -= left_px
            py -= up_py
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


if __name__ == '__main__':
    #create window
    root = tk.Tk()
    root.title("PicGisEditor")
    root.geometry('800x600')

    pad_ = 2
    setting_board = SettingBoard(root)
    #setting_board.pack(side='top', anchor='nw', expand=0, fill='x', padx=pad_, pady=pad_)

    pic_board = PicBoard(root)
    #pic_board.pack(side='left', anchor='nw', expand=0, fill='y', padx=pad_, pady=pad_)
    #add callback on pic added
    setting_board.onPicAdded(lambda fname:pic_board.addPic(fname))

    disp_board = DispBoard(root)
    for arg in sys.argv[1:]:
        gpx = GpsDocument(arg)
        disp_board.showGpx(gpx)
    disp_board.pack(side='right', anchor='se', expand=1, fill='both', padx=pad_, pady=pad_)

    root.mainloop()

