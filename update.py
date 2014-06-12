import os
import MySQLdb
import sys
import ConfigParser
import crypt
import subprocess
import shlex
import os
import time

def RunScript(script):
        args = shlex.split(script)
        process = subprocess.Popen(args, stdout=subprocess.PIPE)
        output = process.communicate()[0].strip()
        return output

def RunAndPrint(script):
	out = RunScript(script)
	if (out!=""):
		print out

def FTPCheck(cur, username, password, root):
	encPass = crypt.crypt(password, "22")
	cur.execute("SELECT COUNT(*) FROM ftpuser WHERE userid='%s'" % (username))
	count = cur.fetchone()
	if (count[0]!=1):
		cur.execute("INSERT INTO  `ftpd`.`ftpuser` (`userid`,`passwd`,`homedir`) VALUES ('%s', '%s', '%s');" % (username, encPass, root))
		return "FTP user %s created" % username
	else:
		return ""

def ApacheCheck(username, hostname, root, alias, apache):
	confname = "%s_%s.conf" % (hostname, username)
	filename = "%s/%s" % (apache, confname)
	cfg = open("template.conf", 'r').read()
	if (not os.path.isfile(filename)):
		if (alias!=""):
			alias = "Alias /%s %s/htdocs" % (alias, root)
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
	logs = []
	apacheRR=False
        for row in cur.fetchall() :
		name, hname, alias, sqlp, ftpp, root = row
		if (root==""):
			root = defaultroot + name
		#1. User
		out = RunScript("./user.sh %s %s %s" % (name, ftpp, root))
		if (out!=""):
			logs.append({"name" : name, "stage" : "user", "out" : out})
			apacheRR=True
		#2. SQL
                out = RunScript("./sql.sh %s %s" % (name, sqlp))
                if (out!=""):
                        logs.append({"name" : name, "stage" : "sql", "out" : out})
		#3. FTP
		out = FTPCheck(ftpcur, name, ftpp, root)
                if (out!=""):
                        logs.append({"name" : name, "stage" : "ftp", "out" : out})
		#4. Apache
                out = ApacheCheck(name, hname, root, alias, apachedir)
                if (out!=""):
                        logs.append({"name" : name, "stage" : "apache", "out" : out})
			apacheRR=True
	for entry in logs:
		for line in entry["out"].split('\n'):
			print "[User %s , %s stage] : %s" % (entry["name"], entry["stage"], line)
	if apacheRR:
		print "Done; restarting apache"
		print RunScript("./apacherr.sh")
	else:
		print "Done."
