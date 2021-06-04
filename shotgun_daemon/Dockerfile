FROM python:2.7

RUN apt-get update
RUN apt-get -y install vim \
					   ffmpeg \
					   jq

# Download and unzip the Shotgun daemon and API
RUN wget -O /tmp/shotgun_daemon.zip \
	"https://github.com/shotgunsoftware/shotgunEvents/archive/master.zip"
	
RUN wget -O /tmp/shotgun_api.zip \
	"https://github.com/shotgunsoftware/python-api/archive/master.zip"

RUN wget -O /tmp/conductor_client.zip \
	"https://github.com/AtomicConductor/conductor_client/master.zip"	

RUN unzip /tmp/shotgun_daemon.zip -d /tmp/
RUN unzip /tmp/shotgun_api.zip -d /tmp/
RUN unzip /tmp/conductor_client.zip -d /tmp/

RUN mv /tmp/shotgunEvents-master /opt/shotgun_daemon
RUN mv /tmp/python-api-master/ /opt/shotgun_daemon/api
RUN mv /tmp/conductor_client-master/ /opt/conductor

COPY files/shotgunEventDaemon.conf /opt/shotgun_daemon/src/shotgunEventDaemon.conf

# Setup the path for plugins
RUN mkdir -p /usr/local/shotgun/plugins
RUN mkdir -p /usr/local/shotgun/support_files

COPY plugins/submit_maya_render_to_conductor.py /usr/local/shotgun/plugins/
COPY plugins/submit_nuke_template_to_conductor.py /usr/local/shotgun/plugins/
COPY plugins/create_version.py /usr/local/shotgun/plugins/

COPY src/submit_to_conductor_base.py /usr/local/shotgun/support_files
COPY src/register_publish.py /usr/local/shotgun/support_files
COPY src/post_render_script.py //usr/local/shotgun/support_files
COPY src/nuke_template.nk /usr/local/shotgun/support_files

RUN pip install -r /opt/conductor/requirements.txt
RUN mkdir -p /root/.conductor
COPY files/conductor_config.yaml /root/.conductor/config.yml

RUN pip install boto3

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

ENV PYTHONPATH=/opt/shotgun_daemon/api:/usr/local/shotgun/support_files:/opt/conductor

COPY files/shotgunEventDaemon.py /opt/shotgun_daemon/src/shotgunEventDaemon.py

CMD /opt/shotgun_daemon/src/shotgunEventDaemon.py foreground
