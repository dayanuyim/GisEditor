#!/usr/bin/env python3
# -*- coding: utf8 -*-

"""handle for tile system, especially WMTS"""

import os
import math
import tkinter as tk
import urllib.request
import shutil
import sqlite3
from datetime import datetime
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

    def __init__(self, cache_dir):
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
            raise ValueError('cache_dir is None')
        self.__cache_dir = cache_dir
        self.__local_cache = None

        #memory cache
        self.__img_repo = {}   #id -> (img, timestamp)
        self.__img_repo_lock = Lock()

        #download helpers
        self.__MAX_WORKS = 3
        self.__download_lock = Lock()
        self.__download_cv = Condition(self.__download_lock)
        self.__workers = {}
        #self.__workers_lock = Lock()
        #self.__workers_cv = Condition(self.__workers_lock)
        self.__req_queue = OrderedDict()
        #self.__req_lock = Lock()
        #self.__req_cv = Condition(self.__req_lock)
        self.__download_monitor = Thread(target=self.__runDownloadMonitor)

    def start(self):
        #create cache dir for the map
        self.__local_cache = DBLocalCache(self.__cache_dir, self)
        self.__local_cache.start()
        #start download thread
        self.__download_monitor.start()

    def close(self):
        #notify download monitor to exit
        with self.__download_cv:
            self.__is_closed = True
            self.__download_cv.notify()
        self.__download_monitor.join()

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
            item = self.__img_repo.get(id)
            if item:
                return item
            else:
                item = (None, datetime.min)  #psuedo data to record timestamp
                self.__img_repo[id] = item
                return item

    def setRepoImage(self, id, item):
        with self.__img_repo_lock:
            self.__img_repo[id] = item

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

        #cache
        #(for data coherence, do this before moving self from workers queue: if download thread is done, data is ready)
        if tile_data:
            tile_img = Image.open(BytesIO(tile_data))
            self.setRepoImage(id, (tile_img, datetime.now()))

        #done the download
        #(do this before thread exit, to ensure monitor is notified)
        with self.__download_cv:
            self.__workers.pop(id, None)
            self.__download_cv.notify()

        #premature done
        if self.__is_closed:
            return

        #side effect
        if tile_data:
            #notify if need
            try:
                if cb is not None:
                    cb(level, x, y)
            except Exception as ex:
                print('Invoke cb of download tile error:', str(ex))

            #save file
            try:
                self.__local_cache.put(level, x, y, tile_data)
            except Exception as ex:
                print('Error to save tile data', str(ex))

    #The thread to handle all download requests
    def __runDownloadMonitor(self):
        def no_worker():
            return len(self.__workers) == 0

        #http_handler = urllib.request.HTTPHandler()
        #opener = urllib.request.build_opener(http_handler)
        #urllib.request.install_opener(opener)

        while True:
            #wait for requests
            with self.__download_cv:
                self.__download_cv.wait()

                if self.__is_closed:
                    break

                if len(self.__req_queue) > 0 and len(self.__workers) < self.__MAX_WORKS:
                    #the req
                    id, (level, x, y, cb) = self.__req_queue.popitem() #LIFO
                    if id in self.__workers:
                        print("WARNING: the req is DUP and in progress.") #should not happen
                    else:
                        #create the job and run the worker
                        job = lambda: self.__runDownloadJob(id, level, x, y, cb)
                        worker = Thread(name=id, target=job)
                        self.__workers[id] = worker
                        worker.start()

        #todo: interrupt urllib.request.openurl to stop download workers.
        #http_handler.close()
        #with self.__download_cv:
            #self.__download_cv.wait_for(no_worker)

    def __requestTile(self, id, level, x, y, cb):
        #check and add to req queue
        with self.__download_cv:
            if id in self.__req_queue:
                return
            if id in self.__workers:
                return
            #add the req
            self.__req_queue[id] = (level, x, y, cb)
            self.__download_cv.notify()

    def __getTile(self, level, x, y, auto_req=True, cb=None):
        #check level
        if level > self.level_max or level < self.level_min:
            raise ValueError("level is out of range")

        #get from cache
        id = self.genTileId(level, x, y)
        img, ts = self.getRepoImage(id)
        if img or (datetime.now() - ts).seconds < 60:
            return img;

        #get from disk
        try:
            data = self.__local_cache.get(level, x, y)
            if data:
                img = Image.open(BytesIO(data))
                self.setRepoImage(id, (img, datetime.now()))
                return img
            else:
                self.setRepoImage(id, (None, datetime.now())) #update timestamp
        except Exception as ex:
            print("Error to read tile data: ", str(ex))

        #async request to WMTS
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
    def start(self):
        pass

    def close(self):
        pass

    def put(self, level, x, y, data):
        pass

    def get(self, level, x, y):
        pass

class FileLocalCache(LocalCache):
    def __init__(self, cache_dir, tile_map):
        self.__cache_dir = os.path.join(cache_dir, tile_map.map_id) #create subfolder
        self.__tile_map = tile_map

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

