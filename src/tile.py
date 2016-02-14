#!/usr/bin/env python3
# -*- coding: utf8 -*-

"""handle for tile system, especially WMTS"""

import os
import math
import tkinter as tk
import urllib.request
import shutil
from os import listdir
from os.path import isdir, isfile, exists
from PIL import Image, ImageTk, ImageDraw, ImageTk
from threading import Thread, Lock, Condition
from math import tan, sin, cos, radians, degrees
from collections import OrderedDict

def mkdirCheck(path, is_recursive=True):
    if not os.path.exists(path):
        if is_recursive:
            os.makedirs(path)
        else:
            os.mkdir(path)

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

class __TileMap:
    @property
    def title(self):
        return self.map_title

    def __init__(self, cache_dir=None):
        #The attributes needed to be initialized outside
        self.map_id = None
        self.map_title = None
        self.lower_corner = None
        self.upper_corner = None
        self.url_template = None
        self.level_min = None
        self.level_max = None
        self.tile_side = None

        #gen cache dir
        self.__cache_dir = cache_dir if cache_dir else './cache' 
        self.__is_closed = False

        #download helpers
        self.__img_repo = {}
        self.__img_repo_lock = Lock()
        self.__MAX_WORKS = 3
        self.__workers = {}
        self.__workers_lock = Lock()
        self.__workers_cv = Condition(self.__workers_lock)
        self.__req_queue = OrderedDict()
        self.__req_lock = Lock()
        self.__req_cv = Condition(self.__req_lock)
        self.__downloader = Thread(target=self.__runDownloadMonitor)

    def start(self):
        #create cache dir for the map
        mkdirCheck(self.getCachePath())
        #start download thread
        self.__downloader.start()

    def close(self):
        self.__is_closed = True
        with self.__workers_cv:
            self.__workers_cv.notify() #wakeup the thread 'foreman'
        with self.__req_cv:
            self.__req_cv.notify() #wakeup the thread 'TileDownloader'

    def isSupportedLevel(self, level):
        return self.level_min <= level and level <= self.level_max

    def getCachePath(self):
        return os.path.join(self.__cache_dir, self.map_id)

    def genTileId(self, level, x, y):
        return "%s-%d-%d-%d" % (self.map_id, level, x, y)

    def genTilePath(self, level, x, y):
        #add extra folder layer 'x' to lower the number of files within a folder
        name = "%d-%d-%d.jpg" % (level, x, y)
        return os.path.join(self.getCachePath(), str(x), name)

    def genTileUrl(self, level, x, y):
        return self.url_template % (level, x, y)

    def getRepoImage(self, id):
        with self.__img_repo_lock:
            return self.__img_repo.get(id)

    def setRepoImage(self, id, img):
        with self.__img_repo_lock:
            self.__img_repo[id] = img

