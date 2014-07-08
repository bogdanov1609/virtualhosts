import os
import MySQLdb
import sys
import ConfigParser
import subprocess
import shlex
import time
import fnmatch
import tarfile
import gzip
import codecs
import chardet
import errno


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
    if len(sys.argv)!=2:
        print("Usage: python restore.py <backup folder>")
        sys.exit(1)
    backupdir = sys.argv[1]
    cur = db.cursor()
    print("Restoring backups from %s" % backupdir)

    cur.execute("SELECT name, SQLpass, root FROM vhosts")
    rows = cur.fetchall()
    for row in rows:
        name, sqlp, root = row
        if (root==""):
            print("No root for user %s" % (name))
            continue
        backup = Find(backupdir+name, "files.%s.*.tar.gz" % (name))
        if (backup!=""):
            print("Restoring files from %s" % backup)
            tar = tarfile.open(backup, encoding="utf-8")
            for x in tar.getmembers():
                print root + "/" + x.name
                y = x.name
                mkdir_p(root + "/" + os.path.dirname(y))
                content = tar.extractfile(x)
                if content != None:
                    file = open(root + "/" + y, "w")
                    file.write(content.read())
                    file.close()
            tar.close()
        backup = Find(backupdir+name, "db.%s.*.sql.gz" % (name))
        if (backup!=""):
            print("Restoring db from %s" % backup)
            f = gzip.open(backup, 'rb')
            file_content = f.read()
            f.close()
            RunScript("mysql -u %s -p%s %s" % (cfg.get("main", "user"), cfg.get("main", "passwd"), name), file_content)
