#!/usr/bin/env python3

import os
import subprocess
import sys
import tkinter as tk
import urllib.request
import shutil
from os import listdir
from os.path import isdir, isfile, exists
from PIL import Image, ImageTk, ImageDraw, ImageFont
from math import floor, ceil

#my modules
import tile
from tile import  TileSystem, TileMap, GeoPoint
from coord import  CoordinateSystem
from gpx import GpsDocument
from pic import PicDocument

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

    def addGpx(self, gpx):
        self.map_ctrl.addGpxLayer(gpx)

    def addPic(self, pic):
        self.map_ctrl.addPicLayer(pic)

    def initDisp(self):
        #set preferred lat/lon
        latlon = self.__getPrefLatLon()
        if latlon is not None:
            self.map_ctrl.geo.lat = latlon[0]
            self.map_ctrl.geo.lon = latlon[1]

        #show map
        disp_w = 800
        disp_h = 600
        self.map_ctrl.shiftGeoPixel(-disp_w/2, -disp_h/2)
        self.setMap(self.map_ctrl.getTileImage(disp_w, disp_h));

    def __getPrefLatLon(self):
        #prefer track point
        for gpx in self.map_ctrl.gpx_layers:
            for trk in gpx.tracks:
                for pt in trk:
                    return (pt.lat, pt.lon)

        #way point
        for gpx in self.map_ctrl.gpx_layers:
            for wpt in gpx.way_points:
                return (wpt.lat, wpt.lon)

        #pic
        for pic in self.map_ctrl.pic_layers:
            return (pic.lat, pic.lon)

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
        #if self.__tile_map.isSupportedLevel(level):
        self.__geo.level = level

    def __init__(self):
        #def settings
        self.__tile_map = tile.getTM25Kv3TileMap(cache_dir=Config['cache_dir'])
        self.__geo = GeoPoint(lon=121.334754, lat=24.987969)  #default location
        self.__geo.level = 14

        #image
        self.disp_img = None
        self.disp_attr = None
        self.extra_p = 256

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

    def getTileImage(self, width, height):

        #The image attributes with which we want to create a image compatible.
        img_attr = ImageAttr(self.level, self.geo.px, self.geo.py, self.geo.px + width, self.geo.py + height)

        #gen new map if need
        if self.disp_attr is None or not self.disp_attr.containsImgae(img_attr):
            (self.disp_img, self.disp_attr) = self.__genDispMap(img_attr)

        #crop by width/height
        img = self.__getCropMap(img_attr)
        self.__drawTM2Coord(img, img_attr)

        return img


    #gen disp_map by req_attr, disp_map may larger than req_attr specifying
    def __genDispMap(self, img_attr):
        print("gen disp map")
        (img, attr) = self.__genBaseMap(img_attr)
        self.__drawGPX(img, attr)
        self.__drawPic(img, attr)

        return (img, attr)

    def __genBaseMap(self, img_attr):
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
        disp_img = Image.new("RGB", (tx_num*256, ty_num*256))
        for x in range(tx_num):
            for y in range(ty_num):
                tile = self.__tile_map.getTileByTileXY(img_attr.level, t_left +x, t_upper +y)
                disp_img.paste(tile, (x*256, y*256))

        #reset img_attr
        disp_attr = ImageAttr(img_attr.level, t_left*256, t_upper*256, (t_right+1)*256 -1, (t_lower+1)*256 -1)

        return  (disp_img, disp_attr)

    def __drawGPX(self, img, img_attr):
        if len(self.gpx_layers) == 0:
            return

        draw = ImageDraw.Draw(img)

        for gpx in self.gpx_layers:
            #draw tracks
            for trk in gpx.tracks:
                if self.isTrackInImage(trk, img_attr):
                    xy = []
                    for pt in trk:
                        (px, py) = pt.getPixel(img_attr.level)
                        xy.append(px - img_attr.left_px)
                        xy.append(py - img_attr.up_py)
                    draw.line(xy, fill=trk.color, width=2)

            #draw way points
            for wpt in gpx.way_points:
                self.drawPoint(draw, img_attr, wpt.lat, wpt.lon, wpt.name)

        #recycle draw object
        del draw

    @staticmethod
    def drawPoint(draw, img_attr, lat, lon, txt=None, font=None):
        #get px, py
        (px, py) = TileSystem.getPixcelXYByLatLon(lat, lon, img_attr.level)
        if not img_attr.containsPoint(px, py):
            return
        px -= img_attr.left_px
        py -= img_attr.up_py

        #draw point
        draw.ellipse((px-3, py-3, px+3, py+3), fill="#404040", outline='white')

        #draw text
        if txt is not None:
            font = ImageFont.truetype("ARIALUNI.TTF", 18)
            draw.text((px+1, py+1), txt, fill="white", font=font)
            draw.text((px-1, py-1), txt, fill="white", font=font)
            draw.text((px, py), txt, fill="gray", font=font)

    def isTrackInImage(self, trk, img_attr):
        #if some track point is in disp
        for pt in trk:
            (px, py) = pt.getPixel(img_attr.level)
            if img_attr.containsPoint(px, py):
                return True
        return False

    #draw pic as waypoint
    def __drawPic(self, img, img_attr):
        draw = ImageDraw.Draw(img)
        for pic in self.pic_layers:
            self.drawPoint(draw, img_attr, pic.lat, pic.lon, pic.desc)
        del draw

    def __getCropMap(self, img_attr):
        disp = self.disp_attr

        left  = img_attr.left_px - disp.left_px
        up    = img_attr.up_py - disp.up_py
        right = img_attr.right_px - disp.left_px
        low   = img_attr.low_py - disp.up_py
        return self.disp_img.crop((left, up, right, low))

    @classmethod
    def __drawTM2Coord(cls, img, attr):

        if attr.level <= 12:  #too crowded to show
            return

        #set draw
        py_shift = 20
        font = ImageFont.truetype("ARIALUNI.TTF", 18)
        draw = ImageDraw.Draw(img)

        #get xy of TM2
        (left_x, up_y) = cls.getTWD67TM2ByPixcelXY(attr.left_px, attr.up_py, attr.level)
        (right_x, low_y) = cls.getTWD67TM2ByPixcelXY(attr.right_px, attr.low_py, attr.level)

        #draw TM2' x per KM
        for x in range(ceil(left_x/1000), floor(right_x/1000) +1):
            #print("tm: ", x)
            (px, py) = cls.getPixcelXYByTWD67TM2(x*1000, low_y, attr.level)
            px -= attr.left_px
            py -= attr.up_py
            draw.text((px, py - py_shift), str(x), fill="black", font=font)

        #draw TM2' y per KM
        for y in range(ceil(low_y/1000), floor(up_y/1000) +1):
            #print("tm: ", y)
            (px, py) = cls.getPixcelXYByTWD67TM2(left_x, y*1000, attr.level)
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
    if ext == '.gpx':
        return GpsDocument(filename=path)
    else:
        gpx_string = toGpxString(path)
        return GpsDocument(filestring=gpx_string)

