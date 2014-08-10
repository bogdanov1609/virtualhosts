#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import MySQLdb
import ConfigParser
import crypt
import subprocess
import shlex
import time
import pwd
import grp
import string
import random


def genpass(length):
    return ''.join(random.choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(length))


def log(event, message):
    if message != "":
        print "[%s]%s" % (event, message)


def runscript(script):
    args = shlex.split(script)
    process = subprocess.Popen(args, stdout=subprocess.PIPE)
    output = process.communicate()[0].strip()
    return output


def sqlcheck(con, acc):
    con["vhosts"].execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '%s'" % acc["name"])
    rows = con["vhosts"].fetchone()
    if rows[0] != 1:
        con["vhosts"].execute("CREATE DATABASE %s" % acc["name"])
        con["vhosts"].execute("GRANT ALL PRIVILEGES ON %s.* TO '%s'@'localhost' IDENTIFIED BY '%s'" % (acc["name"], acc["name"], acc["SQLpass"]))
        con["vhosts"].execute("FLUSH PRIVILEGES")
        return "SQL DB %s created" % acc["name"]
    return ""


def usercheck(acc):
    out = ""
    username = acc["name"]
    userroot = acc["root"]
    try:
        pwd.getpwnam(username)
    except KeyError:
        runscript("groupadd %s" % username)
        runscript("useradd -g %s -p %s %s" % (username, acc["FTPpass"], username))
        out += "Creating user for %s" % username
    if not os.path.isdir(userroot):
        os.makedirs(userroot+"/htdocs")
        os.makedirs(userroot+"/logs")
        os.makedirs(userroot+"/backup")
        uid = pwd.getpwnam(username).pw_uid
        gid = grp.getgrnam(username).gr_gid
        rootuid = pwd.getpwnam("root").pw_uid
        rootgid = grp.getgrnam("nogroup").gr_gid
        os.chown(userroot+"/htdocs", uid, gid)
        os.chown(userroot+"/logs", rootuid, rootgid)
        os.chown(userroot+"/backup", rootuid, rootgid)
        os.chmod(userroot+"/logs", 0775)
        os.chmod(userroot+"/backup", 0775)
        os.chmod(userroot+"/htdocs", 0775)
        out += "Creating folders for %s" % username
    return out


def ftpcheck(con, acc):
    encPass = crypt.crypt(acc["FTPpass"], genpass(2))
    con["ftp"].execute("SELECT COUNT(*) FROM ftpuser WHERE userid='%s'" % acc["name"])
    count = con["ftp"].fetchone()
    if count[0] != 1:
        con["ftp"].execute("INSERT INTO  `ftpd`.`ftpuser` (`userid`,`passwd`,`homedir`) VALUES ('%s', '%s', '%s');" % (acc["name"], encPass, acc["root"]))
        return "FTP user %s created" % acc["name"]
    else:
        return ""


def apachecheck(con, acc):
    confname = "%s_%s.conf" % (acc["hostname"], acc["name"])
    filename = "%s/%s" % (con["apache"], confname)
    cfg = open("template.conf", 'r').read()
    if not os.path.isfile(filename):
        cfg = cfg.replace("%USERNAME%", acc["name"]).replace("%HOSTNAME%", acc["hostnames"])
        cfg = cfg.replace("%ROOT%", acc["root"]).replace("%CUSTOM%", acc["custom"])
        cfile = open(filename, 'w')
        cfile.write(cfg)
        cfile.close()
        return "Create config file %s" % filename
    else:
        return ""


def hostscheck(acc):
    sqlname = acc["name"]+".mysqlserver"
    with open("/etc/hosts") as hosts:
        exists = False
        for line in hosts:
            split = line.strip().split()
            if len(split) == 2:
                if split[1] == sqlname:
                    exists = True
    if exists:
        return ""
    f = open("/etc/hosts", 'a')
    f.write("\n127.0.0.1 	%s" % sqlname)
    f.close()
    return "Created sqlserver alias %s" % sqlname


def checkaccount(con, acc):
    if acc["FTPpass"] == "":
        acc["FTPpass"] = genpass(8)
        con["vhosts"].execute("UPDATE vhosts SET FTPpass='%s' WHERE id=%s" % (acc["FTPpass"], acc["id"]))
        log(acc["name"], "Resetting %s's ftp password" % acc["name"])
    if acc["SQLpass"] == "":
        acc["SQLpass"] = genpass(8)
        con["vhosts"].execute("UPDATE vhosts SET SQLpass='%s' WHERE id=%s" % (acc["SQLpass"], acc["id"]))
        log(acc["name"], "Resetting %s's sql password" % acc["name"])
    if acc["root"] == "":
        acc["root"] = con["root"] + acc["hostname"]
        con["vhosts"].execute("UPDATE vhosts SET root='%s' WHERE id=%s" % (acc["root"], acc["id"]))
        log(acc["name"], "Setting %s's root to %s" % (acc["name"], acc["root"]))

    log(acc["name"], usercheck(con, acc))
    if (acc["SQLenabled"]!=0):
        log(acc["name"], sqlcheck(con, acc))
        log(acc["name"], hostscheck(con, acc))
    if (acc["FTPenabled"]!=0):
        log(acc["name"], ftpcheck(con, acc))
    if (acc["ApacheEnabled"]!=0):
        log(acc["name"], apachecheck(con, acc))


def readconfig(conf):
    con = {}
    cfg = ConfigParser.ConfigParser()
    cfg.read(conf)
    con["db"] = MySQLdb.connect(host=cfg.get("main", "host"),
        user=cfg.get("main", "user"),
        passwd=cfg.get("main", "passwd"),
        db=cfg.get("main", "db"))
    con["ftpdb"] = MySQLdb.connect(host=cfg.get("main", "host"),
        user=cfg.get("main", "user"),
        passwd=cfg.get("main", "passwd"),
        db=cfg.get("main", "ftpdb"))
    con["root"] = cfg.get("main", "root")
    con["apache"] = cfg.get("main", "apachedir")
    
    con["ftp"] = con["ftpdb"].cursor()
    con["vhosts"] = con["db"].cursor()    
    return con


def hello(con):
    print "Script started at " + time.ctime()
    con["vhosts"].execute("SELECT COUNT(*) FROM vhosts")
    count = con["vhosts"].fetchone()
    print "Vhosts: %s" % (count[0])


def getaccounts(con):
    con.execute("SELECT id, name, hostnames, custom, SQLpass, FTPpass, root, FTPenabled, SQLenabled, ApacheEnabled FROM vhosts WHERE enabled=1")
    accs = []
    columns = tuple( [d[0] for d in con.description] )
    for row in con:
        #User can have multuple host names; let's get the first one
        acc = dict(zip(columns, row))
        acc["hostname"] = acc["hostnames"].split()[0]
        accs.append(acc)
    return accs


def finish(con):
    con["db"].commit()
    print "Done; restarting apache"
    runscript("service apache2 reload")


if __name__ == "__main__":
    con = readconfig("config.cfg")
    hello(con)
    acs = getaccounts(con["vhosts"])
    for acc in acs:
        checkaccount(con, acc)
    finish(con)
