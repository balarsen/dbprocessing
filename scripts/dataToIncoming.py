#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-
from __future__ import division

import ConfigParser
import copy
import datetime
import glob
import fnmatch
import itertools
import shutil
import subprocess
from optparse import OptionParser
import os
from operator import itemgetter, attrgetter

import dateutil.parser as dup
import numpy as np
import spacepy.toolbox as tb

from dbprocessing import Utils
from dbprocessing import DBUtils

def readconfig(config_filepath):
    # Create a ConfigParser object, to read the config file
    cfg=ConfigParser.SafeConfigParser()
    cfg.read(config_filepath)
    sections = cfg.sections()
    # Read each parameter in turn
    ans = {}
    for section in sections:
        ans[section] = dict(cfg.items(section))
    return ans

def _fileTest(filename):
    """
    open up the file as txt and do a check that there are no repeated section headers
    """
    def rep_list(inval):
        seen = set()
        seen_twice = set( x for x in inval if x in seen or seen.add(x) )
        return list(seen_twice)

    with open(filename, 'r') as fp:
        data = fp.readlines()
    data = [v.strip() for v in data if v[0] == '[']
    seen_twice = rep_list(data)
    if seen_twice:
        raise(ValueError('Specified section(s): "{0}" is repeated!'.format(seen_twice) ))

def _processSubs(conf):
    """
    go through the conf object and deal with any substitutions

    this works by looking for {}
    """
    for key in conf:
        for v in conf[key]:
            while True:
                if isinstance(conf[key][v], (str,unicode)):
                    if '{' in conf[key][v] and '}' in conf[key][v]:
                        sub = conf[key][v].split('{')[1].split('}')[0]
                        if sub == 'Y':
                            sub_v = '????'
                        else:
                            raise(NotImplementedError("Unsupported substitution {0} found".format(sub)))
                        conf[key][v] = conf[key][v].replace('{' + sub + '}', sub_v)
                    else:
                        break
                else:
                    break
    return conf

def _processBool(conf):
    for k in conf:
        if 'link' in conf[k]:
            conf[k]['link'] = Utils.toBool(conf[k]['link'])
    return conf


def getFilesFromDisk(conf):
    """
    given a partial config file return the files on disk
    ** this returns full path

    this is done as conf['sync1'] from teh upper level
    """
    ans = glob.glob(os.path.join(conf['source'], conf['glob']))
    return ans


def getFilesFromDB(conf, dbu):
    """
    given the same conf get the files form the database
    ** rememebnr that filenames have to be unique

    this returns only basename
    """
    files = dbu.session.query(dbu.File.filename).filter(dbu.File.filename.like(conf['like'])).all()
    files = map(itemgetter(0), files)
    return files
    

def basenameToFullname(diff, diskfiles):
    """
    diff is the files that we need to find in diskfiles
    """
    ans = []
    for d in diff:
        a2 = [v for v in diskfiles if d in v]
        ans.extend(a2)
    return ans

def makeLinks(files, incoming):
    """
    given an incoming desitroy (destination) and files make symlinks between them
    """
    good = 0
    bad = 0
    for f in files:
        newf = os.path.join(incoming, os.path.basename(f))
        try:
            os.symlink(f, newf)
            print("Symlink: {0}->{1}".format(f, newf))
            good += 1
        except OSError:
            bad += 1
    return good, bad
    
def copyFiles(files, incoming):
    """
    given an incoming desitroy (destination) and files copy files between them
    """
    good = 0
    bad = 0
    for f in files:
        newf = os.path.join(incoming, os.path.basename(f))
        try:
            shutil.copy(f, incoming)
            print("Copy: {0}->{1}".format(f, newf)) 
            good += 1
        except shutil.Error:
            bad += 1
    return good, bad

if __name__ == "__main__":
    usage = "usage: %prog [options] configfile"
    parser = OptionParser(usage=usage)

    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("incorrect number of arguments")

    conffile = os.path.expanduser(os.path.expandvars(os.path.abspath(args[0])))
    if not os.path.isfile(conffile):
        parser.error("could not read config file: {0}".format(conffile))
        
    conf = readconfig(conffile)
    conf = _processSubs(conf)
    conf = _processBool(conf)
    print('Read and parsed config file: {0}'.format(conffile))

    dbu = DBUtils.DBUtils(conf['settings']['mission'])

    inc_dir = dbu.getIncomingPath()
    
    for k in conf:
        if not k.startswith('sync'):
            continue # this is not a sync
        diskfiles = getFilesFromDisk(conf[k])
        print("Found {0} files on disk".format(len(diskfiles)))
        dbfiles = getFilesFromDB(conf[k], dbu)
        print("Found {0} files in db".format(len(dbfiles)))

        # the files that need to be linked or copied are the set difference
        df2 = set([os.path.basename(v) for v in diskfiles])
        diff = df2.difference(set(dbfiles))
        # the files in diff need to be found in the full path
        tocopy = basenameToFullname(diff, diskfiles)
        if conf[k]['link']:
            g, b = makeLinks(tocopy, inc_dir)
        else:
            g, b = copyFiles(tocopy, inc_dir)
        print("{0} Files successfully placed in {1}.  {2} Failures".format(g, inc_dir, b))

    




        
#############################
# sample config file
#############################
