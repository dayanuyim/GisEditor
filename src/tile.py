#!/usr/bin/env python3
# -*- coding: utf8 -*-

"""handle for tile system, especially WMTS"""

import os
import math
import tkinter as tk
import urllib.request
import shutil
import sqlite3
import conf
import logging
import util
from xml.etree import ElementTree as ET
from datetime import datetime
from os import listdir
from os.path import isdir, isfile, exists
from PIL import Image, ImageTk, ImageDraw, ImageTk
from threading import Thread, Lock, Condition
from math import tan, sin, cos, radians, degrees
from collections import OrderedDict
from io import BytesIO
from util import mkdirSafely, saveXml

class MapDescriptor:
    #should construct from static methods.
    def __init__(self):
        #fields loaded from xml
        #....
        self.enabled = False
        self.alpha = 50

    def save(self, dirpath, id=None):
        root = ET.Element("customMapSource")

        name = ET.SubElement(root, "name")
        name.text = self.map_title

        min_zoom = ET.SubElement(root, "minZoom")
        min_zoom.text = str(self.level_min)

        max_zoom = ET.SubElement(root, "maxZoom")
        max_zoom.text = str(self.level_max)

        tile_type = ET.SubElement(root, "tileType")
        tile_type.text = self.tile_format

        tile_update = ET.SubElement(root, "tileUpdate")
        tile_update.text = "IfNotMatch"

        url = ET.SubElement(root, "url")
        url.text = self.url_template

        lower_corner = ET.SubElement(root, "lowerCorner")
        lower_corner.text = "%.9f %.9f" % self.lower_corner

        upper_corner = ET.SubElement(root, "upperCorner")
        upper_corner.text = "%.9f %.9f" % self.upper_corner

        bgcolor = ET.SubElement(root, "backgroundColor")
        bgcolor.text = "#000000"

        #write to file
        filename = id if id else self.map_id
        filepath = os.path.join(dirpath, filename) + ".xml"
        util.saveXml(root, filepath)

    def clone(self):
        desc = MapDescriptor()
        desc.map_id = self.map_id
        desc.map_title = self.map_title
        desc.level_min = self.level_min
        desc.level_max = self.level_max
        desc.url_template = self.url_template
        desc.lower_corner = self.lower_corner
        desc.upper_corner = self.upper_corner
        desc.tile_format = self.tile_format
        desc.tile_side = self.tile_side
        desc.alpha = self.alpha
        desc.enabled = self.enabled
        return desc

    # satic method #######################################
    @classmethod
    def __getElemText(cls, root, tag_path, def_value=None, errmsg=None):
        elem = root.find(tag_path)
        if elem is not None:
            return elem.text
        else:
            if errmsg:
                logging.warning(errmsg)
            return def_value

    @classmethod
    def __cropValue(cls, val, low, up, errmsg=None):
        _val = min(max(low, val), up)
        if _val != val and errmsg:
            logging.warning(errmsg)
        return _val

    @classmethod
    def __parseLatlon(cls, latlon_str, def_latlon):
        tokens = latlon_str.split(' ')
        if len(tokens) != 2:
            logging.info("not valid lat lon string: '%s'" % (latlon_str,))
            return def_latlon

        try:
            lat = float(tokens[0])
            lon = float(tokens[1])
            lat = cls.__cropValue(lat, -180, 180, "not valid lat value: %f" % (lat,))
            lon = cls.__cropValue(lon, -85, 85, "not valid lon value: %f" % (lon,))
            return (lat, lon)
        except Exception as ex:
            logging.error("parsing latlon string '%s' error: '%s'" % (latlon_str, str(ex)))

        return def_latlon

    @classmethod
    def __parseXml(cls, xml_root, id):
        if not id:
            raise ValueError("[map info] map id is empty")

        name = cls.__getElemText(xml_root, "./name", "")
        if not name:
            raise ValueError("[map info '%s'] no map name" % (id,))

        min_zoom = int(cls.__getElemText(xml_root, "./minZoom", "0", "[map info '%s'] invalid min zoom, set to 0" % (id,)))
        max_zoom = int(cls.__getElemText(xml_root, "./maxZoom", "24","[map info '%s'] invalid max zoom, set to 24" % (id,)))
        min_zoom = cls.__cropValue(min_zoom, 0, 24, "[map info '%s'] min zoom should be in 0~24" % (id,))
        max_zoom = cls.__cropValue(max_zoom, 0, 24, "[map info '%s'] max zoom should be in 0~24" % (id,))
        if min_zoom > max_zoom:
            raise ValueError("[map info '%s'] min_zoom(%d) is larger tahn max_zoom(%d)" % (id, min_zoom, max_zoom))

        tile_type = cls.__getElemText(xml_root, "./tileType", "")
        if tile_type not in ("jpg", "png") :
            raise ValueError("[map info '%s'] not support tile format '%s'" % (id, tile_type))

        url = cls.__getElemText(xml_root, "./url", "")
        if not url or ("{$x}" not in url) or ("{$y}" not in url) or ("{$z}" not in url):
            raise ValueError("[map info '%s'] url not catains {$x}, {$y}, or {$z}: %s" % (id, url))

        lower_corner = cls.__parseLatlon(cls.__getElemText(xml_root, "./lowerCorner", ""), (-180, -85))
        upper_corner = cls.__parseLatlon(cls.__getElemText(xml_root, "./upperCorner", ""), (180, 85))

        #collection data
        desc = MapDescriptor()
        desc.map_id = id
        desc.map_title = name
        desc.level_min = min_zoom
        desc.level_max = max_zoom
        desc.url_template = url
        desc.lower_corner = lower_corner
        desc.upper_corner = upper_corner
        desc.tile_format = tile_type
        desc.tile_side = 256
        return desc

    @classmethod
    def parseXml(cls, filepath=None, xmlstr=None, id=None):
        if filepath is not None:
            xml_root = ET.parse(filepath).getroot()
            if not id:
                id = os.path.splitext(os.path.basename(filepath))[0]
            return cls.__parseXml(xml_root, id)
        elif xmlstr is not None:
            xml_root = ET.fromstring(xmlstr)
            return cls.__parseXml(xml_root, id)
        else:
            return None

    #todo
    @classmethod
    def parseWMTS(cls, filepath, xmlstr=None):
        return []


