import ConfigParser
import MySQLdb
import os
import datetime
import tarfile
import ftplib
import sys
import gzip
import argparse
from update import getaccounts
from restore import RunScript

def mysql_connect(auth_data):
    try:
        db = MySQLdb.connect(host=auth_data['mysql_host'], user=auth_data['mysql_username'], passwd=auth_data['mysql_password'], db=auth_data['mysql_db'])
        cursor = db.cursor()
    except MySQLdb.Error:
        print db.error()
    return cursor


def get_auth_data():
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


def mysql_dump(auth_data, user):
    now_date = str(datetime.date.today())
    mysql_backup_dir = auth_data['backup_dir'] + now_date + '/' 
    if not os.path.exists(mysql_backup_dir):
        os.makedirs(mysql_backup_dir)
    dump = RunScript("mysqldump -u %s -p%s -h %s 2> /dev/null &" % 
        (auth_data['mysql_username'],
        auth_data['mysql_password'],
        auth_data['mysql_host']), "")
    filename = user['name'] + ".sql.gz"
    f = gzip.open(mysql_backup_dir + filename, 'wb')
    f.write(dump)
    f.close()
    return filename


def files_dump(auth_data, user):
    now_date = str(datetime.date.today())
    ftp_backup_dir = auth_data['backup_dir'] + now_date + '/'
    if not os.path.exists(ftp_backup_dir):
        os.makedirs(ftp_backup_dir)
    filename = user['name'] + ".tar.gz"
    tar = tarfile.open(ftp_backup_dir + filename, "w:gz")
    tar.add(user['root']+"/htdocs", arcname="htdocs")
    tar.close()
    return filename


def upload_to_ftp(auth_data, paths):
    #ToDo: clean this mess
    now_date = str(datetime.date.today())
    backup_dir = auth_data['backup_dir'] + now_date + '/'

    session = ftplib.FTP(auth_data['ftp_host'], auth_data['ftp_username'], auth_data['ftp_password'])
    try:
        session.mkd("faculty/" + now_date)
    except:
        pass
    session.cwd("faculty/" + now_date)

    for path in paths:
        content = open(backup_dir + path, 'rb')
        session.storbinary('STOR ' + path, content)
        content.close()
    session.quit()


def main(files, sql, onlyusers, upload):
    auth_data = get_auth_data()
    con = mysql_connect(auth_data)
    users = getaccounts(con)
    backups = []
    for user in users:
        if (onlyusers) and (user['name'] not in onlyusers):
            print "Ignoring %s" % user['name']
            continue
        if files:
            print "Making %s's files backup" % user['name']
            backups.append(files_dump(auth_data, user))
        if sql:
            print "Making %s's DB backup" % user['name']
            backups.append(mysql_dump(auth_data, user))
    if upload:
        print "uploading"
        upload_to_ftp(auth_data, backups)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Restores from backup')
    parser.add_argument("-nosql", action="store_true", required=False)
    parser.add_argument("-nofiles", action="store_true", required=False)
    parser.add_argument("-only", default="", required=False)
    parser.add_argument("-upload", action="store_false")
    (args) = parser.parse_args()
    if args.only!="":
        users = args.only.split(",")
    else:
        users = []
    main(not args.nofiles, not args.nosql, users, args.upload)
