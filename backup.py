#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import tarfile
import ftplib
import gzip
import argparse

from common import run_script, mysql_connect, get_config, get_hosts, mkdir_recursive


def add_backup_record(con, user, filename, uploaded, folder, type):
    query = "INSERT INTO `vhosts`.`backups` (`host`, `filename`, `localpath`, `uploaded`, `remotepath`, `type`)" \
            "VALUES ('%s', '%s', '%s', '%s', NULL, '%s');" % (
                user['id'], filename, folder + filename, int(uploaded), type)
    con.execute(query)


def mysql_dump(auth_data, user, folder):
    now_date = str(datetime.date.today())
    dump = run_script("mysqldump -u %s -p%s -h %s %s" %
                      (auth_data['mysql_username'],
                       auth_data['mysql_password'],
                       auth_data['mysql_host'],
                       user['name']), "")
    filename = user['name'] + "." + now_date + ".sql.gz"
    f = gzip.open(folder + filename, 'wb')
    f.write(dump)
    f.close()
    return filename


def files_dump(auth_data, user, folder):
    now_date = str(datetime.date.today())
    filename = user['name'] + "." + now_date + ".tar.gz"
    tar = tarfile.open(folder + filename, "w:gz")
    tar.add(user['root'] + "/htdocs", arcname="htdocs")
    tar.close()
    return filename


def upload_to_ftp(auth_data, con, db):
    session = ftplib.FTP(auth_data['ftp_host'], auth_data['ftp_username'], auth_data['ftp_password'])
    session.set_pasv(True)
    query = "SELECT id, name, filename, localpath, date FROM uploaded_backups WHERE remotepath IS NULL"
    con.execute(query)
    backups = con.fetchall()
    for back in backups:
        id, name, filename, localpath, date = back
        remotedir = "/faculty/" + date.strftime("%Y-%m-%d")
        try:
            session.mkd(remotedir)
        except:
            pass
        session.cwd(remotedir)
        try:
            content = open(localpath, 'rb')
            try:
                session.storbinary('STOR ' + filename, content)
            except:
                pass
            content.close()
        except:
            pass
        query = "UPDATE backups SET remotepath='%s' WHERE id='%s'" % (remotedir + "\\" + filename, id)
        con.execute(query)
        print "Uploaded %s " % filename
        db.commit()
    session.quit()


def main(files, sql, onlyusers, upload):
    auth_data = get_config()
    db, con = mysql_connect(auth_data)
    accs = get_hosts(con)
    for acc in accs:
        if onlyusers and (acc['name'] not in onlyusers):
            print "Ignoring %s" % acc['name']
            continue
        if upload:
            folder = auth_data['backup_dir'] + str(datetime.date.today()) + '/'
        else:
            folder = acc['root'] + "/backup/"
        mkdir_recursive(folder)
        if files:
            print "Making %s's files backup" % acc['name']
            filename = files_dump(auth_data, acc, folder)
            add_backup_record(con, acc, filename, upload, folder, "files")
        if sql:
            print "Making %s's DB backup" % acc['name']
            filename = mysql_dump(auth_data, acc, folder)
            add_backup_record(con, acc, filename, upload, folder, "sql")
    db.commit()
    if upload:
        print "uploading"
        upload_to_ftp(auth_data, con, db)
    db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backups hosts')
    parser.add_argument("-nosql", action="store_true", required=False)
    parser.add_argument("-nofiles", action="store_true", required=False)
    parser.add_argument("-only", default="", required=False)
    parser.add_argument("-upload", action="store_true")
    (args) = parser.parse_args()
    if args.only != "":
        users = args.only.split(",")
    else:
        users = []
    main(not args.nofiles, not args.nosql, users, args.upload)