'''
The agent for getting tiles, using memory cache and db to be efficient.
'''
class TileAgent:
    TILE_VALID       = 0
    TILE_NOT_IN_MEM  = 1
    TILE_NOT_IN_DISK = 2
    TILE_REQ         = 3

    #properties from map_desc
    @property
    def map_id(self): return self.__map_desc.map_id
    @property
    def map_title(self): return self.__map_desc.map_title
    @property
    def level_min(self): return self.__map_desc.level_min
    @property
    def level_max(self): return self.__map_desc.level_max
    @property
    def url_template(self): return self.__map_desc.url_template
    @property
    def lower_corner(self): return self.__map_desc.lower_corner
    @property
    def upper_corner(self): return self.__map_desc.upper_corner
    @property
    def tile_format(self): return self.__map_desc.tile_format
    @property
    def tile_side(self): return self.__map_desc.tile_side

    def __init__(self, map_desc, cache_dir, auto_start=False):
        self.__map_desc = map_desc.clone()

        self.__is_closed = False

        #local cache
        self.__cache_dir = cache_dir
        self.__disk_cache = None

        #memory cache
        self.__mem_cache = MemoryCache(self.TILE_NOT_IN_MEM, is_concurrency=True)

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

        if auto_start:
            self.start()

    def start(self):
        #create cache dir for the map
        self.__disk_cache = DBDiskCache(self.__cache_dir, self.__map_desc, conf.DB_SCHEMA)
        self.__disk_cache.start()
        #start download thread
        self.__download_monitor.start()

    def close(self):
        #notify download monitor to exit
        with self.__download_cv:
            self.__is_closed = True
            self.__download_cv.notify()
        self.__download_monitor.join()

        #close resources
        if self.__disk_cache is not None:
            self.__disk_cache.close()

    def isSupportedLevel(self, level):
        return self.level_min <= level and level <= self.level_max

    def getCachePath(self):
        return os.path.join(self.__cache_dir, self.map_id)

    def genTileId(self, level, x, y):
        return "%s-%d-%d-%d" % (self.map_id, level, x, y)

    def genTileUrl(self, level, x, y):
        url = self.url_template;
        url = url.replace("{$x}", str(x))
        url = url.replace("{$y}", str(y))
        url = url.replace("{$z}", str(level))
        return url

    #The therad to download
    def __runDownloadJob(self, id, level, x, y, cb):
        #do download
        tile_data = None
        try:
            url = self.genTileUrl(level, x, y)
            logging.info("DL " + url)
            with urllib.request.urlopen(url, timeout=30) as response:
                tile_data = response.read()
        except Exception as ex:
            logging.warning('Error to download %s: %s' % (url, str(ex)))
        logging.info('DL %s [%s]' % (url, 'SUCCESS' if tile_data else 'FAILED'))

        #cache
        #(for data coherence, do this before moving self from workers queue: if download thread is done, data is ready)
        if tile_data:
            tile_img = Image.open(BytesIO(tile_data))
            self.__mem_cache.set(id, self.TILE_VALID, tile_img)
        else:
            self.__mem_cache.set(id, self.TILE_NOT_IN_DISK)

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
                logging.warning('Invoke cb of download tile error: ' + str(ex))

            #save file
            try:
                self.__disk_cache.put(level, x, y, tile_data)
            except Exception as ex:
                logging.error('Error to save tile data ' + str(ex))

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
                        logging.warning("WARNING: the req is DUP and in progress.") #should not happen
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

    def __getTileFromDisk(self, level, x, y):
        try:
            data = self.__disk_cache.get(level, x, y)
            if data is not None:
                img = Image.open(BytesIO(data))
                return img
        except Exception as ex:
            logging.warning("Error to read tile data: " + str(ex))
        return None

    def __getTile(self, level, x, y, auto_req=True, cb=None):
        #check level
        if level > self.level_max or level < self.level_min:
            raise ValueError("level is out of range")

        id = self.genTileId(level, x, y)
        img, status, ts = self.__mem_cache.get(id)      #READ FROM memory

        if status == self.TILE_NOT_IN_MEM:
            img = self.__getTileFromDisk(level, x, y)   #READ FROM disk
            if img is not None:
                self.__mem_cache.set(id, self.TILE_VALID, img)
                return img
            if not auto_req:
                self.__mem_cache.set(id, self.TILE_NOT_IN_DISK)
                return None
            status = self.TILE_NOT_IN_DISK  #go through to the next status

        if status == self.TILE_NOT_IN_DISK:
            if auto_req:
                self.__mem_cache.set(id, self.TILE_REQ)
                self.__requestTile(id, level, x, y, cb) #READ FROM WMTS (async)
            return None
        elif status == self.TILE_VALID:
            return img
        elif status == self.TILE_REQ:
            return None
        else:
            logging.error('Error: unknown tile status: %d' % (status,))
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

