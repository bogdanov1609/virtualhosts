import os
import datetime
import tarfile
import ftplib
import gzip
import argparse
from common import run_script, mysql_connect, get_config, get_hosts, mkdir_recursive


def add_backup_record(con, user, filename, uploaded, folder):
    query = "INSERT INTO `vhosts`.`backups` (`host`, `filename`, `localpath`, `uploaded`)" \
            "VALUES (%s, %s, %s, %s);" % (user['id'], filename, folder+filename, uploaded)
    con.execute(query)
    con.commit()

def mysql_dump(auth_data, user, folder):
    now_date = str(datetime.date.today())
    dump = run_script("mysqldump -u %s -p%s -h %s 2> /dev/null &" %
        (auth_data['mysql_username'],
        auth_data['mysql_password'],
        auth_data['mysql_host']), "")
    filename = user['name'] + "." + now_date + ".sql.gz"
    f = gzip.open(folder + filename, 'wb')
    f.write(dump)
    f.close()
    return filename


def files_dump(auth_data, user, folder):
    now_date = str(datetime.date.today())
    filename = user['name'] + "." + now_date + ".tar.gz"
    tar = tarfile.open(folder + filename, "w:gz")
    tar.add(user['root']+"/htdocs", arcname="htdocs")
    tar.close()
    return filename


def upload_to_ftp(auth_data, paths):
    return
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
    auth_data = get_config()
    db, con = mysql_connect(auth_data)
    accs = get_hosts(con)
    backups = []
    for acc in accs:
        if onlyusers and (acc['name'] not in onlyusers):
            print "Ignoring %s" % acc['name']
            continue
        if upload:
            folder = auth_data['backup_dir'] + str(datetime.date.today()) + '/'
        else:
            folder = acc['root']+"/backup/"
        mkdir_recursive(folder)
        if files:
            print "Making %s's files backup" % acc['name']
            filename = files_dump(auth_data, acc, folder)
            add_backup_record(con, acc, filename, upload, folder)
        if sql:
            print "Making %s's DB backup" % acc['name']
            filename = mysql_dump(auth_data, acc, folder)
            add_backup_record(con, acc, filename, upload, folder)
    if upload:
        print "uploading"
        upload_to_ftp(auth_data, backups)
    db.commit()
    db.close()


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