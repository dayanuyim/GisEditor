#!/usr/bin/env python3
# -*- coding: utf8 -*-

"""handle for tile system, especially WMTS"""

import os
import math
import tkinter as tk
import urllib.request
import shutil
import sqlite3
import logging
import random
import time
from xml.etree import ElementTree as ET
from datetime import datetime, timedelta
from os import listdir
from os.path import isdir, isfile, exists
from PIL import Image, ImageTk, ImageDraw, ImageTk
from threading import Thread, Lock, Condition
from math import tan, sin, cos, radians, degrees
from collections import OrderedDict
from io import BytesIO

import coord
import conf
import util
from util import mkdirSafely, saveXml

to_pixel = coord.TileSystem.getPixcelXYByTileXY
to_tile = coord.TileSystem.getTileXYByPixcelXY

class MapDescriptor:
    #should construct from static methods.
    def __init__(self):
        #NOTEICE: see clone() method to see full fields

        #set default value
        self.enabled = False
        self.alpha = 1.00

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

        url = ET.SubElement(root, "url")
        url.text = self.url_template

        if self.server_parts:
            server_parts = ET.SubElement(root, "serverParts")
            server_parts.text = " ".join(self.server_parts)

        if self.invert_y:
            invert_y = ET.SubElement(root, "invertYCoordinate")
            invert_y.text = "true" if self.invert_y else "false"

        if self.coord_sys:
            coord_sys = ET.SubElement(root, "coordinatesystem")
            coord_sys.text = self.coord_sys

        lower_corner = ET.SubElement(root, "lowerCorner")
        lower_corner.text = "%.9f %.9f" % self.lower_corner

        upper_corner = ET.SubElement(root, "upperCorner")
        upper_corner.text = "%.9f %.9f" % self.upper_corner

        #bgcolor = ET.SubElement(root, "backgroundColor")
        #bgcolor.text = "#FFFFFF"

        #tile_update = ET.SubElement(root, "tileUpdate")
        #tile_update.text = "IfNotMatch"

        if self.expire_sec:
            exp_text = "%.3f" % (self.expire_sec / 86400.0,)
            if exp_text.endswith(".000"):
                exp_text = exp_text[:-4]
            expire = ET.SubElement(root, "expireDays")
            expire.text = exp_text

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
        desc.tile_format = self.tile_format
        desc.url_template = self.url_template
        desc.server_parts = self.server_parts
        desc.invert_y = self.invert_y
        desc.coord_sys = self.coord_sys
        desc.lower_corner = self.lower_corner
        desc.upper_corner = self.upper_corner
        desc.expire_sec = self.expire_sec
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
    def __parseExpireDays(cls, expire_txt, id):
        try:
            expire_val = float(expire_txt)
            return int(expire_val * 86400)
        except Exception as ex:
            logging.warning("[map desc '%s'] parsing expire_days '%s', error: %s" % (id, expire_txt, str(ex)))
        return 0

    @classmethod
    def __parseXml(cls, xml_root, id):
        if not id:
            raise ValueError("[map desc] map id is empty")

        name = cls.__getElemText(xml_root, "./name", "")
        if not name:
            raise ValueError("[map desc '%s'] no map name" % (id,))

        min_zoom = int(cls.__getElemText(xml_root, "./minZoom", "0", "[map desc '%s'] invalid min zoom, set to 0" % (id,)))
        max_zoom = int(cls.__getElemText(xml_root, "./maxZoom", "24","[map desc '%s'] invalid max zoom, set to 24" % (id,)))
        min_zoom = cls.__cropValue(min_zoom, 0, 24, "[map desc '%s'] min zoom should be in 0~24" % (id,))
        max_zoom = cls.__cropValue(max_zoom, 0, 24, "[map desc '%s'] max zoom should be in 0~24" % (id,))
        if min_zoom > max_zoom:
            raise ValueError("[map desc '%s'] min_zoom(%d) is larger tahn max_zoom(%d)" % (id, min_zoom, max_zoom))

        tile_type = cls.__getElemText(xml_root, "./tileType", "").lower()
        if tile_type not in ("jpg", "png") :
            raise ValueError("[map desc '%s'] not support tile format '%s'" % (id, tile_type))

        url = cls.__getElemText(xml_root, "./url", "")
        if not url or ("{$x}" not in url) or ("{$y}" not in url) or ("{$z}" not in url):
            raise ValueError("[map desc '%s'] url not catains {$x}, {$y}, or {$z}: %s" % (id, url))

        server_parts = cls.__getElemText(xml_root, "./serverParts", "")

        invert_y = cls.__getElemText(xml_root, "./invertYCoordinate", "false").lower()
        if invert_y not in ("false", "true"):
            logging.warning("[map desc '%s'] invalid invertYCoordinate value: '%s', set to 'false'" % (id, invert_y))


        coord_sys = cls.__getElemText(xml_root, "./coordinatesystem", "EPSG:4326").upper()

        lower_corner = cls.__parseLatlon(cls.__getElemText(xml_root, "./lowerCorner", ""), (-180, -85))
        upper_corner = cls.__parseLatlon(cls.__getElemText(xml_root, "./upperCorner", ""), (180, 85))

        expire_days = cls.__getElemText(xml_root, "./expireDays", "0")
        expire_sec = cls.__parseExpireDays(expire_days, id)

        #collection data
        desc = MapDescriptor()
        desc.map_id = id
        desc.map_title = name
        desc.level_min = min_zoom
        desc.level_max = max_zoom
        desc.url_template = url
        desc.server_parts = server_parts.split(' ') if server_parts else None
        desc.invert_y = (invert_y == "true")
        desc.coord_sys = coord_sys
        desc.lower_corner = lower_corner
        desc.upper_corner = upper_corner
        desc.expire_sec = expire_sec
        desc.tile_format = tile_type
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
    ST_IDLE    = 0
    ST_RUN     = 1
    ST_PAUSE   = 2
    ST_CLOSING = 3

    TILE_VALID       = 0x00
    TILE_NOT_IN_MEM  = 0x01
    TILE_NOT_IN_DISK = 0x02
    TILE_EXPIRE      = 0x03
    TILE_REQ         = 0x10
    TILE_REQ_FAILED  = 0x20

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
    def server_parts(self): return self.__map_desc.server_parts
    @property
    def invert_y(self): return self.__map_desc.invert_y
    @property
    def coord_sys(self): return self.__map_desc.coord_sys
    @property
    def lower_corner(self): return self.__map_desc.lower_corner
    @property
    def upper_corner(self): return self.__map_desc.upper_corner
    @property
    def expire_sec(self): return self.__map_desc.expire_sec
    @property
    def tile_format(self): return self.__map_desc.tile_format

    @property
    def state(self): return self.__state

    def __init__(self, map_desc, cache_dir, auto_start=False):
        self.__map_desc = map_desc.clone()

        self.__state = self.ST_IDLE

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
        self.__state = self.ST_RUN
        self.__download_monitor.start()

    def close(self):
        #notify download monitor to exit
        with self.__download_cv:
            self.__state = self.ST_CLOSING
            self.__download_cv.notify()
        self.__download_monitor.join()

        #close resources
        if self.__disk_cache is not None:
            self.__disk_cache.close()

    def pause(self):
        with self.__download_cv:
            if self.__state == self.ST_RUN:
                self.__state = self.ST_PAUSE
                logging.debug("[%s] Change status from run to pause" % (self.map_id,))
                self.__download_cv.notify()

    def resume(self):
        with self.__download_cv:
            if self.__state == self.ST_PAUSE:
                self.__state = self.ST_RUN
                logging.debug("[%s] Change status from pasue to run" % (self.map_id,))
                self.__download_cv.notify()

    def isSupportedLevel(self, level):
        return self.level_min <= level and level <= self.level_max

    def getCachePath(self):
        return os.path.join(self.__cache_dir, self.map_id)

    def genTileId(self, level, x, y):
        return "%s-%d-%d-%d" % (self.map_id, level, x, y)

    @classmethod
    def flipY(cls, y, level):
        return (1 << level) - 1 - y

    def genTileUrl(self, level, x, y):
        if self.invert_y:
            y = self.flipY(y, level)

        url = self.url_template;

        if self.server_parts:
            url = url.replace("{$serverpart}", random.choice(self.server_parts))
        url = url.replace("{$x}", str(x))
        url = url.replace("{$y}", str(y))
        url = url.replace("{$z}", str(level))
        #logging.critical('url: ' + url)
        return url

    def __downloadTile(self, id, req):
        level, x, y, status, cb = req  #unpack the req

        tile_data = None
        try:
            url = self.genTileUrl(level, x, y)
            logging.info("[%s] DL %s" % (self.map_id, url))
            with urllib.request.urlopen(url, timeout=30) as response:
                tile_data = response.read()
        except Exception as ex:
            logging.warning('[%s] Error to download %s: %s' % (self.map_id, url, str(ex)))
        logging.info('[%s] DL %s [%s]' % (self.map_id, url, 'SUCCESS' if tile_data else 'FAILED'))

        #as failed, and not save to memory/disk
        if self.__state == self.ST_CLOSING:
            return None

        if tile_data is None:
            #save to memory
            status = self.TILE_REQ_FAILED | (status & 0x0F)
            self.__mem_cache.set(id, status)
            return None
        else:
            #save to memory
            tile_img = Image.open(BytesIO(tile_data))
            self.__mem_cache.set(id, self.TILE_VALID, tile_img)

            #save to disk
            try:
                self.__disk_cache.put(level, x, y, tile_data)
            except Exception as ex:
                logging.error("[%s] Error to save tile data: %s" % (self.map_id, str(ex)))

            #notify
            try:
                if cb is not None:
                    cb(level, x, y)
            except Exception as ex:
                 logging.warning("[%s] Invoke cb of download tile error: %s" % (self.map_id, str(ex)))

            return tile_img

    #The therad to download
    def __runDownloadJob(self, id, req):

        #do download
        tile_img = self.__downloadTile(id, req)

        #the download is done
        #(do this before thread exit, to ensure monitor is notified)
        with self.__download_cv:
            self.__workers.pop(id, None)
            self.__download_cv.notify()
            #premature done
            if self.__state == self.ST_CLOSING:
                return

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

                if self.__state == self.ST_CLOSING:
                    logging.debug("[%s] status(closing), download monitor closing" % (self.map_id,))
                    break
                elif self.__state == self.ST_PAUSE:
                    logging.debug("[%s] status(pause), continue to wait" % (self.map_id,))
                    continue

                if len(self.__req_queue) > 0 and len(self.__workers) < self.__MAX_WORKS:
                    #the req
                    id, req = self.__req_queue.popitem() #LIFO
                    if id in self.__workers:
                        logging.warning("[%s] Opps! the req is DUP and in progress." % (self.map_id,)) #should not happen
                    else:
                        #create the job and run the worker
                        job = lambda: self.__runDownloadJob(id, req)
                        worker = Thread(name=id, target=job)
                        self.__workers[id] = worker
                        worker.start()

        #todo: interrupt urllib.request.openurl to stop download workers.
        #http_handler.close()
        with self.__download_cv:
            #self.__download_cv.wait_for(no_worker)
            self.__state = self.ST_IDLE
            logging.debug("[%s] status(idle), download monitor closed" % (self.map_id,))

    def __requestTile(self, id, req):
        #check and add to req queue
        with self.__download_cv:
            if id in self.__req_queue:
                return
            if id in self.__workers:
                return
            #add the req
            self.__req_queue[id] = req
            self.__download_cv.notify()

    def __getTileFromDisk(self, level, x, y):
        try:
            data, ts = self.__disk_cache.get(level, x, y)
            if data is not None:
                img = Image.open(BytesIO(data))
                return img, ts
        except Exception as ex:
            logging.warning("[%s] Error to read tile data: %s" % (self.map_id, str(ex)))
        return None, None

    def __notifyTileReady(self, level, x, y, cb):
        try:
            if cb is not None:
                cb(level, x, y)
        except Exception as ex:
            logging.error("invoke cb for tile ready error: %s" % (self.map_id, str(ex)))

    def __getTile(self, level, x, y, req_type=None, cb=None):
        #check level
        if level > self.level_max or level < self.level_min:
            raise ValueError("level is out of range")

        id = self.genTileId(level, x, y)
        img, status, ts = self.__mem_cache.get(id)      #READ FROM memory
        status_bak = status

        if status == self.TILE_VALID:
            return img

        if (status & 0xF0) == self.TILE_REQ:
            return img    # None or Expire

        if (status & 0xF0) == self.TILE_REQ_FAILED:
            if (time.time() - ts) < 60: #todo: user to specify retry period
                return None
            status &= 0x0F    #remove req_failed status

        if status == self.TILE_NOT_IN_MEM:
            img, ts = self.__getTileFromDisk(level, x, y)   #READ FROM disk
            if img is None:
                status = self.TILE_NOT_IN_DISK
            elif ts and self.expire_sec and (time.time() - ts) > self.expire_sec:
                status = self.TILE_EXPIRE
            else:
                self.__mem_cache.set(id, self.TILE_VALID, img)
                return img

        #check status, should be 'not in disk' or 'expire'
        if status == self.TILE_NOT_IN_DISK:
            pass
        elif status == self.TILE_EXPIRE:
            logging.warning("[%s] Tile(%d,%d,%d) is expired" % (self.map_id, level, x, y))
        else:
            logging.critical("[%s] Error: unexpected tile status: %d" % (self.map_id, status))
            return None

        #req or not
        if not req_type:
            if status != status_bak:
                self.__mem_cache.set(id, status)
            return img
        else:
            status |= self.TILE_REQ
            self.__mem_cache.set(id, status)
            if req_type == "async":
                self.__requestTile(id, (level, x, y, status, cb))
                return img
            else:      # sync
                img = self.__downloadTile(id, (level, x, y, status, None))
                self.__notifyTileReady(level, x, y, cb)
                return img

    def __genMagnifyFakeTile(self, level, x, y, diff=1):
        side = to_pixel(1,1)[0]
        for i in range(1, diff+1):
            scale = 2**i
            img = self.__getTile(level-i, int(x/scale), int(y/scale))
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
        side = to_pixel(1,1)[0]

        for i in range(1, diff+1):
            scale = 2**i
            img = Image.new("RGBA", (side*scale, side*scale), bg)
            has_tile = False
            #paste tiles
            for p in range(scale):
                for q in range(scale):
                    t = self.__getTile(level+i, x*scale+p, y*scale+q)
                    if t:
                        img.paste(t, (p*side, q*side))
                        has_tile = True
            #minify
            if has_tile:
                img = img.resize((side,side))
                return img
        return None

    #gen fake from lower/higher level
    #return None if not avaliable
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

        return None

    def getTile(self, level, x, y, req_type, cb=None, allow_fake=True):
        img = self.__getTile(level, x, y, req_type, cb)
        if img is not None:
            img.is_fake = False
            return img

        if allow_fake:
            img = self.__genFakeTile(level, x, y)
            if img is not None:
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
        if data is None:      #using old data
            item = self.__repo.get(id)
            if item is not None:
                data = item[0]
        self.__repo[id] = (data, status, time.time())

    def __get(self, id):
        item = self.__repo.get(id)
        if item is None:
            item = (None, self.__init_status, time.time())
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
    @property
    def map_id(self):
        return self.__map_desc.map_id

    def __init__(self, cache_dir, map_desc, db_schema, is_concurrency=True):
        self.__map_desc = map_desc
        self.__db_path = os.path.join(cache_dir, map_desc.map_id + ".mbtiles")
        self.__conn = None

        #configs
        self.__db_schema = db_schema
        self.__has_timestamp = True

        self.__is_concurrency = is_concurrency

        if is_concurrency:
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
        tiles_create_sql += "timestamp   INTEGER  NOT NULL, "
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
            logging.warning('[%s] Get mbtiles metadata error: %s' % (self.map_id, str(ex)))
        return None

    def __tableHasColumn(self, tbl_name, col_name):
        try:
            sql = "PRAGMA table_info(%s)" % tbl_name
            cursor = self.__conn.execute(sql)
            rows = cursor.fetchall()

            for row in rows:
                if row[1] == col_name:
                    return True

        except Exception as ex:
            logging.warning("[%s] detect table '%s' has column '%s' error: %s" % (self.map_id, tbl_name, col_name, str(ex)))
        return False

    def __readConfig(self):
        #db schema from metadta
        schema = self.__getMetadata('schema')
        if schema and self.__db_schema != schema:
            logging.info("[%s] Reset db schema from %s to %s" % (self.map_id, self.__db_schema, schema))
            self.__db_schema = schema

        self.__has_timestamp = self.__tableHasColumn("tiles", "timestamp")

    #the true actions which are called by Surrogate
    def __start(self):
        if not os.path.exists(self.__db_path):
            logging.info("[%s] Initializing local cache DB..." % (self.map_id,))
            mkdirSafely(os.path.dirname(self.__db_path))
            self.__conn = sqlite3.connect(self.__db_path)
            self.__initDB()
        else:
            self.__conn = sqlite3.connect(self.__db_path)
            self.__readConfig()

        logging.info("[%s][Config] db schema: %s" % (self.map_id, self.__db_schema))
        logging.info("[%s][Config] suuport tile timestamp: %s" % (self.map_id, self.__has_timestamp))

    def __close(self):
        logging.info("[%s] Closing local cache DB..." % (self.map_id,))
        self.__conn.close()

    @classmethod
    def flipY(cls, y, level):
        return (1 << level) - 1 - y

    def __put(self, level, x, y, data):
        #sql
        if self.__db_schema == 'tms':
            y = self.flipY(y, level)

        sql = None
        if self.__has_timestamp:
            sql  = "INSERT OR REPLACE INTO tiles(zoom_level, tile_column, tile_row, tile_data, timestamp)"
            sql += " VALUES(%d, %d, %d, ?, %d)" % (level, x, y, int(time.time()))
        else:
            sql = "INSERT OR REPLACE INTO tiles(zoom_level, tile_column, tile_row, tile_data)"
            sql += " VALUES(%d, %d, %d, ?)" % (level, x, y)

        #query
        try:
            self.__conn.execute(sql, (data,))
            self.__conn.commit()
            logging.info("[%s] %s [OK]" % (self.map_id, sql))
        except Exception as ex:
            logging.info("[%s] %s [Fail]" % (self.map_id, sql))
            raise ex

    def __get(self, level, x, y):
        #sql
        if self.__db_schema == 'tms':
            y = self.flipY(y, level)

        cols = "tile_data, timestamp" if self.__has_timestamp else "tile_data"
        sql = "SELECT %s FROM tiles WHERE zoom_level=%d AND tile_column=%d AND tile_row=%d" % \
                (cols, level, x, y,)

        row = None
        try:
            #query
            cursor = self.__conn.execute(sql)
            row = cursor.fetchone()
        except Exception as ex:
            logging.info("[%s] %s [Fail]" % (self.map_id, sql))
            raise ex

        #result (tile, timestamp)
        if row is None:
            logging.info("[%s] %s [NA]" % (self.map_id, sql))
            return (None, None)
        elif self.__has_timestamp:
            logging.info("[%s] %s [OK][TS]" % (self.map_id, sql))
            return row
        else:
            logging.info("[%s] %s [OK]" % (self.map_id, sql))
            return (row[0], None)

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
            return self.__get(level, x, y)
        else:
            def has_respose():
                return self.__get_respose is not None

            with self.__get_lock:  #for blocking the continuous get
                #req tile
                with self.__sql_queue_cv:
                    item = (level, x, y, None)
                    self.__sql_queue.insert(0, item)  #service first
                    self.__sql_queue_cv.notify()

                #wait resposne
                res = None
                with self.__get_respose_cv:
                    self.__get_respose_cv.wait_for(has_respose)
                    res, self.__get_respose = self.__get_respose, res   #swap: pop response of get()

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
                        logging.error("[%s] DB put data error: %s" % (self.map_id, str(ex)))
                #get data
                else:
                    res_data, res_ex = None, None
                    try:
                        res_data = self.__get(level, x, y)
                        res_ex = None
                    except Exception as ex:
                        logging.error("[%s] DB get data error: %s" % (self.map_id, str(ex)))
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