class MemoryCache:
    '''
    class Item:
        self.__init__(data=None, status=None, timestamp=None):
        self.data = data
        self.status = status
        self.timestamp = timestamp
    '''

    @property
    def is_concurrency(self):
        return self.__repo_lock is not None

    def __init__(self, init_status, is_concurrency=False):
        self.__init_status = init_status
        self.__repo = {}
        self.__repo_lock = Lock() if is_concurrency else None

    def __set(self, id, status, data):
        self.__repo[id] = (data, status, datetime.now())

    def __get(self, id):
        item = self.__repo.get(id)
        if item is None:
            item = (None, self.__init_status, datetime.now())
            self.__repo[id] = item
        return item

    def set(self, id, status, data=None):
        if self.is_concurrency:
            with self.__repo_lock:
                self.__set(id, status, data)
        else:
            self.__set(id, status, data)

    def get(self, id):
        if self.is_concurrency:
            with self.__repo_lock:
                return self.__get(id)
        else:
            return self.__get(id)

class DiskCache:
    def start(self):
        pass

    def close(self):
        pass

    def put(self, level, x, y, data):
        pass

    def get(self, level, x, y):
        pass

class FileDiskCache(DiskCache):
    def __init__(self, cache_dir, map_desc):
        self.__cache_dir = os.path.join(cache_dir, map_desc.map_id) #create subfolder
        self.__map_desc = map_desc

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

