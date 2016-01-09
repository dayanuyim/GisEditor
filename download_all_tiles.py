#!/usr/bin/env python3
# -*- coding: utf8 -*-

import sys
sys.path.insert(0, 'src')

import tile
from tile import TileSystem

import urllib.request
import shutil
import threading
from threading import Thread, Lock
import time
import os

CACHE_DIR = "mapcache"
MAX_THREAD = 5
thread_lock = Lock()
thread_pool = []

def downloadJob(tile_map, level, x, y):
    #do download
    result_ok = False
    try:
        url = tile_map.genTileUrl(level, x, y)
        path = tile_map.genTilePath(level, x, y)
        print('DL', url)
        with urllib.request.urlopen(url, timeout=30) as response:
            tile.mkdirCheck(os.path.dirname(path))
            with open(path, 'wb') as f:
                shutil.copyfileobj(response, f)
        result_ok = True
    except Exception as ex:
        print('ERROR download %s to %s error: %s' % (url, path, str(ex)))

    #result
    print('DL %s [%s]' % (url, 'SUCCESS' if result_ok else 'FAILED'))

    #remove from pool
    myself = threading.current_thread()
    with thread_lock:
        thread_pool.remove(myself)

if __name__ == '__main__':
    #main island of Taiwan
    low_lat, up_lat = 21.876792, 25.373809
    left_lon, right_lon = 120.020142, 122.025146

    #TM25Kv3
    cdir = sys.argv[1] if len(sys.argv) > 1 else CACHE_DIR
    map = tile.getTM25Kv3TileMap(cache_dir=cdir)

    for level in range(map.level_min, map.level_max+1):
        min_x, min_y = TileSystem.getTileXYByLatLon(up_lat, left_lon, level)
        max_x, max_y = TileSystem.getTileXYByLatLon(low_lat, right_lon, level)
        total = (max_x - min_x + 1) * (max_y - min_y + 1)
        print("Download Tiles in level %d, X,Y=(%d->%d, %d->%d), total %d tiles" % (level, min_x, max_x, min_y, max_y, total))

        count = 0
        for x in range(min_x, max_x+1):
            for y in range(min_y, max_y+1):
                count += 1
                #check
                path = map.genTilePath(level, x, y)
                if os.path.exists(path) and os.path.getsize(path):
                    #print("SKIP tile(%d,%d,%d)...%d/%d" % (level, x, y, count, total))
                    continue

                #wait thread_pool available
                while True:
                    with thread_lock:
                        if len(thread_pool) < MAX_THREAD:
                            break
                    print('.', end='')
                    time.sleep(1)

                #download
                print("DL tile(%d,%d,%d)...%d/%d" % (level, x, y, count, total))
                job = lambda: downloadJob(map, level, x, y)
                th = Thread(target=job)
                with thread_lock:
                    thread_pool.append(th)
                th.start()
    map.close()




