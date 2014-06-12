#!/bin/bash
#USAGE:
#update.sh USERNAME USERPASS
user=$1
base=$1
pass=$(cat sqlpass)
userpass=$2
base_exists=$(mysql -u root -prootroot -B -N -e "SHOW DATABASES like '$base'")
if [[ $base_exists == "" ]]
then
	mysql -u root -p$pass -e "CREATE DATABASE $base;"
	mysql -u root -p$pass -e "GRANT ALL PRIVILEGES ON $user.* TO '$base'@'localhost' IDENTIFIED BY '$userpass';"
	mysql -u root -p$pass -e "FLUSH PRIVILEGES;"
	echo "Database $base created"
fi