class DBDiskCache(DiskCache):
    def __init__(self, cache_dir, map_desc, db_schema, is_concurrency=True):
        self.__db_path = os.path.join(cache_dir, map_desc.map_id + ".mbtiles")
        self.__db_schema = db_schema
        self.__map_desc = map_desc
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
        def getBoundsText(map_desc):
            left, bottom = map_desc.lower_corner
            right, top   = map_desc.upper_corner
            bounds = "%f,%f,%f,%f" % (left, bottom, right, top) #OpenLayers Bounds format
            return bounds

        desc = self.__map_desc
        conn = self.__conn

        #meatadata
        meta_create_sql = "CREATE TABLE metadata(name TEXT PRIMARY KEY, value TEXT)"
        meta_data_sqls = ("INSERT INTO metadata(name, value) VALUES('%s', '%s')" % ('name', desc.map_id),
                          "INSERT INTO metadata(name, value) VALUES('%s', '%s')" % ('type', 'overlayer'),
                          "INSERT INTO metadata(name, value) VALUES('%s', '%s')" % ('version', '1.0'),
                          "INSERT INTO metadata(name, value) VALUES('%s', '%s')" % ('description', desc.map_title),
                          "INSERT INTO metadata(name, value) VALUES('%s', '%s')" % ('format', desc.tile_format),
                          "INSERT INTO metadata(name, value) VALUES('%s', '%s')" % ('bounds', getBoundsText(desc)),
                          "INSERT INTO metadata(name, value) VALUES('%s', '%s')" % ('schema', self.__db_schema),
                         )
        #tiles
        tiles_create_sql = "CREATE TABLE tiles("
        tiles_create_sql += "zoom_level  INTEGER, "
        tiles_create_sql += "tile_column INTEGER, "
        tiles_create_sql += "tile_row    INTEGER, "
        tiles_create_sql += "tile_data   BLOB     NOT NULL, "
        tiles_create_sql += "PRIMARY KEY (zoom_level, tile_column, tile_row))"

        #tiles_idx
        tiles_idx_create_sql = "CREATE INDEX tiles_idx on tiles(zoom_level, tile_column, tile_row)"

        #exec
        conn.execute(meta_create_sql)
        conn.execute(tiles_create_sql)
        conn.execute(tiles_idx_create_sql)
        for sql in meta_data_sqls:
            conn.execute(sql)
        conn.commit()

    def __getMetadata(self, name):
        try:
            sql = 'SELECT value FROM metadata WHERE name="%s"' % (name,)
            cursor = self.__conn.execute(sql)
            row = cursor.fetchone()
            data = None if row is None else row[0]
            return data
        except Exception as ex:
            logging.warning('Get mbtiles metadata error: ' + str(ex))

        return None

    def __readMetadata(self):
        #overwrite db schema from metadta
        schema = self.__getMetadata('schema')
        if schema and self.__db_schema != schema:
            self.__db_schema = schema
            logging.info('Reset db schema to %s' % (self.__db_schema,))

    #the true actions which are called by Surrogate
    def __start(self):
        logging.info("The db schema default of '%s' is %s" % (self.__map_desc.map_id, self.__db_schema))
        if not os.path.exists(self.__db_path):
            logging.info("Initializing local cache DB '%s'..." % (self.__map_desc.map_id,))
            mkdirSafely(os.path.dirname(self.__db_path))
            self.__conn = sqlite3.connect(self.__db_path)
            self.__initDB()
        else:
            self.__conn = sqlite3.connect(self.__db_path)
            self.__readMetadata()

    def __close(self):
        logging.info("Closing local cache DB '%s'..." % (self.__map_desc.map_id,))
        self.__conn.close()

    @classmethod
    def __flipY(cls, y, z):
        max_y = (1 << z) -1
        return max_y - y


    def __put(self, level, x, y, data):
        ex = None
        try:
            if self.__db_schema == 'tms':
                y = self.__flipY(y, level)
            sql = "INSERT OR REPLACE INTO tiles(zoom_level, tile_column, tile_row, tile_data) VALUES(%d, %d, %d, ?)" % \
                    (level, x, y)
            self.__conn.execute(sql, (data,))
            self.__conn.commit()
        except Exception as _ex:
            ex = _ex

        logging.info("%s [%s]" % (sql, ("Fail" if ex else "OK")))
        if ex:
            raise ex

    def __get(self, level, x, y):
        data, ex = None, None
        try:
            if self.__db_schema == 'tms':
                y = self.__flipY(y, level)
            sql = "SELECT tile_data FROM tiles WHERE zoom_level=%d AND tile_column=%d AND tile_row=%d" % (level, x, y)
            cursor = self.__conn.execute(sql)
            row = cursor.fetchone()
            data = None if row is None else row[0]
        except Exception as _ex:
            ex = _ex

        logging.info("%s [%s]" % (sql, ("Fail" if ex else "OK" if data else "NA")))
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
                #add TILE_req
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
                        logging.error("DB put data error: " + str(ex))
                #get data
                else:
                    res_data, res_ex = None, None
                    try:
                        res_data = self.__get(level, x, y)
                        res_ex = None
                    except Exception as ex:
                        logging.error("DB get data error: " + str(ex))
                        res_data = None
                        res_ex = ex

                    #notify
                    with self.__get_respose_cv:
                        self.__get_respose = (res_data, res_ex)
                        self.__get_respose_cv.notify()

        finally:
            self.__close()

if __name__ == '__main__':
    desc = MapDescriptor.parseXml("mapcache/TM25K_2001.xml")
    desc.save("mapcache", id="TM25K_2001-2")
    desc.save(".")
