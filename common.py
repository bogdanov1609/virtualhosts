import ConfigParser
import shlex
import subprocess
import MySQLdb
import os
import errno


def mkdir_recursive(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise


def get_hosts(con):
    con.execute("SELECT id, name, hostnames, custom, SQLpass, FTPpass, root, FTPenabled, SQLenabled, ApacheEnabled"
                "FROM vhosts WHERE enabled=1")
    accs = []
    columns = tuple( [d[0] for d in con.description] )
    for row in con:
        #User can have multuple host names; let's get the first one
        acc = dict(zip(columns, row))
        if acc["hostnames"]=="":
            acc["hostname"] = ""
        else:
            acc["hostname"] = acc["hostnames"].split()[0]
        accs.append(acc)
    return accs


def mysql_connect(auth_data):
    try:
        db = MySQLdb.connect(host=auth_data['mysql_host'], user=auth_data['mysql_username'],
                             passwd=auth_data['mysql_password'], db=auth_data['mysql_db'])
        cursor = db.cursor()
    except MySQLdb.Error:
        print db.error()
    return db, cursor


def run_script(script, input):
    args = shlex.split(script)
    process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    output = process.communicate(input=input)[0].strip()
    return output


def get_config():
    config = ConfigParser.ConfigParser()
    config.read('config.cfg')
    auth_data = {}
    auth_data['mysql_username'] = config.get('main', 'user')
    auth_data['mysql_password'] = config.get('main', 'passwd')
    auth_data['mysql_db'] = config.get('main', 'db')
    auth_data['mysql_host'] = config.get('main', 'host')
    auth_data['ftp_username'] = config.get('main', 'backuser')
    auth_data['ftp_password'] = config.get('main', 'backpass')
    auth_data['ftp_host'] = config.get('main', 'backhost')
    auth_data['backup_dir'] = config.get('main', 'directory')
    return auth_data

