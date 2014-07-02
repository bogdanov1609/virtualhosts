import os
import MySQLdb
import ConfigParser
import crypt
import subprocess
import shlex
import time
import pwd
import grp


def log(event, message):
    if message != "":
        print "[%s]%s" % (event, message)


def runscript(script):
    args = shlex.split(script)
    process = subprocess.Popen(args, stdout=subprocess.PIPE)
    output = process.communicate()[0].strip()
    return output


def sqlcheck(con, username, sqlpass):
    cur.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '%s'" % username)
    rows = cur.fetchone()
    if rows[0] != 1:
        cur.execute("CREATE DATABASE %s" % username)
        cur.execute("GRANT ALL PRIVILEGES ON %s.* TO '%s'@'localhost' IDENTIFIED BY '%s'" % (username, username, sqlpass))
        cur.execute("FLUSH PRIVILEGES")
        return "SQL DB %s created" % username
    return ""


def usercheck(username, ftppass, userroot):
    out = ""
    try:
        pwd.getpwnam(username)
    except KeyError:
        runscript("groupadd %s" % username)
        runscript("useradd -g %s -p %s %s" % (username, ftppass, username))
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


def ftpcheck(sqlcur, username, password, userroot):
    encPass = crypt.crypt(password, "22")
    sqlcur.execute("SELECT COUNT(*) FROM ftpuser WHERE userid='%s'" % username)
    count = sqlcur.fetchone()
    if count[0] != 1:
        sqlcur.execute("INSERT INTO  `ftpd`.`ftpuser` (`userid`,`passwd`,`homedir`) VALUES ('%s', '%s', '%s/htdocs');" % (username, encPass, userroot))
        return "FTP user %s created" % username
    else:
        return ""


def apachecheck(username, hostname, root, alias, apache):
    confname = "%s_%s.conf" % (hostname, username)
    filename = "%s/%s" % (apache, confname)
    cfg = open("template.conf", 'r').read()
    if not os.path.isfile(filename):
        if alias != "":
            alias = "ServerAlias %s" % alias
        cfg = cfg.replace("%USERNAME%", username).replace("%HOSTNAME%", hostname)
        cfg = cfg.replace("%ROOT%", root).replace("%ALIAS%", alias)
        cfile = open(filename, 'w')
        cfile.write(cfg)
        cfile.close()
        return "Create config file %s" % filename
    else:
        return ""


def hostscheck(username):
    sqlname = username+".mysqlserver"
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


if __name__ == "__main__":
    print "Script started at " + time.ctime()
    cfg = ConfigParser.ConfigParser()
    cfg.read("config.cfg")
    db = MySQLdb.connect(host=cfg.get("main", "host"),
    user=cfg.get("main", "user"),
    passwd=cfg.get("main", "passwd"),
    db=cfg.get("main", "db"))
    ftpdb = MySQLdb.connect(host=cfg.get("main", "host"),
    user=cfg.get("main", "user"),
    passwd=cfg.get("main", "passwd"),
    db=cfg.get("main", "ftpdb"))
    defaultroot = cfg.get("main", "root")
    apachedir = cfg.get("main", "apachedir")

    ftpcur = ftpdb.cursor()
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) FROM vhosts")
    count = cur.fetchone()
    print "Vhosts: %s" % (count[0])

    cur.execute("SELECT id, username, hostname, alias, SQLpass, FTPpass, root FROM vhosts")
    rows = cur.fetchall()
    for row in rows :
        id, name, hname, alias, sqlp, ftpp, root = row
        if root == "":
            root = defaultroot + hname
            cur.execute("UPDATE vhosts SET root='%s' WHERE id=%s" % (root, id))
            log(name, "Setting %s's root to %s" % (name, root))
        log(name, usercheck(name, ftpp, root))
        log(name, sqlcheck(cur, name, sqlp))
        log(name, ftpcheck(ftpcur, name, ftpp, root))
        log(name, apachecheck(name, hname, root, alias, apachedir))
        log(name, hostscheck(name))
    db.commit()
    print "Done; restarting apache"
    print runscript("service apache2 restart")
