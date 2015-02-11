#!/bin/bash
# Backup the vsc home directory with rsync
# (add to crontab via 'crontab -e')

SRC="~"
DEST="$HOME/VSC_Backup"
OLD="$DEST/deleted_files"

DATE=$(date "+%Y_%m_%d-%H:%M:%S")
LOGFILE="$DEST/LOGFILES/rsync_log_$DATE.log"

rsync --delete -abvzPe ssh vsc:$SRC $DEST --backup-dir=$OLD > $LOGFILE