#get tile in sync
#    def getTileByTileXY(self, level, x, y):
#        id = self.genTileId(level, x, y)
#
#        img = self.__img_repo.get(id)
#        if img is None:
#            img = self.__readTile(level, x, y)
#            self.__img_repo[id] = img
#        return img
#
#    def __readTile(self, level, x, y):
#        path = self.genTilePath(level, x, y)
#        #print("File", path)
#
#        if not os.path.exists(path):
#            self.__downloadTile(level, x, y, path)
#        return Image.open(path)
#
#    def __downloadTile(self, level, x, y, file_path):
#        url = self.genTileUrl(level, x, y)
#        print("DL", url)
#
#        #urllib.request.urlretrieve(url, file_path)
#        with urllib.request.urlopen(url) as response, open(file_path, 'wb') as out_file:
#            shutil.copyfileobj(response, out_file)

    #The therad to download
    def __runDownloadJob(self, id, level, x, y, cb):
        #do download
        res_img = None
        try:
            url = self.genTileUrl(level, x, y)
            print('DL', url)
            with urllib.request.urlopen(url, timeout=30) as response:
                res_img = Image.open(response)
        except Exception as ex:
            print('Error to download %s: %s' % (url, str(ex)))
        print('DL %s [%s]' % (url, 'SUCCESS' if res_img else 'FAILED'))

        #premature done
        if self.__is_closed:
            return

        #cache
        if res_img:
            self.setRepoImage(id, res_img)

        #done the download
        with self.__workers_cv:
            self.__workers.pop(id, None)
            self.__workers_cv.notify()

        #side effect
        if res_img:
            #notify if need
            if cb:
                try:
                    cb(level, x, y)
                except Exception as ex:
                    print('Invoke cb of download tile error:', str(ex))

            #save file
            try:
                path = self.genTilePath(level, x, y)
                mkdirCheck(os.path.dirname(path))
                res_img.save(path, quality=85)
            except Exception as ex:
                print('Error to save tile file', str(ex))

    #deliver a req to a worker
    def __deliverDownloadJob(self):
        with self.__req_lock, self.__workers_lock:  #Be CAREFUL the order
            if len(self.__req_queue) == 0:
                print("WARNING: no request in the queue!") #should not happen
                return

            #the req
            id, (level, x, y, cb) = self.__req_queue.popitem() #LIFO
            if id in self.__workers:
                print("WARNING: the req is DUP and in progress.") #should not happen
                return

            #create the job and run the worker
            job = lambda: self.__runDownloadJob(id, level, x, y, cb)
            worker = Thread(name=id, target=job)
            self.__workers[id] = worker
            worker.start()

    #The thread to handle all download requests
    def __runDownloadMonitor(self):
        def req_events():
            return self.__is_closed or len(self.__req_queue)

        def worker_events():
            return self.__is_closed or len(self.__workers) < self.__MAX_WORKS

        while True:
            #wait for requests
            with self.__req_cv:
                self.__req_cv.wait_for(req_events)
            if self.__is_closed:
                break

            #wait waker availabel
            with self.__workers_cv:
                self.__workers_cv.wait_for(worker_events)
            if self.__is_closed:
                break

            self.__deliverDownloadJob()


    def __requestTile(self, id, level, x, y, cb):
        #check and add to req queue
        with self.__req_cv:
            with self.__workers_lock:  #Be CAREFUL the order
                if id in self.__req_queue:
                    return
                if id in self.__workers:
                    return
            #add the req
            self.__req_queue[id] = (level, x, y, cb)
            self.__req_cv.notify()

    def __getTile(self, level, x, y, auto_req=True, cb=None):
        #check level
        if level > self.level_max or level < self.level_min:
            raise ValueError("level is out of range")

        #from cache
        id = self.genTileId(level, x, y)
        img = self.getRepoImage(id)
        if img:
            return img;

        #from disk
        path = self.genTilePath(level, x, y)
        if os.path.exists(path): #check file exists and is valid
            try:
                img = Image.open(path)
                self.setRepoImage(id, img)
                return img
            except Exception as ex:
                print("ERROR read tile image file error: ", str(ex))

        #async request
        if auto_req:
            self.__requestTile(id, level, x, y, cb)
        return None

    def __genMagnifyFakeTile(self, level, x, y, diff=1):
        side = self.tile_side
        for i in range(1, diff+1):
            scale = 2**i
            img = self.__getTile(level-i, int(x/scale), int(y/scale), False)
            if img:
                step = int(side/scale)
                px = step * (x%scale)
                py = step * (y%scale)
                img = img.crop((px, py, px+step, py+step))
                img = img.resize((side,side))  #magnify
                return img
        return None

    def __genMinifyFakeTile(self, level, x, y, diff=1):
        bg = 'lightgray'
        side = self.tile_side

        for i in range(1, diff+1):
            scale = 2**i
            img = Image.new("RGBA", (side*scale, side*scale), bg)
            has_tile = False
            #paste tiles
            for p in range(scale):
                for q in range(scale):
                    t = self.__getTile(level+i, x*scale+p, y*scale+q, False)
                    if t:
                        img.paste(t, (p*side, q*side))
                        has_tile = True
            #minify
            if has_tile:
                img = img.resize((side,side))
                return img
        return None

    def __genFakeTile(self, level, x, y):
        #gen from lower level
        level_diff = min(level - self.level_min, 3)
        img = self.__genMagnifyFakeTile(level, x, y, level_diff)
        if img:
            return img

        #gen from upper level
        level_diff = min(self.level_max - level, 1)
        img = self.__genMinifyFakeTile(level, x, y, level_diff)
        if img:
            return img

        #gen empty
        side = self.tile_side
        bg = 'lightgray'
        img = Image.new("RGBA", (side, side), bg)
        return img

    def getTile(self, level, x, y, cb=None, allow_fake=True):
        img = self.__getTile(level, x, y, True, cb)
        if img:
            img.is_fake = False
            return img

        if allow_fake:
            img = self.__genFakeTile(level, x, y)
            img.is_fake = True
            return img

        return None

def getTM25Kv3TileMap(cache_dir):
    tm = __TileMap(cache_dir=cache_dir)
    tm.map_id = "TM25K_2001"
    tm.map_title = "2001-臺灣經建3版地形圖-1:25,000"
    tm.lower_corner = (117.84953432, 21.65607265)
    tm.upper_corner = (123.85924109, 25.64233621)
    tm.url_template = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2001-jpg-%d-%d-%d"
    tm.level_min = 7
    tm.level_max = 16
    tm.tile_side = 256
    tm.start()
    return tm

def getTM25Kv4TileMap(cache_dir):
    tm = __TileMap(cache_dir=cache_dir)
    tm.map_id = "TM25K_2003"
    tm.map_title = "2001-臺灣經建4版地形圖-1:25,000"
    tm.lower_corner = (117.84953432, 21.65607265)
    tm.upper_corner = (123.85924109, 25.64233621)
    tm.url_template = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2003-jpg-%d-%d-%d"
    tm.level_min = 5
    tm.level_max = 17
    tm.tile_side = 256
    tm.start()
    return tm

if __name__ == '__main__':
    import time

    root = tk.Tk()

    level = 14
    x, y = TileSystem.getTileXYByLatLon(24.988625, 121.313181, 14)
    print('level, x, y:', level, x, y) #14, 13713, 7016

    def showim(img, title=''):
        top = tk.Toplevel(root)
        top.title(title)
        if img:
            img = ImageTk.PhotoImage(img)
            label = tk.Label(top, image=img)
            label.image = img
            label.pack(expand=1, fill='both')
        else:
            print('oops, img is none')
        top.update()

    def downloadImage(tm, title):
        while True:
            tile = tm.getTile(level, x, y)
            showim(tile, title)
            if tile.is_fake:
                time.sleep(3)
            else:
                break

    def test(cache_dir):
        tm = getTM25Kv3TileMap(cache_dir)
        downloadImage(tm, cache_dir.split('/')[-1])
        tm.close()

    #test('test/tile/noop')
    #test('test/tile/normal')

    #test('test/tile/magnify_13')
    #test('test/tile/magnify_12')
    #test('test/tile/magnify_11')

    #test('test/tile/minify')
    test('test/tile/minify_part')

    #tm = getTM25Kv3TileMap('test/tile/minify_magnify')
    #showim(tm.getTile(14, x, y), 'minify_magnify')

    root.mainloop()
