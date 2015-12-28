#!/usr/bin/env python3

import os
import shutil

if __name__ == '__main__':
    base = '/home/dayanuyim/Dropbox/backup/mapcache'

    #TM25K_2001-16-54869-28139.jpg
    for dirpath, dirnames, filenames in os.walk(base):
        for f in filenames:
            tokens = f.split('-', 2)
            if len(tokens) != 3:
                continue
            map = tokens[0]
            level = tokens[1]
            tile = tokens[2]
            src = os.path.join(dirpath, f)
            dst = os.path.join(base, map, level, tile)
            shutil.move(src, dst)

        

