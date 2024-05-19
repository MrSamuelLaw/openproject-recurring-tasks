#!/usr/bin/sh
printenv > /etc/environment;        # pass enviroment variables for crontab
/usr/sbin/sshd;                     # start the ssh server
cron && tail -f /var/log/cronlog;   # start the cron daemon