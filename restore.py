#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import MySQLdb
import ConfigParser
import subprocess
import shlex
import fnmatch
import tarfile
import gzip
import errno
import argparse


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise


def Log(name, message):
    if message!="":
        print("[%s]%s" % (name, message))


def Find(path, pattern):
    out = ""
    if (not os.path.isdir(path)):
        return ""
    for index, file in enumerate(sorted(os.listdir(path))):
        if fnmatch.fnmatch(file, pattern):
            out = path+"/"+file
    return out


def RunScript(script, input):
    args = shlex.split(script)
    process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    output = process.communicate(input=input)[0].strip()
    return output


if __name__ == "__main__":
    cfg = ConfigParser.ConfigParser()
    cfg.read("config.cfg")
    db = MySQLdb.connect(host=cfg.get("main", "host"),
            user=cfg.get("main", "user"),
            passwd=cfg.get("main", "passwd"),
            db=cfg.get("main", "db"))
    parser = argparse.ArgumentParser(description='Restores from backup')
    parser.add_argument("-nosql", action="store_true", required=False)
    parser.add_argument("-nofiles", action="store_true", required=False)
    parser.add_argument("-only", default="", required=False)
    parser.add_argument("folder")
    (args) = parser.parse_args()

    backupdir = args.folder
    users = args.only.split(",")
    cur = db.cursor()
    print("Restoring backups from %s" % backupdir)

    cur.execute("SELECT name, hostnames, SQLpass, root FROM vhosts")
    rows = cur.fetchall()
    for row in rows:
        name, hostnames, sqlp, root = row
        if (users) and (name not in users):
            continue
        if (root==""):
            print("No root for user %s" % (name))
            continue
        backup = Find(backupdir+name, "files.%s.*.tar.gz" % (name))
        if not args.nofiles:
            if backup=="":
                if (os.path.isfile(backupdir+hostnames+".tar.gz")):
                    backup = backupdir+hostnames+".tar.gz"
                short = hostnames.strip().split()[0].split(".")[0]
                if (os.path.isfile(backupdir+short+".tar.gz")):
                    backup = backupdir+short+".tar.gz"
            if (backup!=""):
                print("Restoring files from %s" % backup)
                tar = tarfile.open(backup, encoding="utf-8")
                for x in tar.getmembers():
                    mkdir_p(root + "/" + os.path.dirname(x.name))
                    content = tar.extractfile(x)
                    if content != None:
                        file = open(root + "/" + x.name, "w")
                        file.write(content.read())
                        file.close()
                tar.close()
            else:
                print "No file backup found for %s" % name
        if not args.nosql:
            backup = Find(backupdir+name, "db.%s.*.sql.gz" % (name))
            if (backup!=""):
                print("Restoring db from %s" % backup)
                f = gzip.open(backup, 'rb')
                file_content = f.read()
                f.close()
                RunScript("mysql -u %s -p%s %s" % (cfg.get("main", "user"), cfg.get("main", "passwd"), name), file_content)
            else:
                print "No SQL backup found for %s" % name
