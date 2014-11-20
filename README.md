virtualhosts
============
This is script for automated managing virtual hosts under Apache+MySQL+FTPd.
#General
Account data is stored in MySQL database.

To synchronize account info in base with actual one should use `update.py`

To create backup run `backup.py`.

There is no built-in GUI for managing accounts. One should use PhpMyAdmin or console mysql client to make changes.

Currently, scripts are incapable to update passwords, delete or rename accounts,
restore backups (script is broken), add entries to logrotate,
and update some configuration files.

#Managing account information
Make changes in DB using your favourite MySQL client, and then use
`update.py` to apply changes. Specificially, it does (for each account, in that order):

<UL>
<LI>Generate FTP and SQL passwords, if these fields are empty
<LI>Set `root` field to default one, if field is empty
<LI>Create SQL database, if one doesn't exist
<LI>Add entry to `hosts` file (entry is `127.0.0.1  <hostname>.mysqlserver), if one doesn't exist
<LI>Create account for ftpd, if one doesn't exist
<LI>Create entry in apache, if one doesn't exist
</UL>

#Creating backups
`backup.py` is script for backups. Syntax is:

```
backup.py [-nosql] [-nofiles] [-only users] [-upload]
```

`-nosql` no MySQL dump will be made and included in backup.

`-nofiles` files won't be backupped.

`-only users` create backups for specified users only. `users` should be comma-separated list of account names.

`-upload` upload backups to FTP

#Usage
##Updating
Update information in MySQL database and run
```
python update.py
```
##Making backups
Run
```
python backup.py
```

