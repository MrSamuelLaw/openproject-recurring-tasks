FROM python:3.12-slim

# update and upgrade
RUN apt update && apt upgrade -y

# get ssh server running
RUN apt install -y openssh-server -y
RUN mkdir /var/run/sshd
RUN echo 'root:root' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
EXPOSE 22

# copy the app into the root dir of the container
COPY ./app /app
RUN pip install -r /app/requirements.txt

# install cron
RUN apt install cron -y
COPY ./app/crontab /etc/cron.d/crontab
RUN chmod +x /etc/cron.d/crontab
RUN touch /var/log/cronlog
RUN /usr/bin/crontab /etc/cron.d/crontab

# run the entry point script
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["sh", "/app/entrypoint.sh"]
