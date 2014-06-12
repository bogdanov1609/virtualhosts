#!/bin/bash

#USAGE:
#user.sh <username> <hostname> <root> <alias> <apachedir>

user=$1
host=$2
root=$3
alias=$4
dir=$5

conf="$host-$user.conf"

if [ ! -f "$dir/$conf" ]; then
	echo "Creating $dir/$conf"
	cat template.conf | sed "s/%USER%/$user/g" | sed "s/%HOST%/$host/g" | sed "s/%ROOT%/$root/g" | sed "s/%ALIAS%/$alias/g"
fi
