#!/usr/bin/env python3

import sys
sys.path.insert(0, 'src')

import os
import shutil
import tile


if __name__ == '__main__':
    src_dir = '/home/dayanuyim/DropboxExt/mapcache/TM25K_2001'
    dst_dir = '/home/dayanuyim/DropboxExt/mapcache'

    tm = tile.getTM25Kv3TileMap('/tmp', False)
    db = tile.DBLocalCache(dst_dir, tm, is_concurrency=False)
    db.start()
    try:
        for dirpath, dirnames, filenames in os.walk(src_dir):
            map_id = os.path.basename(os.path.dirname(dirpath))
            print('Reading the dir:', dirpath)
            for f in filenames:
                #parse level, x, y
                tokens = f.split('-')
                if len(tokens) != 3:
                    print('not target file: %s, %s', (dirpath, f))
                    continue
                level = int(tokens[0])
                x = int(tokens[1])
                y = int(tokens[2].split('.')[0])

                #read file into DB
                filepath = os.path.join(dirpath, f)
                #print('read file %s, level=%d, x=%d, y=%d' % (filepath, level, x, y))
                with open(filepath, 'rb') as tile_file:
                    data = tile_file.read()
                    db.put(level, x, y, data)
    finally:
        db.close()
        

