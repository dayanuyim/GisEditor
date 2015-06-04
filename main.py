#!/usr/bin/env python3

import os
import math
import tkinter as tk
import urllib.request
import shutil
from os import listdir
from os.path import isdir, isfile, exists
from PIL import Image, ImageTk

class TileSystem:
    EARTH_RADIUS = 6378137
    MIN_LATITUDE = -85.05112878
    MAX_LATITUDE = 85.05112878
    MIN_LONGITUDE = -180
    MAX_LONGITUDE = 180

    @staticmethod
    def crop(val, min_val, max_val):
        return min(max(val, min_val), max_val)

    @staticmethod
    def getMapSize(level):
        return 256 << level

    @classmethod
    def getValidLatitude(C, latitude):
        return C.crop(latitude, C.MIN_LATITUDE, C.MAX_LATITUDE)

    @classmethod
    def getValidLongitude(C, latitude):
        return C.crop(latitude, C.MIN_LONGITUDE, C.MAX_LONGITUDE)

    @classmethod
    def getGroundResolution(C, latitude, level):
        return math.cos(latitude * math.pi / 180) * 2 * math.pi * C.EARTH_RADIUS / C.getMapSize(level)

    @classmethod
    def getMapScale(C, latitude, level, screen_dpi):
        return C.getGroundResolution(latitude, level) * screen_dpi / 0.0254

    @classmethod
    def getPixcelXYByLatLon(C, latitude, longitude, level):
        latitude = C.crop(latitude, C.MIN_LATITUDE, C.MAX_LATITUDE)
        longitude = C.crop(longitude, C.MIN_LONGITUDE, C.MAX_LONGITUDE)

        x = (longitude + 180) / 360 
        sin_latitude = math.sin(latitude * math.pi / 180)
        y = 0.5 - math.log((1 + sin_latitude) / (1 - sin_latitude)) / (4 * math.pi)

        map_size = C.getMapSize(level)
        pixel_x = int(C.crop(x * map_size + 0.5, 0, map_size - 1))
        pixel_y = int(C.crop(y * map_size + 0.5, 0, map_size - 1))

        return (pixel_x, pixel_y)
    

    @classmethod
    def getLatLonByPixcelXY(C, pixel_x, pixel_y, level):
        map_size = C.getMapSize(level)
        x = (C.crop(pixel_x , 0, map_size - 1) / map_size) - 0.5
        y = 0.5 - (C.crop(pixel_y , 0, map_size - 1) / map_size)

        lat = 90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi
        lon = x * 360
        return (lat, lon)

    @staticmethod
    def getTileXYByPixcelXY(pixel_x, pixel_y):
        tile_x = int(pixel_x / 256)
        tile_y = int(pixel_y / 256)
        return (tile_x, tile_y)

    @staticmethod
    def getPixcelXYByTileXY(tile_x, tile_y):
        pixel_x = tile_x * 256
        pixel_y = tile_y * 256
        return (pixel_x, pixel_y)

    @classmethod
    def getTileXYByLatLon(C, latitude, longitude, level):
        (px, py) = C.getPixcelXYByLatLon(latitude, longitude, level)
        return C.getTileXYByPixcelXY(px, py)


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

        #set map
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

    def setMapInfo(self):
        c = self.map_ctrl
        (lon, lat) = c.getLonLat()
        self.info_label.config(text="[%s] level: %s, lon: %f, lat: %f" % (c.getTileMap().getMapName(), c.getLevel(), lon, lat))

    def setMap(self, img):
        photo = ImageTk.PhotoImage(img)
        self.disp_label.config(image=photo)
        self.disp_label.image = photo #keep a ref

