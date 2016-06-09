#!/usr/bin/env python2.6


from dbprocessing import DButils
from __future__ import print_function


if __name__ == "__main__":
    a = DButils.DButils('rbsp')
    a.openDB()
    a._createTableObjects()
    f = a.getAllFilenames()
    for ff in f:
        a.purgeFileFromDB(ff[0])
    print('deleted {0} files'.format(len(f)))

