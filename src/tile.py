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
from io import BytesIO
from util import mkdirSafely

class __TileMap:
    @property
    def title(self):
        return self.map_title

    def __init__(self, cache_dir=None):
        #The attributes needed to be initialized outside
        self.uid = None
        self.map_id = None
        self.map_title = None
        self.lower_corner = None
        self.upper_corner = None
        self.url_template = None
        self.level_min = None
        self.level_max = None
        self.tile_side = None
        self.tile_format = None

        self.__is_closed = False

        #local cache
        if cache_dir is None:
            cache_dir = 'cache'
        self.__local_cache = LocalCache(cache_dir)

        #memory cache
        self.__img_repo = {}
        self.__img_repo_lock = Lock()

        #download helpers
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
        self.__local_cache.start()
        #start download thread
        self.__downloader.start()

    def close(self):
        #set flag
        self.__is_closed = True

        #stop all download workers/monitor
        #todo: stop download workers, if any
        with self.__workers_cv:
            self.__workers_cv.notify() #wakeup the thread 'downloader monitor'
        with self.__req_cv:
            self.__req_cv.notify()     #wakeup the thread 'downloader monitor'
        #todo: wait download workers/monitor to stop

        #close resources
        self.__local_cache.close()

    def isSupportedLevel(self, level):
        return self.level_min <= level and level <= self.level_max

    def getCachePath(self):
        return os.path.join(self.__cache_dir, self.map_id)

    def genTileId(self, level, x, y):
        return "%s-%d-%d-%d" % (self.map_id, level, x, y)

    def genTileUrl(self, level, x, y):
        return self.url_template % (level, x, y)

    def getRepoImage(self, id):
        with self.__img_repo_lock:
            return self.__img_repo.get(id)

    def setRepoImage(self, id, img):
        with self.__img_repo_lock:
            self.__img_repo[id] = img

    #The therad to download
    def __runDownloadJob(self, id, level, x, y, cb):
        #do download
        tile_data = None
        try:
            url = self.genTileUrl(level, x, y)
            print('DL', url)
            with urllib.request.urlopen(url, timeout=30) as response:
                tile_data = response.read()
        except Exception as ex:
            print('Error to download %s: %s' % (url, str(ex)))
        print('DL %s [%s]' % (url, 'SUCCESS' if tile_data else 'FAILED'))

        #premature done
        if self.__is_closed:
            return

        #cache
        if tile_data:
            tile_img = Image.open(BytesIO(tile_data))
            self.setRepoImage(id, tile_img)

        #done the download
        with self.__workers_cv:
            self.__workers.pop(id, None)
            self.__workers_cv.notify()

        #side effect
        if tile_data:
            #notify if need
            try:
                if cb: cb(level, x, y)
            except Exception as ex:
                print('Invoke cb of download tile error:', str(ex))

            #save file
            try:
                self.__local_cache.put(level, x, y, tile_data)
            except Exception as ex:
                print('Error to save tile data', str(ex))

    #deliver a req to a worker
    def __deliverDownloadJob(self):
        with self.__req_lock, self.__workers_lock:  #Be CAREFUL the order
            #test conditions again
            if len(self.__req_queue) == 0:
                print("WARNING: no request in the queue!") #should not happen
                return
            if len(self.__workers) >= self.__MAX_WORKS:
                print("WARNING: no available download workers!") #should not happen
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
        try:
            data = self.__local_cache.get(level, x, y)
            if data:
                img = Image.open(BytesIO(data))
                self.setRepoImage(id, img)
                return img
        except Exception as ex:
            print("Error to read tile data: ", str(ex))

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

def getTM25Kv3TileMap(cache_dir, is_started=False):
    tm = __TileMap(cache_dir=cache_dir)
    tm.uid = 210
    tm.map_id = "TM25K_2001"
    tm.map_title = "2001-臺灣經建3版地形圖-1:25,000"
    tm.lower_corner = (117.84953432, 21.65607265)
    tm.upper_corner = (123.85924109, 25.64233621)
    tm.url_template = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2001-jpg-%d-%d-%d"
    tm.level_min = 7
    tm.level_max = 16
    tm.tile_side = 256
    tm.tile_format = 'jpg'
    if is_started: tm.start()
    return tm

def getTM25Kv4TileMap(cache_dir):
    tm = __TileMap(cache_dir=cache_dir, is_started=False)
    tm.uid = 211
    tm.map_id = "TM25K_2003"
    tm.map_title = "2001-臺灣經建4版地形圖-1:25,000"
    tm.lower_corner = (117.84953432, 21.65607265)
    tm.upper_corner = (123.85924109, 25.64233621)
    tm.url_template = "http://gis.sinica.edu.tw/tileserver/file-exists.php?img=TM25K_2003-jpg-%d-%d-%d"
    tm.level_min = 5
    tm.level_max = 17
    tm.tile_side = 256
    tm.tile_format = 'jpg'
    if is_started: tm.start()
    return tm

class LocalCache:
    def __init__(self, cache_dir):
        self.__cache_dir = cache_dir

    def __genTilePath(self, level, x, y):
        #add extra folder layer 'x' to lower the number of files within a folder
        name = "%d-%d-%d.jpg" % (level, x, y)
        return os.path.join(self.__cache_dir, str(x), name)

    def start(self):
        mkdirSafely(self.__cache_dir)

    def close(self):
        pass

    def put(self, level, x, y, data):
        path = self.__genTilePath(level, x, y)
        mkdirSafely(os.path.dirname(path))
        with open(path, 'wb') as file:
            file.write(data)

    def get(self, level, x, y):
        path = self.__genTilePath(level, x, y)
        if os.path.exists(path):
            with open(path, 'rb') as file:
                return file.read()
        return None

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
        tm = getTM25Kv3TileMap(cache_dir, True)
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