class TileMap:
    def getMapName(self): return self.map_title

    def __init__(self):
        #self.map_id = "TM25K_2001"
        #self.map_title = "2001-臺灣經建3版地形圖-1:25,000"
        #self.lower_corner = (117.84953432, 21.65607265)
        #self.upper_corner = (123.85924109, 25.64233621)
        #self.url_template = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2001-jpg-%d-%d-%d"
        #self.level_min = 7
        #self.level_max = 16

        self.__cache_dir = './cache'
        if not os.path.exists(self.__cache_dir):
            os.makedirs(self.__cache_dir)

        self.__img_repo = {}

    def isSupportedLevel(self, level):
        return self.level_min <= level and level <= self.level_max

    def genTileName(self, level, x, y):
        return "%s-%d-%d-%d.jpg" % (self.map_id, level, x, y)

    #return tkinter.PhotoImage
    def getTileByLonLat(self, level, longitude, latitude):
        (x, y) = TileSystem.getTileXYByLatLon(latitude, longitude, level)
        return self.getTileByTileXY(level, x, y)

    def getTileByTileXY(self, level, x, y):
        name = self.genTileName(level, x, y)

        img = self.__img_repo.get(name)
        if img is None:
            img = self.__readTile(level, x, y)
            self.__img_repo[name] = img
        return img

    def __readTile(self, level, x, y):
        path = "%s/%s" % (self.__cache_dir, self.genTileName(level, x, y))
        if not os.path.exists(path):
            self.__downloadTile(level, x, y, path)
        print(path)
        return Image.open(path)

    def __downloadTile(self, level, x, y, file_path):
        url = self.url_template % (level, x, y)

        #urllib.request.urlretrieve(url, file_path)
        with urllib.request.urlopen(url) as response, open(file_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print(url)

def getTM25Kv3TileMap():
    tm = TileMap()
    tm.map_id = "TM25K_2001"
    tm.map_title = "2001-臺灣經建3版地形圖-1:25,000"
    tm.lower_corner = (117.84953432, 21.65607265)
    tm.upper_corner = (123.85924109, 25.64233621)
    tm.url_template = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2001-jpg-%d-%d-%d"
    tm.level_min = 7
    tm.level_max = 16
    return tm

def getTM25Kv4TileMap():
    tm = TileMap()
    tm.map_id = "TM25K_2003"
    tm.map_title = "2001-臺灣經建4版地形圖-1:25,000"
    tm.lower_corner = (117.84953432, 21.65607265)
    tm.upper_corner = (123.85924109, 25.64233621)
    tm.url_template = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2003-jpg-%d-%d-%d"
    tm.level_min = 5
    tm.level_max = 17
    return tm

class MapController:
    def getTileMap(self): return self.tile_map
    def setTileMap(self, tm): self.tile_map = tm

    def getLevel(self): return self.level
    def setLevel(self, level):
        if self.tile_map.isSupportedLevel(level):
            (lon, lat) = self.getLonLat()
            (self.geo_px, self.geo_py) = TileSystem.getPixcelXYByLatLon(lat, lon, level)
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

    def __init__(self):
        self.level = 16
        self.tile_map = getTM25Kv3TileMap()
        #self.center_lon = 121.334754
        #self.center_lat = 24.987969
        self.setLonLat(lon=121.334754, lat=24.987969)

    def shiftGeoPixel(self, px, py):
        self.geo_px += int(px)
        self.geo_py += int(py)

    def getTileImage(self, width, height):

        #get tile x, y.
        (t_left, t_upper) = TileSystem.getTileXYByPixcelXY(self.geo_px, self.geo_py)
        (t_right, t_lower) = TileSystem.getTileXYByPixcelXY(self.geo_px + width, self.geo_py + height)
        tx_num = t_right - t_left +1
        ty_num = t_lower - t_upper +1

        #image
        new_img = Image.new("RGB", (tx_num*256, ty_num*256))
        for x in range(tx_num):
            for y in range(ty_num):
                img = self.tile_map.getTileByTileXY(self.level, t_left +x, t_upper +y)
                new_img.paste(img, (x*256, y*256))

        img_x = self.geo_px %256
        img_y = self.geo_py %256
        return new_img.crop((img_x, img_y, img_x + width, img_y + height))

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
    disp_board.pack(side='right', anchor='se', expand=1, fill='both', padx=pad_, pady=pad_)


    root.mainloop()

