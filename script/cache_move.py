#!/usr/bin/env python3

import os
import shutil

if __name__ == '__main__':
    src_dir = '/home/dayanuyim/DropboxExt/mapcache'
    dst_dir = '/home/dayanuyim/DropboxExt/mapcache2'

    #TM25K_2001-16-54869-28139.jpg
    for dirpath, dirnames, filenames in os.walk(src_dir):
        #parse level and map_id
        level = os.path.basename(dirpath)
        if not level.isdigit():
            continue
        map_id = os.path.basename(os.path.dirname(dirpath))
        for f in filenames:
            #parse x, y
            tokens = f.split('-')
            if len(tokens) != 2:
                print('not target file: %s, %s', (dirpath, f))
                continue
            x = tokens[0]
            y_ext = tokens[1]

            #gen name
            name = "%s-%s-%s" % (level, x, y_ext)

            #copy
            src = os.path.join(dirpath, f)
            dst = os.path.join(dst_dir, map_id, x)
            if not os.path.exists(dst):
                os.makedirs(dst)
            dst = os.path.join(dst, name)
            #print('copy %s to \n    %s' % (src, dst))
            shutil.move(src, dst)

        

