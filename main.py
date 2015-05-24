#!/usr/bin/env python3

import math
import tkinter as tk
from os import listdir
from os.path import isdir, isfile, exists
import urllib.request
import shutil

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
    def getGroundResolution(C, latitude, level):
        latitude = C.crop(latitude, C.MIN_LATITUDE, C.MAX_LATITUDE)
        return math.cos(latitude * math.pi / 180) * 2 * math.pi * C.EARTH_RADIUS / C.getMapSize(level)

    @classmethod
    def getMapScale(C, latitude, level, screen_dpi):
        return C.getGroundResolution(latitude, level) * screen_dpi / 0.0254

    @classmethod
    def getPixcelXYByLatLong(C, latitude, longitude, level):
        latitude = C.crop(latitude, C.MIN_LATITUDE, C.MAX_LATITUDE)
        longitude = C.crop(longitude, C.MIN_LONGITUDE, C.MAX_LONGITUDE)

        x = (longitude + 180) / 360 
        sin_latitude = math.sin(latitude * math.pi / 180)
        y = 0.5 - math.log((1 + sin_latitude) / (1 - sin_latitude)) / (4 * math.pi)

        map_size = C.getMapSize(level)
        pixel_x = int(C.crop(x * map_size + 0.5, 0, map_size - 1))
        pixel_y = int(C.crop(y * map_size + 0.5, 0, map_size - 1))

        return (pixel_x, pixel_y)

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
    def getTileXYByLatLong(C, latitude, longitude, level):
        (px, py) = C.getPixcelXYByLatLong(latitude, longitude, level)
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

        #data member
        self.bg_color='#808080'

        #board
        self.config(bg=self.bg_color)

        tk.Label(self, text="Dispaly Pic/Map", font='monaco 24', bg=self.bg_color).pack(expand=1, fill='both')


#get tile of 經建三
def getTileOfTM25K_2001(latitude, longitude, level):
    (tile_x, tile_y) = TileSystem.getTileXYByLatLong(latitude, longitude, level)
    url = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2001-jpg-%d-%d-%d" % (level, tile_x, tile_y)
    file_name = "C:/TM25K_2001-%d-%d-%d.jpg" % (level, tile_x, tile_y)
    urllib.request.urlretrieve(url, file_name)
    print(url)

#get tile of 經建四
def getTileOfTM25K_2003(latitude, longitude, level):
    (tile_x, tile_y) = TileSystem.getTileXYByLatLong(latitude, longitude, level)
    url = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2003-jpg-%d-%d-%d" % (level, tile_x, tile_y)
    file_name = "C:/TM25K_2003-%d-%d-%d.jpg" % (level, tile_x, tile_y)

    #urllib.request.urlretrieve(url, file_name)
    with urllib.request.urlopen(url) as response, open(file_name, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    print(url)

#
latitude = 24.987969
longitude = 121.334754
for level in range (24):
    getTileOfTM25K_2001(latitude, longitude, level)

for level in range (24):
    getTileOfTM25K_2003(latitude, longitude, level)


root = tk.Tk()
root.title("PicGisEditor")
root.geometry('400x300')

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