def toGpxString(src_path):
    (fname, ext) = os.path.splitext(src_path)
    if ext == '':
        raise ValueError("cannot identify input format")

    exe_file = Config['gpsbabel_dir'] + "\gpsbabel.exe"

    cmd = '"%s" -i %s -f %s -o gpx,gpxver=1.1 -F -' % (exe_file, ext[1:], src_path)
    output = subprocess.check_output(cmd, shell=True)
    return output.decode("utf-8")

def isPicFile(path):
    (fname, ext) = os.path.splitext(path)
    ext = ext.lower()

    if ext == '.jpg' or ext == '.jpeg':
        return True
    return False

def readConfig(conf_path):
    conf = {}
    with open(conf_path) as conf_file:
        for line in conf_file:
            k, v = line.rstrip().split('=', 1)
            conf[k] = v
    return conf


def readFiles(paths):
    gps_path = []
    pic_path = []
    __readFiles(paths, gps_path, pic_path)
    return gps_path, pic_path
    
def __readFiles(paths, gps_path, pic_path):
    for path in paths:
        if isdir(path):
            subpaths = [os.path.join(path, f) for f in listdir(path)]
            __readFiles(subpaths, gps_path, pic_path)
        elif isPicFile(path):
            pic_path.append(path)
        elif isGpsFile(path):
            gps_path.append(path)

if __name__ == '__main__':

    #read conf
    Config = readConfig('./giseditor.conf')

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
    disp_board.pack(side='right', anchor='se', expand=1, fill='both', padx=pad_, pady=pad_)

    #add files
    gps_path, pic_path = readFiles(sys.argv[1:])
    for path in gps_path:
        disp_board.addGpx(getGpsDocument(path))
    for path in pic_path:
        disp_board.addPic(PicDocument(path))

    disp_board.initDisp()
    root.mainloop()