class DBLocalCache(LocalCache):
    def __init__(self, cache_dir, tile_map, is_concurrency=True):
        self.__db_path = os.path.join(cache_dir, tile_map.map_id + ".db")
        self.__tile_map = tile_map
        self.__is_concurrency = is_concurrency
        self.__conn = None
        self.__surrogate = None  #the thread do All DB operations, due to sqlite3 requiring only the same thread.

        self.__is_closed = False

        #concurrency get/put
        self.__sql_queue = []
        self.__sql_queue_lock = Lock()
        self.__sql_queue_cv = Condition(self.__sql_queue_lock)

        self.__get_lock = Lock()    #block the 'get' action

        self.__get_respose = None   #the pair (data, exception)
        self.__get_respose_lock = Lock()
        self.__get_respose_cv = Condition(self.__get_respose_lock)

    def __initDB(self):
        def getBoundsText(tile_map):
            left, bottom = tile_map.lower_corner
            right, top   = tile_map.upper_corner
            bounds = "%f,%f,%f,%f" % (left, bottom, right, top) #OpenLayers Bounds format
            return bounds

        tm = self.__tile_map
        conn = self.__conn

        #meatadata
        meta_create_sql = "CREATE TABLE metadata(name TEXT PRIMARY KEY, value TEXT)"
        meta_data_sqls = ("INSERT INTO metadata(name, value) VALUES('%s', '%s')" % ('name', tm.map_id),
                          "INSERT INTO metadata(name, value) VALUES('%s', '%s')" % ('type', 'overlayer'),
                          "INSERT INTO metadata(name, value) VALUES('%s', '%s')" % ('version', '1.0'),
                          "INSERT INTO metadata(name, value) VALUES('%s', '%s')" % ('description', tm.map_title),
                          "INSERT INTO metadata(name, value) VALUES('%s', '%s')" % ('format', tm.tile_format),
                          "INSERT INTO metadata(name, value) VALUES('%s', '%s')" % ('bounds', getBoundsText(tm)),
                         )
        #tiles
        tiles_create_sql = "CREATE TABLE tiles("
        tiles_create_sql += "zoom_level  INTEGER, "
        tiles_create_sql += "tile_column INTEGER, "
        tiles_create_sql += "tile_row    INTEGER, "
        tiles_create_sql += "tile_data   BLOB     NOT NULL, "
        tiles_create_sql += "PRIMARY KEY (zoom_level, tile_column, tile_row))"

        #ind_create_sql = "CREATE INDEX IND on tiles (zoom_level, tile_row, tile_column)"

        #exec
        conn.execute(meta_create_sql)
        conn.execute(tiles_create_sql)
        for sql in meta_data_sqls:
            conn.execute(sql)


    #the true actions which are called by Surrogate
    def __start(self):
        if not os.path.exists(self.__db_path):
            print('Initializing local cache DB...')
            mkdirSafely(os.path.dirname(self.__db_path))
            self.__conn = sqlite3.connect(self.__db_path)
            self.__initDB()
        else:
            self.__conn = sqlite3.connect(self.__db_path)

    def __close(self):
        print('Closing local cache DB...')
        self.__conn.close()

    def __put(self, level, x, y, data):
        ex = None
        try:
            sql = "INSERT OR REPLACE INTO tiles(zoom_level, tile_column, tile_row, tile_data) VALUES(%d, %d, %d, ?)" % \
                    (level, x, y)
            self.__conn.execute(sql, (data,))
            self.__conn.commit()
        except Exception as _ex:
            ex = _ex

        print("%s [%s]" % (sql, ("Fail" if ex else "OK")))
        if ex:
            raise ex

    def __get(self, level, x, y):
        data, ex = None, None
        try:
            sql = "SELECT tile_data FROM tiles WHERE zoom_level=%d AND tile_column=%d AND tile_row=%d" % (level, x, y)
            cursor = self.__conn.execute(sql)
            row = cursor.fetchone()
            data = None if row is None else row[0]
        except Exception as _ex:
            ex = _ex

        print("%s [%s]" % (sql, ("Fail" if ex else "OK" if data else "NA")))
        if ex:
            raise ex
        return data

    #the interface which are called by the user
    def start(self):
        if not self.__is_concurrency:
            self.__start()
        else:
            self.__surrogate = Thread(target=self.__runSurrogate)
            self.__surrogate.start()

    def close(self):
        if not self.__is_concurrency:
            self.__close()
        else:
            with self.__sql_queue_cv:
                self.__is_closed = True
                self.__sql_queue_cv.notify()
            self.__surrogate.join()

    def put(self, level, x, y, data):
        if not self.__is_concurrency:
            self.__put(level, x, y, data)
        else:
            with self.__sql_queue_cv:
                item = (level, x, y, data)
                self.__sql_queue.append(item)
                self.__sql_queue_cv.notify()

    def get(self, level, x, y):
        if not self.__is_concurrency:
            self.__get(level, x, y)
        else:
            def has_respose():
                return self.__get_respose is not None

            with self.__get_lock:  #for blocking the continuous get
                #add req
                with self.__sql_queue_cv:
                    item = (level, x, y, None)
                    self.__sql_queue.insert(0, item)  #service first
                    self.__sql_queue_cv.notify()

                #wait resposne
                res = None
                with self.__get_respose_cv:
                    self.__get_respose_cv.wait_for(has_respose)
                    res, self.__get_respose = self.__get_respose, None   #swap

                #return data
                data, ex = res
                if ex:
                    raise ex
                return data

    #the Surrogate thread
    def __runSurrogate(self):
        def has_sql_events():
            return self.__is_closed or len(self.__sql_queue)
        
        self.__start()
        try:
            while True:
                #wait events
                item = None
                with self.__sql_queue_cv:
                    self.__sql_queue_cv.wait_for(has_sql_events)
                    if self.__is_closed:
                        return
                    item = self.__sql_queue.pop(0)

                level, x, y, data = item
                #put data
                if data:
                    try:
                        self.__put(level, x, y, data)
                    except Exception as ex:
                        print("DB put data error:", str(ex))
                #get data
                else:
                    res_data, res_ex = None, None
                    try:
                        res_data = self.__get(level, x, y)
                        res_ex = None
                    except Exception as ex:
                        print("DB get data error:", str(ex))
                        res_data = None
                        res_ex = ex

                    #notify
                    with self.__get_respose_cv:
                        self.__get_respose = (res_data, res_ex)
                        self.__get_respose_cv.notify()

        finally:
            self.__close()

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
