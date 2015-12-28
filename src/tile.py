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
        self.__workers_cv = Condition()
        self.__workers_lock = Lock()
        self.__workers = []
        self.__MAX_WORKS = 3
        self.__req_lock = Lock()
        self.__req_cv = Condition()
        self.__req_queue = OrderedDict()
        self.__downloader = Thread(target=self.__tileDownloader)

    def start(self):
        #create cache dirs
        for level in range(self.level_min, self.level_max+1):
            level_dir = os.path.join(self.__cache_dir, self.map_id, str(level))
            if not os.path.exists(level_dir):
                os.makedirs(level_dir)
        #start download thread
        self.__downloader.start()

    def close(self):
        self.__is_closed = True
        with self.__req_cv:
            self.__req_cv.notify() #wakeup the thread 'TileDownloader'

    def isSupportedLevel(self, level):
        return self.level_min <= level and level <= self.level_max

    def genTileId(self, level, x, y):
        return "%s-%d-%d-%d" % (self.map_id, level, x, y)

    def genTilePath(self, level, x, y):
        name = "%d-%d.jpg" % (x, y)
        return os.path.join(self.__cache_dir, self.map_id, str(level), name)

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
    def __doDownloadJob(self, id, level, x, y, cb):
        #do download
        result_ok = False
        try:
            url = self.genTileUrl(level, x, y)
            print('DL', url)
            with urllib.request.urlopen(url) as response:
                res_img = Image.open(response)
            result_ok = True
        except Exception as ex:
            print('Error to download %s: %s' % (url, str(ex)))

        #remove myself from workers
        with self.__workers_lock:
            self.__workers = [w for w in self.__workers if w.name != id]
        #wakeup the foreman
        with self.__workers_cv:
            self.__workers_cv.notify()
        print('DL %s [FINISH][%s]' % (url, 'SUCCESS' if result_ok else 'FAILED'))

        #cache && notify if need
        if not self.__is_closed:
            self.setRepoImage(id, res_img)
            if result_ok and cb:
                try:
                    cb(level, x, y)
                except Exception as ex:
                    print('Invoke cb of download tile error:', str(ex))

        #save file
        if result_ok:
            try:
                path = self.genTilePath(level, x, y)
                res_img.save(path, quality=85)
            except Exception as ex:
                print('Error to save tile file', str(ex))

    #wait an available worker and deliver the download job.
    def __deliverDownload(self, id, level, x, y, cb):
        def has_worker():
            return len(self.__workers) < self.__MAX_WORKS

        if not has_worker():
            with self.__workers_cv:
                self.__workers_cv.wait_for(has_worker)
            
        if not self.__is_closed:
            job = lambda: self.__doDownloadJob(id, level, x, y, cb)
            worker = Thread(name=id, target=job)
            with self.__workers_lock:
                self.__workers.append(worker)
            worker.start()

    #The thread to handle all download requests
    def __tileDownloader(self):
        def has_events():
            return self.__is_closed or len(self.__req_queue)

        while not self.__is_closed:
            #wait for events
            with self.__req_cv:
                self.__req_cv.wait_for(has_events)

            #closed
            if self.__is_closed:
                break

            #check queue
            item = None
            with self.__req_lock:
                if len(self.__req_queue) > 0:
                    item = self.__req_queue.popitem() #LIFO
            if item:
                id, (level, x, y, cb) = item
                self.__deliverDownload(id, level, x, y, cb)  #wait a worker to download
            
    def __requestTile(self, id, level, x, y, cb):
        has_new_req = False
        with self.__req_lock:
            if not id in self.__req_queue:
                self.__req_queue[id] = (level, x, y, cb)   #add request
                has_new_req = True
        if has_new_req:
            with self.__req_cv:
                self.__req_cv.notify()    #notify

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
        if os.path.exists(path):
            img = Image.open(path)
            self.setRepoImage(id, img)
            return img

        #async request
        if auto_req:
            self.__requestTile(id, level, x, y, cb)
        return None

    def __genFakeTile(self, level, x, y):
        side = self.tile_side
        bg = 'lightgray'

        #gen fake by zome out of level-1
        if level > self.level_min:
            img = self.__getTile(level-1, int(x/2), int(y/2), False)
            if img:
                half_side = int(side/2)
                px = 0 if x%2 == 0 else half_side
                py = 0 if y%2 == 0 else half_side
                img = img.crop((px, py, px+half_side, py+half_side))
                img = img.resize((side,side))  #magnify
                return img

        #gen fake by zome in of level+1
        if level < self.level_max:
            img = Image.new("RGBA", (2*side, 2*side), bg)
            tl = self.__getTile(level+1, 2*x,   2*y, False)
            tr = self.__getTile(level+1, 2*x+1, 2*y, False)
            bl = self.__getTile(level+1, 2*x,   2*y+1, False)
            br = self.__getTile(level+1, 2*x+1, 2*y+1, False)

            if tl: img.paste(tl, (0, 0))
            if tr: img.paste(tr, (side, 0))
            if bl: img.paste(bl, (0, side))
            if br: img.paste(br, (side, side))
            img = img.resize((side,side)) #minify
            return img

        img = Image.new("RGBA", (side, side), bg)
        return img

    def getTileByTileXY_(self, level, x, y, cb=None, allow_fake=True):
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
        cb = lambda level, x, y: downloadImage(tm, title)
        while True:
            tile = tm.getTileByTileXY_(level, x, y, cb)
            showim(tile, title)
            if tile.is_fake:
                time.sleep(3)
            else:
                break

    def test(cache_dir):
        tm = getTM25Kv3TileMap(cache_dir)
        downloadImage(tm, cache_dir.split('/')[-1])
        tm.close()

    test('test/tile/noop')

    #tm = getTM25Kv3TileMap('test/tile/normal')
    #showim(tm.getTileByTileXY_(14, x, y), 'normal')

    #tm = getTM25Kv3TileMap('test/tile/magnify')
    #showim(tm.getTileByTileXY_(14, x, y), 'magnify')

    #tm = getTM25Kv3TileMap('test/tile/minify')
    #showim(tm.getTileByTileXY_(14, x, y), 'minify')

    #tm = getTM25Kv3TileMap('test/tile/minify_part')
    #showim(tm.getTileByTileXY_(14, x, y), 'magnify')

    #tm = getTM25Kv3TileMap('test/tile/minify_magnify')
    #showim(tm.getTileByTileXY_(14, x, y), 'minify_magnify')

    root.mainloop()
