#!/usr/bin/sh
printenv > /etc/environment;        # pass enviroment variables for crontab
cron && tail -f /var/log/cronlog;   # start the cron daemon