import glob
import os
import shutil


filenames = glob.glob(".cache/*.json")
for fn in filenames:
    fn = os.path.basename(fn)
    prefix = fn[0:3]
    dstdir = os.path.join('.cache', prefix)
    if not os.path.exists(dstdir):
        os.makedirs(dstdir)
    src = os.path.join('.cache', fn)
    dst = os.path.join('.cache', prefix, fn)
    print(f'{src} -> {dst}')
    shutil.move(src, dst)
    #import epdb; epdb.st()
