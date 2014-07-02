import os
import MySQLdb
import sys
import ConfigParser
import crypt
import subprocess
import shlex
import time
import pwd
import grp

def Log(name, message):
	if message!="":
		print "[%s]%s" % (name, message)

def RunScript(script):
        args = shlex.split(script)
        process = subprocess.Popen(args, stdout=subprocess.PIPE)
        output = process.communicate()[0].strip()
        return output

def chmodr(path, mode):
	for root, dirs, files in os.walk(path, topdown=False):
		for dir in dirs:
			os.chmod(path + "/" + dir, mode)
		for file in files:
			os.chmod(path + "/" + file, mode)

def SQLCheck(con, name, sqlp):
	cur.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '%s'" % (name))
	rows = cur.fetchone()
	if (rows[0]!=1):
       		cur.execute("CREATE DATABASE %s" % (name))
		cur.execute("GRANT ALL PRIVILEGES ON %s.* TO '%s'@'localhost' IDENTIFIED BY '%s'" % (name, name, sqlp))
		cur.execute("FLUSH PRIVILEGES")
		return "SQL DB %s created" % name
	return ""

def UserCheck(name, ftpp, root):
	out = ""

	try:
		pwd.getpwnam(name)
	except KeyError:
		RunScript("groupadd %s" % (name))
		RunScript("useradd -g %s -p %s %s" % (name, ftpp, name))
    		out += "Creating user for %s" % (name)

	if not os.path.isdir(root):
		os.makedirs(root+"/htdocs")
		os.makedirs(root+"/logs")
		os.makedirs(root+"/backup")
		chmodr(root, 755)
		uid = pwd.getpwnam(name).pw_uid
		gid = grp.getgrnam(name).gr_gid
		rootuid = pwd.getpwnam("root").pw_uid
		rootgid = grp.getgrnam("nogroup").gr_gid
		os.chown(root+"/htdocs", uid, gid)
		os.chown(root+"/logs", rootuid, rootgid)
		os.chown(root+"/backup", rootuid, rootgid)
		out += "Creating folders for %s" % (name)
	return out

def FTPCheck(cur, username, password, root):
	encPass = crypt.crypt(password, "22")
	cur.execute("SELECT COUNT(*) FROM ftpuser WHERE userid='%s'" % (username))
	count = cur.fetchone()
	if (count[0]!=1):
		cur.execute("INSERT INTO  `ftpd`.`ftpuser` (`userid`,`passwd`,`homedir`) VALUES ('%s', '%s', '%s/htdocs');" % (username, encPass, root))
		return "FTP user %s created" % username
	else:
		return ""

def ApacheCheck(username, hostname, root, alias, apache):
	confname = "%s_%s.conf" % (hostname, username)
	filename = "%s/%s" % (apache, confname)
	cfg = open("template.conf", 'r').read()
	if (not os.path.isfile(filename)):
		if (alias!=""):
			alias = "ServerAlias %s" % (alias)
		cfg = cfg.replace("%USERNAME%", username).replace("%HOSTNAME%", hostname)
		cfg = cfg.replace("%ROOT%", root).replace("%ALIAS%", alias)
		file = open(filename, 'w')
		file.write(cfg)
		file.close()
		return "Create config file %s" % (filename)
	else:
		return ""

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

        cur.execute("SELECT username, hostname, alias, SQLpass, FTPpass, root FROM vhosts")
	rows = cur.fetchall()
        for row in rows :
		name, hname, alias, sqlp, ftpp, root = row
		if (root==""):
			root = defaultroot + hname
		Log(name, "Checking %s (root %s)" % (hname, root))
		Log(name, UserCheck(name, ftpp, root))
		Log(name, SQLCheck(cur, name, sqlp))
		Log(name, FTPCheck(ftpcur, name, ftpp, root))
                Log(name, ApacheCheck(name, hname, root, alias, apachedir))
	print "Done; restarting apache"
	print RunScript("service apache2 restart")
