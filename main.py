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
from tile import  TileSystem, TileMap
from gpx import GpsDocument

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
        self.info_label.pack(expand=1, fill='x', anchor='n')

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

    def showGpx(self, gpx):
        self.map_ctrl.addGpxLayer(gpx)
        self.map_ctrl.setLonLat(gpx.getMinLon(), gpx.getMaxLat())

        disp_w = 800
        disp_h = 600
        self.map_ctrl.shiftGeoPixel(-disp_w/2, -disp_h/2)
        self.setMap(self.map_ctrl.getTileImage(disp_w, disp_h));
        
    def onMouseWheel(self, event):
        label = event.widget

        #set focused pixel
        self.map_ctrl.shiftGeoPixel(event.x, event.y)

        #level
        level = self.map_ctrl.getLevel()
        if event.delta > 0:
            self.map_ctrl.setLevel(level+1)
        elif event.delta < 0:
            self.map_ctrl.setLevel(level-1)

        #set focused pixel again
        self.map_ctrl.shiftGeoPixel(-event.x, -event.y)

        self.setMapInfo()
        self.setMap(self.map_ctrl.getTileImage(label.winfo_width(), label.winfo_height()))

    def onMouseDown(self, event):
        self.__mouse_down_pos = (event.x, event.y)

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

    def setMapInfo(self):
        c = self.map_ctrl
        (lon, lat) = c.getLonLat()
        self.info_label.config(text="[%s] level: %s, lon: %f, lat: %f" % (c.getTileMap().getMapName(), c.getLevel(), lon, lat))

    def setMap(self, img):
        photo = ImageTk.PhotoImage(img)
        self.disp_label.config(image=photo)
        self.disp_label.image = photo #keep a ref


class MapController:
    def getTileMap(self): return self.tile_map
    def setTileMap(self, tm): self.tile_map = tm

    def getLevel(self): return self.level
    def setLevel(self, level):
        if self.tile_map.isSupportedLevel(level):
            #set geo x/y
            #(lon, lat) = self.getLonLat()
            #(self.geo_px, self.geo_py) = TileSystem.getPixcelXYByLatLon(lat, lon, level)
            diff = level - self.level
            if diff > 0:
                self.geo_px <<= diff
                self.geo_py <<= diff
            elif diff < 0:
                self.geo_px >>= -diff
                self.geo_py >>= -diff

            self.level = level

    #def getLongitude(self): return self.center_lon
    #def setLongitude(self, lon): self.center_lon = TileSystem.getValidLongitude(lon);

    #def getLatitude(self): return self.center_lat
    #def setLatitude(self, lat): self.center_lat = TileSystem.getValidLatitude(lat);

    def setLonLat(self, lon, lat):
        (self.geo_px, self.geo_py) = TileSystem.getPixcelXYByLatLon(lat, lon, self.level)

    def getLonLat(self):
        (lat, lon) = TileSystem.getLatLonByPixcelXY(self.geo_px, self.geo_py, self.level)
        return (lon, lat)

    def getGeoPx(self): return self.geo_px
    def setGeoPx(self, px): self.geo_px = px

    def getGeoPy(self): return self.geo_py
    def setGeoPy(self, py): self.geo_py = py

    def setGeoPixel(self, px, py):
        self.geo_px = int(px)
        self.geo_py = int(py)

    def __init__(self):
        #def settings
        self.level = 14
        self.tile_map = tile.getTM25Kv3TileMap()
        #self.center_lon = 121.334754
        #self.center_lat = 24.987969
        self.setLonLat(lon=121.334754, lat=24.987969)

        #image
        self.disp_img = None
        self.disp_img_attr = None

        #layer
        self.gpx_layers = []

    def shiftGeoPixel(self, px, py):
        self.geo_px += int(px)
        self.geo_py += int(py)

    def addGpxLayer(self, gpx):
        self.gpx_layers.append(gpx)

    def getTileImage(self, width, height):

        #gen new map if need
        if not self.__isInDispMap(width, height):
            self.__genDispMap(width, height)

        #crop by width/height
        return self.__getCropMap(width, height)

    def __isInDispMap(self, width, height):
        if self.disp_img_attr is None:
            return False

        left = self.geo_px
        up = self.geo_py
        right = self.geo_px + width
        low = self.geo_py + height
        (img_level, img_left, img_up, img_right, img_low) = self.disp_img_attr

        if img_level == self.level and img_left <= left and img_up <= up and img_right >= right and img_low >= low:
            return True

    def __genDispMap(self, width, height):
        print("gen disp map")
        self.__genBaseMap(width, height)
        self.__drawGPX(width, height)

    def __genBaseMap(self, width, height):
        left = self.geo_px
        up = self.geo_py
        right = self.geo_px + width
        low = self.geo_py + height

        #get tile x, y.
        (t_left, t_upper) = TileSystem.getTileXYByPixcelXY(left, up)
        (t_right, t_lower) = TileSystem.getTileXYByPixcelXY(right, low)
        tx_num = t_right - t_left +1
        ty_num = t_lower - t_upper +1

        #gen image
        img = Image.new("RGB", (tx_num*256, ty_num*256))
        for x in range(tx_num):
            for y in range(ty_num):
                tile = self.tile_map.getTileByTileXY(self.level, t_left +x, t_upper +y)
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
                if self.isTrackInDisp(trk, width, height):
                    xy = []
                    for pt in trk:
                        (px, py) = TileSystem.getPixcelXYByLatLon(pt.lat, pt.lon, self.level)
                        xy.append(px - img_left)
                        xy.append(py - img_up)
                    draw.line(xy, fill=trk.color, width=2)

            #draw way points
            for wpt in gpx.getWayPoints():
                if self.isWayPointInDisp(wpt, width, height):
                    (px, py) = TileSystem.getPixcelXYByLatLon(wpt.lat, wpt.lon, self.level)
                    px -= img_left
                    py -= img_up
                    #draw point
                    draw.ellipse((px-1, py-1, px+1, py+1), fill="#404040")
                    #draw text
                    draw.text((px+1, py+1), wpt.name, fill="white", font=font)
                    draw.text((px-1, py-1), wpt.name, fill="white", font=font)
                    draw.text((px, py), wpt.name, fill="gray", font=font)
        #recycle draw object
        del draw

    def isWayPointInDisp(self, wpt, width, height):
        #Todo
        return True

    def isTrackInDisp(self, trk, width, height):
        #Todo
        return True

    def __getCropMap(self, width, height):
        (img_level, img_left, img_up, img_right, img_low) = self.disp_img_attr
        img = self.disp_img

        img_x = self.geo_px - img_left
        img_y = self.geo_py - img_up
        return img.crop((img_x, img_y, img_x + width, img_y + height))


if __name__ == '__main__':
    #create window
    root = tk.Tk()
    root.title("PicGisEditor")
    root.geometry('800x600')

    pad_ = 2
    setting_board = SettingBoard(root)
    setting_board.pack(side='top', anchor='nw', expand=0, fill='x', padx=pad_, pady=pad_)

    pic_board = PicBoard(root)
    pic_board.pack(side='left', anchor='nw', expand=0, fill='y', padx=pad_, pady=pad_)
    #add callback on pic added
    setting_board.onPicAdded(lambda fname:pic_board.addPic(fname))

    disp_board = DispBoard(root)
    for arg in sys.argv[1:]:
        gpx = GpsDocument(arg)
        disp_board.showGpx(gpx)
    disp_board.pack(side='right', anchor='se', expand=1, fill='both', padx=pad_, pady=pad_)

    root.mainloop()

