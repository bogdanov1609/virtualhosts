#!/bin/bash

#USAGE:
#user.sh <user> <password> <wwwdir>

user=$1
ftppass=$2
www=$3

encpass=$(perl -e 'print crypt($ARGV[0], "password")' $ftppass)

if [[ $(id -u $user 2> /dev/null) == "" ]]
then
        echo "Creating user $user"
	groupadd $1
	useradd -g $1 -p $encpass $1
fi

if [ ! -d "$www" ]; then
	echo "Creating dirs in $www"

	mkdir -p $www/htdocs
	mkdir -p $www/logs
	mkdir -p $www/backup

	chmod -R 777 $www
	chown -R root $www
	chown -R root $www/backup
	chown -R $1 $www/htdocs
	chmod -R 777 $www/htdocs

	#chown -R root:$login $www/backup
	#chown -R $login:$login $www/htdocs
	#chown -R root:$login $www/logs
fi
